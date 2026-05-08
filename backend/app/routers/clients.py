"""
clients.py — Gestión de clientes y asignación a vendedores

Endpoints:
  GET    /clientes                    → cartera del vendedor autenticado
  GET    /clientes/{id}               → detalle de un cliente
  POST   /clientes                    → crear cliente [admin]
  PATCH  /clientes/{id}               → editar cliente [admin]
  POST   /clientes/{id}/asignar       → asignar cliente a vendedor [admin]
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Cliente, ClienteVendedor, Usuario
from backend.app.routers.auth import get_current_user, require_admin
from backend.app.schemas import ClienteCreate, ClienteOut, ClienteUpdate

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(
    buscar: Optional[str] = Query(default=None, description="Buscar por nombre"),
    sede:   Optional[str] = Query(default=None),
    tipo:   Optional[str] = Query(default=None),
    skip:   int           = Query(default=0, ge=0),
    limit:  int           = Query(default=50, ge=1, le=5000),
    db:     AsyncSession  = Depends(get_db),
    user:   Usuario       = Depends(get_current_user),
):
    """
    Vendedor: devuelve su cartera asignada.
    Admin: devuelve todos los clientes con su vendedor asignado actual.
    """
    if user.rol == "admin":
        # Subconsulta correlacionada: obtiene el vendedor activo de cada cliente
        vendedor_subq = (
            select(ClienteVendedor.vendedor_id)
            .where(ClienteVendedor.cliente_id == Cliente.cliente_id)
            .where(ClienteVendedor.activo == True)
            .limit(1)
            .scalar_subquery()
        )

        q = select(Cliente, vendedor_subq.label("cv_vendedor_id")).where(
            Cliente.activo == True
        )

        if buscar:
            q = q.where(Cliente.nombre.ilike(f"%{buscar}%"))
        if sede:
            q = q.where(Cliente.sede_cliente == sede)
        if tipo:
            q = q.where(Cliente.tipo == tipo)

        q = q.order_by(Cliente.nombre).offset(skip).limit(limit)
        result = await db.execute(q)
        rows = result.all()
        return [
            ClienteOut.model_validate(c).model_copy(update={"vendedor_id": vid})
            for c, vid in rows
        ]
    else:
        # Solo los clientes asignados a este vendedor
        q = (
            select(Cliente)
            .join(ClienteVendedor, ClienteVendedor.cliente_id == Cliente.cliente_id)
            .where(ClienteVendedor.vendedor_id == user.id)
            .where(ClienteVendedor.activo == True)
            .where(Cliente.activo == True)
        )

        if buscar:
            q = q.where(Cliente.nombre.ilike(f"%{buscar}%"))
        if sede:
            q = q.where(Cliente.sede_cliente == sede)
        if tipo:
            q = q.where(Cliente.tipo == tipo)

        q = q.order_by(Cliente.nombre).offset(skip).limit(limit)
        result = await db.execute(q)
        return result.scalars().all()


@router.get("/{cliente_id}", response_model=ClienteOut)
async def detalle_cliente(
    cliente_id: str,
    db:   AsyncSession = Depends(get_db),
    user: Usuario      = Depends(get_current_user),
):
    result = await db.execute(
        select(Cliente).where(Cliente.cliente_id == cliente_id)
    )
    cliente = result.scalar_one_or_none()
    if cliente is None:
        raise HTTPException(404, f"Cliente '{cliente_id}' no encontrado.")
    return cliente


@router.post("", response_model=ClienteOut, status_code=201)
async def crear_cliente(
    data:   ClienteCreate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Crea un nuevo cliente. Solo administradores."""
    existing = await db.execute(
        select(Cliente).where(Cliente.cliente_id == data.cliente_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Cliente '{data.cliente_id}' ya existe.")

    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.patch("/{cliente_id}", response_model=ClienteOut)
async def editar_cliente(
    cliente_id: str,
    data:   ClienteUpdate,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Edita los datos de un cliente. Solo administradores."""
    result = await db.execute(
        select(Cliente).where(Cliente.cliente_id == cliente_id)
    )
    cliente = result.scalar_one_or_none()
    if cliente is None:
        raise HTTPException(404, f"Cliente '{cliente_id}' no encontrado.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(cliente, field, value)

    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.post("/{cliente_id}/asignar", status_code=200)
async def asignar_cliente(
    cliente_id:  str,
    vendedor_id: int,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Asigna un cliente a un vendedor. Solo administradores."""
    # Verificar que el cliente existe
    res_c = await db.execute(select(Cliente).where(Cliente.cliente_id == cliente_id))
    if not res_c.scalar_one_or_none():
        raise HTTPException(404, f"Cliente '{cliente_id}' no encontrado.")

    # Verificar que el vendedor existe
    res_v = await db.execute(select(Usuario).where(Usuario.id == vendedor_id))
    if not res_v.scalar_one_or_none():
        raise HTTPException(404, f"Vendedor ID {vendedor_id} no encontrado.")

    # Eliminar todas las asignaciones anteriores del cliente (sin importar estado)
    await db.execute(
        update(ClienteVendedor)
        .where(ClienteVendedor.cliente_id == cliente_id)
        .values(activo=False),
        execution_options={"synchronize_session": False},
    )

    # Buscar si ya existe fila para este par exacto (tomar solo la primera)
    res_a = await db.execute(
        select(ClienteVendedor)
        .where(
            ClienteVendedor.cliente_id  == cliente_id,
            ClienteVendedor.vendedor_id == vendedor_id,
        )
        .limit(1)
    )
    asig = res_a.scalar_one_or_none()

    if asig:
        asig.activo = True
    else:
        db.add(ClienteVendedor(cliente_id=cliente_id, vendedor_id=vendedor_id))

    await db.commit()
    return {"detail": f"Cliente '{cliente_id}' asignado al vendedor {vendedor_id}."}
