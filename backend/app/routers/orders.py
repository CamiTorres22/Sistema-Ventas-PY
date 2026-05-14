"""
orders.py — Gestión del carrito y pedidos

Endpoints:
  POST   /pedidos                  → confirmar pedido (carrito → pedido)
  GET    /pedidos                  → historial del vendedor autenticado
  GET    /pedidos/{id}             → detalle de un pedido
  PATCH  /pedidos/{id}/estado      → cambiar estado [admin]
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database import get_db
from backend.app.models import Cliente, DetallePedido, Pedido, Producto, Usuario
from backend.app.routers.auth import get_current_user, require_admin
from backend.app.schemas import PedidoCreate, PedidoOut, PedidoResumen

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

TAX_RATE = 0.12   # IGV Perú


def _generar_numero_pedido(pedido_id: int) -> str:
    anio = datetime.now(timezone.utc).year
    return f"ICO-{anio}-{pedido_id:04d}"


@router.post("", response_model=PedidoOut, status_code=201)
async def confirmar_pedido(
    data: PedidoCreate,
    db:   AsyncSession = Depends(get_db),
    user: Usuario      = Depends(get_current_user),
):
    """
    Convierte el carrito en un pedido confirmado.
    Valida stock de cada producto y actualiza las unidades disponibles.
    El flag `desde_recomendacion` en cada ítem se persiste para métricas.
    """
    # Verificar que el cliente existe
    res_c = await db.execute(select(Cliente).where(Cliente.cliente_id == data.cliente_id))
    if not res_c.scalar_one_or_none():
        raise HTTPException(404, f"Cliente '{data.cliente_id}' no encontrado.")

    subtotal = 0.0
    detalles = []

    for item in data.items:
        res_p = await db.execute(
            select(Producto).where(Producto.producto_id == item.producto_id)
        )
        prod = res_p.scalar_one_or_none()
        if prod is None:
            raise HTTPException(404, f"Producto '{item.producto_id}' no encontrado.")
        if prod.stock < item.cantidad:
            raise HTTPException(
                400,
                f"Stock insuficiente para '{prod.nombre}': "
                f"disponible {prod.stock}, solicitado {item.cantidad}.",
            )

        linea_subtotal = round(prod.precio_unitario * item.cantidad, 2)
        subtotal += linea_subtotal

        # Descontar del stock
        prod.stock -= item.cantidad

        detalles.append(DetallePedido(
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            precio_unit=prod.precio_unitario,
            subtotal=linea_subtotal,
            desde_recomendacion=item.desde_recomendacion,
        ))

    impuesto = round(subtotal * TAX_RATE, 2)
    total    = round(subtotal + impuesto, 2)

    pedido = Pedido(
        numero="TEMP",   # se actualiza tras el commit para tener el id
        cliente_id=data.cliente_id,
        vendedor_id=user.id,
        estado="completado",
        subtotal=subtotal,
        impuesto=impuesto,
        descuento=0.0,
        total=total,
        forma_pago=data.forma_pago,
        notas=data.notas,
    )
    db.add(pedido)
    await db.flush()   # obtener pedido.id antes del commit

    pedido.numero = _generar_numero_pedido(pedido.id)
    for det in detalles:
        det.pedido_id = pedido.id
        db.add(det)

    await db.commit()

    # Re-cargar con relaciones para la respuesta
    res = await db.execute(
        select(Pedido)
        .options(selectinload(Pedido.detalles).selectinload(DetallePedido.producto))
        .where(Pedido.id == pedido.id)
    )
    pedido_full = res.scalar_one()

    return _pedido_to_out(pedido_full)


@router.get("", response_model=list[PedidoResumen])
async def listar_pedidos(
    estado:     Optional[str] = Query(default=None),
    cliente_id: Optional[str] = Query(default=None),
    skip:       int           = Query(default=0, ge=0),
    limit:      int           = Query(default=20, ge=1, le=1000),
    db:         AsyncSession  = Depends(get_db),
    user:       Usuario       = Depends(get_current_user),
):
    """
    Vendedor: su propio historial.
    Admin: todos los pedidos.
    """
    q = select(Pedido).options(selectinload(Pedido.detalles), selectinload(Pedido.cliente))

    if user.rol != "admin":
        if cliente_id:
            # Al filtrar por cliente, incluye pedidos propios Y pedidos históricos
            # (vendedor_id=NULL) para que el vendedor vea el historial completo del cliente
            q = q.where(
                (Pedido.vendedor_id == user.id) | (Pedido.vendedor_id == None)
            )
        else:
            q = q.where(Pedido.vendedor_id == user.id)
    if estado:
        q = q.where(Pedido.estado == estado)
    if cliente_id:
        q = q.where(Pedido.cliente_id == cliente_id)

    q = q.order_by(Pedido.creado_en.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    pedidos = result.scalars().all()

    return [
        PedidoResumen(
            id=p.id,
            numero=p.numero,
            cliente_id=p.cliente_id,
            nombre_cliente=p.cliente.nombre if p.cliente else p.cliente_id,
            estado=p.estado,
            total=p.total,
            n_productos=len(p.detalles),
            creado_en=p.creado_en,
        )
        for p in pedidos
    ]


@router.get("/{pedido_id}", response_model=PedidoOut)
async def detalle_pedido(
    pedido_id: int,
    db:   AsyncSession = Depends(get_db),
    user: Usuario      = Depends(get_current_user),
):
    res = await db.execute(
        select(Pedido)
        .options(selectinload(Pedido.detalles).selectinload(DetallePedido.producto))
        .where(Pedido.id == pedido_id)
    )
    pedido = res.scalar_one_or_none()
    if pedido is None:
        raise HTTPException(404, f"Pedido ID {pedido_id} no encontrado.")
    if user.rol != "admin" and pedido.vendedor_id != user.id:
        raise HTTPException(403, "No tienes acceso a este pedido.")
    return _pedido_to_out(pedido)


@router.patch("/{pedido_id}/estado")
async def cambiar_estado(
    pedido_id: int,
    estado:    str,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Actualiza el estado de un pedido. Solo administradores."""
    estados_validos = {"pendiente", "en_proceso", "completado", "cancelado"}
    if estado not in estados_validos:
        raise HTTPException(400, f"Estado inválido. Opciones: {estados_validos}")

    res = await db.execute(select(Pedido).where(Pedido.id == pedido_id))
    pedido = res.scalar_one_or_none()
    if pedido is None:
        raise HTTPException(404, f"Pedido ID {pedido_id} no encontrado.")

    pedido.estado = estado
    await db.commit()
    return {"detail": f"Estado actualizado a '{estado}'."}


# ──────────────────────────────────────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────────────────────────────────────

def _pedido_to_out(pedido: Pedido) -> PedidoOut:
    from backend.app.schemas import DetallePedidoOut

    detalles_out = [
        DetallePedidoOut(
            producto_id=d.producto_id,
            nombre=d.producto.nombre if d.producto else d.producto_id,
            categoria_producto=d.producto.categoria_producto if d.producto else "",
            cantidad=d.cantidad,
            precio_unit=d.precio_unit,
            subtotal=d.subtotal,
            desde_recomendacion=d.desde_recomendacion,
        )
        for d in pedido.detalles
    ]

    return PedidoOut(
        id=pedido.id,
        numero=pedido.numero,
        cliente_id=pedido.cliente_id,
        vendedor_id=pedido.vendedor_id,
        estado=pedido.estado,
        subtotal=pedido.subtotal,
        impuesto=pedido.impuesto,
        descuento=pedido.descuento,
        total=pedido.total,
        forma_pago=pedido.forma_pago,
        notas=pedido.notas,
        creado_en=pedido.creado_en,
        detalles=detalles_out,
    )
