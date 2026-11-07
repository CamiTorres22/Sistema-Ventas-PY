from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database import get_db
from backend.app.models import Cliente, ClienteVendedor, Producto, Venta, DetalleVenta, Usuario
from backend.app.routers.auth import get_current_user
from backend.app.schemas.schemas import (
    PedidoCreate, PedidoOut, PedidoResumen, DetallePedidoOut,
)

router = APIRouter(prefix="/ventas", tags=["Ventas"])


def _vid() -> str:
    return "ICO-" + uuid.uuid4().hex[:8].upper()


@router.post("", response_model=PedidoOut, status_code=201)
async def confirmar_venta(
    data: PedidoCreate,
    db:   AsyncSession = Depends(get_db),
    user: Usuario      = Depends(get_current_user),
):
    if not (await db.execute(select(Cliente).where(Cliente.cliente_id == data.cliente_id))).scalar_one_or_none():
        raise HTTPException(404, f"Cliente '{data.cliente_id}' no encontrado.")
    total = 0.0
    detalles = []
    for item in data.items:
        prod = (await db.execute(
            select(Producto).where(Producto.producto_id == item.producto_id, Producto.sede == item.sede).limit(1)
        )).scalar_one_or_none()
        if prod is None: raise HTTPException(404, f"Producto '{item.producto_id}' no encontrado.")
        if prod.stock < item.cantidad: raise HTTPException(400, f"Stock insuficiente para '{item.producto_id}'.")
        sub = round(prod.precio_unitario * item.cantidad, 2)
        total += sub
        prod.stock -= item.cantidad
        detalles.append(DetalleVenta(producto_id=item.producto_id, cantidad_producto=item.cantidad, subtotal=sub))
    venta = Venta(venta_id=_vid(), cliente_id=data.cliente_id, fecha_venta=data.fecha_venta, monto_total=round(total, 2))
    db.add(venta)
    await db.flush()
    for d in detalles:
        d.venta_id = venta.venta_id
        db.add(d)
    await db.commit()
    res = await db.execute(select(Venta).options(selectinload(Venta.detalles)).where(Venta.venta_id == venta.venta_id))
    return _to_out(res.scalar_one())


@router.get("", response_model=list[PedidoResumen])
async def listar_ventas(
    cliente_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    db:   AsyncSession = Depends(get_db),
    user: Usuario      = Depends(get_current_user),
):
    q = select(Venta).options(selectinload(Venta.detalles))

    if cliente_id:
        # Mostrar todos los pedidos de ese cliente
        q = q.where(Venta.cliente_id == cliente_id)
    else:
        # Mostrar pedidos de todos los clientes asignados al vendedor
        asignados = (await db.execute(
            select(ClienteVendedor.cliente_id).where(ClienteVendedor.vendedor_id == user.id)
        )).scalars().all()
        if asignados:
            q = q.where(Venta.cliente_id.in_(asignados))

    q = q.order_by(Venta.fecha_venta.desc()).offset(skip).limit(limit)
    ventas = (await db.execute(q)).scalars().all()
    return [PedidoResumen(venta_id=v.venta_id, cliente_id=v.cliente_id,
                         fecha_venta=v.fecha_venta, monto_total=v.monto_total,
                         n_productos=len(v.detalles)) for v in ventas]


@router.get("/{venta_id}", response_model=PedidoOut)
async def detalle_venta_ep(
    venta_id: str,
    db:   AsyncSession = Depends(get_db),
    user: Usuario      = Depends(get_current_user),
):
    venta = (await db.execute(
        select(Venta).options(selectinload(Venta.detalles)).where(Venta.venta_id == venta_id)
    )).scalar_one_or_none()
    if venta is None: raise HTTPException(404, f"Venta '{venta_id}' no encontrada.")
    return _to_out(venta)


def _to_out(v: Venta) -> PedidoOut:
    return PedidoOut(
        venta_id=v.venta_id, cliente_id=v.cliente_id,
        fecha_venta=v.fecha_venta, monto_total=v.monto_total,
        detalles=[DetallePedidoOut(producto_id=d.producto_id,
                                  cantidad_producto=d.cantidad_producto,
                                  subtotal=d.subtotal) for d in v.detalles],
    )
