from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db
from backend.app.models import Producto, Usuario
from backend.app.routers.auth import get_current_user, require_admin
from backend.app.schemas import ProductoCreate, ProductoOut, StockUpdate

router = APIRouter(prefix="/productos", tags=["Productos"])

@router.get("", response_model=list[ProductoOut])
async def listar_productos(
    categoria: Optional[str] = Query(default=None),
    sede:      Optional[str] = Query(default=None),
    buscar:    Optional[str] = Query(default=None),
    skip:      int           = Query(default=0, ge=0),
    limit:     int           = Query(default=50, ge=1, le=2000),
    db:        AsyncSession  = Depends(get_db),
    _user:     Usuario       = Depends(get_current_user),
):
    q = select(Producto)
    if categoria: q = q.where(Producto.categoria_producto == categoria)
    if sede:      q = q.where(Producto.sede == sede)
    if buscar:    q = q.where(Producto.producto_id.ilike(f"%{buscar}%"))
    q = q.order_by(Producto.producto_id).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

@router.get("/{producto_id}", response_model=ProductoOut)
async def detalle_producto(
    producto_id: str,
    sede:  Optional[str] = Query(default=None),
    db:    AsyncSession = Depends(get_db),
    _user: Usuario      = Depends(get_current_user),
):
    q = select(Producto).where(Producto.producto_id == producto_id)
    if sede: q = q.where(Producto.sede == sede)
    prod = (await db.execute(q.limit(1))).scalar_one_or_none()
    if prod is None:
        raise HTTPException(404, f"Producto '{producto_id}' no encontrado.")
    return prod

@router.post("", response_model=ProductoOut, status_code=201)
async def crear_producto(
    data:   ProductoCreate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    ex = (await db.execute(select(Producto).where(
        Producto.producto_id == data.producto_id, Producto.sede == data.sede
    ))).scalar_one_or_none()
    if ex: raise HTTPException(409, f"Producto '{data.producto_id}' en sede '{data.sede}' ya existe.")
    prod = Producto(**data.model_dump())
    db.add(prod); await db.commit(); await db.refresh(prod)
    return prod

@router.patch("/{producto_id}/stock", response_model=ProductoOut)
async def agregar_stock(
    producto_id: str,
    sede:   str,
    data:   StockUpdate,
    db:     AsyncSession = Depends(get_db),
    _user:  Usuario      = Depends(get_current_user),
):
    prod = (await db.execute(select(Produto).where(
        Produto.produto_id == produto_id, Produto.sede == sede
    ))).scalar_one_or_none()
    if prod is None: raise HTTPException(404, f"Produto '{produto_id}' nao encontrado.")
    prod.stock += data.incremento
    await db.commit(); await db.refresh(prod)
    return prod
