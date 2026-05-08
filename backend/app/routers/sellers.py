"""
sellers.py — Gestión de vendedores (solo admin)

Endpoints:
  GET    /vendedores             → lista todos los vendedores
  POST   /vendedores             → registrar vendedor [admin]
  PATCH  /vendedores/{id}        → editar vendedor [admin]
  GET    /vendedores/{id}/cartera → clientes asignados a un vendedor
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Cliente, ClienteVendedor, Usuario
from backend.app.routers.auth import get_current_user, hash_password, require_admin
from backend.app.schemas import ClienteOut, UsuarioOut, VendedorCreate, VendedorUpdate

router = APIRouter(prefix="/vendedores", tags=["Vendedores"])


@router.get("", response_model=list[UsuarioOut])
async def listar_vendedores(
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    result = await db.execute(
        select(Usuario).where(Usuario.rol == "vendedor").order_by(Usuario.nombre)
    )
    return result.scalars().all()


@router.post("", response_model=UsuarioOut, status_code=201)
async def crear_vendedor(
    data:   VendedorCreate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Registra un nuevo vendedor o administrador."""
    existing = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"El email '{data.email}' ya está registrado.")

    user = Usuario(
        nombre=data.nombre,
        email=data.email,
        hashed_password=hash_password(data.password),
        rol=data.rol,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{vendedor_id}", response_model=UsuarioOut)
async def editar_vendedor(
    vendedor_id: int,
    data:   VendedorUpdate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    result = await db.execute(select(Usuario).where(Usuario.id == vendedor_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, f"Vendedor ID {vendedor_id} no encontrado.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{vendedor_id}/cartera", response_model=list[ClienteOut])
async def cartera_vendedor(
    vendedor_id: int,
    db:          AsyncSession = Depends(get_db),
    current_user: Usuario     = Depends(get_current_user),
):
    """Lista los clientes asignados a un vendedor.
    Acceso: admin (cualquier vendedor) o el propio vendedor."""
    if current_user.rol != "admin" and current_user.id != vendedor_id:
        raise HTTPException(status_code=403, detail="Acceso no permitido.")

    result = await db.execute(
        select(Cliente)
        .join(ClienteVendedor, ClienteVendedor.cliente_id == Cliente.cliente_id)
        .where(ClienteVendedor.vendedor_id == vendedor_id)
        .where(ClienteVendedor.activo == True)
        .order_by(Cliente.nombre)
    )
    return result.scalars().all()
