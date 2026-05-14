"""
products.py — CRUD de productos

Endpoints:
  GET    /productos              → listar catálogo (con filtros)
  GET    /productos/{id}         → detalle de un producto
  POST   /productos              → agregar producto [admin]
  PATCH  /productos/{id}         → editar producto [admin]
  PATCH  /productos/{id}/stock   → agregar stock [admin]
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Producto, Usuario
from backend.app.routers.auth import get_current_user, require_admin
from backend.app.schemas import ProductoCreate, ProductoOut, ProductoUpdate, StockUpdate

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("", response_model=list[ProductoOut])
async def listar_productos(
    categoria:    Optional[str] = Query(default=None),
    sede:         Optional[str] = Query(default=None),
    buscar:       Optional[str] = Query(default=None, description="Buscar por nombre o ID"),
    solo_activos: bool          = Query(default=True),
    skip:         int           = Query(default=0, ge=0),
    limit:        int           = Query(default=50, ge=1, le=2000),
    db:           AsyncSession  = Depends(get_db),
    _user:        Usuario       = Depends(get_current_user),
):
    """Lista el catálogo de productos con filtros opcionales."""
    q = select(Producto)

    if solo_activos:
        q = q.where(Producto.activo == True)
    if categoria:
        q = q.where(Producto.categoria_producto == categoria)
    if sede:
        q = q.where(Producto.sede == sede)
    if buscar:
        q = q.where(or_(
            Producto.nombre.ilike(f"%{buscar}%"),
            Producto.producto_id.ilike(f"%{buscar}%"),
        ))

    q = q.order_by(Producto.nombre).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{producto_id}", response_model=ProductoOut)
async def detalle_producto(
    producto_id: str,
    db:    AsyncSession = Depends(get_db),
    _user: Usuario      = Depends(get_current_user),
):
    result = await db.execute(
        select(Producto).where(Producto.producto_id == producto_id)
    )
    prod = result.scalar_one_or_none()
    if prod is None:
        raise HTTPException(404, f"Producto '{producto_id}' no encontrado.")
    return prod


@router.post("", response_model=ProductoOut, status_code=201)
async def crear_producto(
    data:  ProductoCreate,
    db:    AsyncSession = Depends(get_db),
    _admin: Usuario    = Depends(require_admin),
):
    """Agrega un nuevo producto al catálogo. Solo administradores."""
    existing = await db.execute(
        select(Producto).where(Producto.producto_id == data.producto_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"El producto '{data.producto_id}' ya existe.")

    prod_data = data.model_dump()
    if not prod_data.get("fecha_ingreso_catalogo"):
        prod_data["fecha_ingreso_catalogo"] = date.today().isoformat()
    prod = Producto(**prod_data, rotacion_diaria=0.0, baja_rotacion=0)
    db.add(prod)
    await db.commit()
    await db.refresh(prod)
    return prod


@router.patch("/{producto_id}", response_model=ProductoOut)
async def editar_producto(
    producto_id: str,
    data:   ProductoUpdate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Edita los datos de un producto. Solo administradores."""
    result = await db.execute(
        select(Producto).where(Producto.producto_id == producto_id)
    )
    prod = result.scalar_one_or_none()
    if prod is None:
        raise HTTPException(404, f"Producto '{producto_id}' no encontrado.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prod, field, value)

    await db.commit()
    await db.refresh(prod)
    return prod


@router.patch("/{producto_id}/stock", response_model=ProductoOut)
async def agregar_stock(
    producto_id: str,
    data:   StockUpdate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Incrementa el stock disponible de un producto. Solo administradores."""
    result = await db.execute(
        select(Producto).where(Producto.producto_id == producto_id)
    )
    prod = result.scalar_one_or_none()
    if prod is None:
        raise HTTPException(404, f"Producto '{producto_id}' no encontrado.")

    prod.stock += data.incremento
    await db.commit()
    await db.refresh(prod)
    return prod
