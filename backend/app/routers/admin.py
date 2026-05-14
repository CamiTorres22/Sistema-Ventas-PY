"""
admin.py — Panel de administración y métricas del modelo

Endpoints:
  GET /admin/metricas       → métricas del modelo NCF
  GET /admin/actividad      → actividad reciente del sistema
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Cliente, DetallePedido, LoginLog, Pedido, Producto, Usuario
from backend.app.routers.auth import require_admin
from backend.app.schemas import HealthResponse, MetricasModelo

router = APIRouter(prefix="/admin", tags=["Administración"])

ROOT_DIR     = Path(__file__).resolve().parent.parent.parent.parent
EVAL_PATH    = ROOT_DIR / "data" / "processed" / "eval_metrics.json"
TRAIN_PATH   = ROOT_DIR / "data" / "processed" / "train_metrics.json"
DB_PATH      = ROOT_DIR / "data" / "db" / "ico.db"


@router.get("/metricas", response_model=MetricasModelo)
async def metricas_modelo(
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Devuelve métricas del modelo NCF y del batch más reciente."""
    eval_data  = {}
    train_data = {}

    if EVAL_PATH.exists():
        with open(EVAL_PATH, encoding="utf-8") as f:
            eval_data = json.load(f)

    if TRAIN_PATH.exists():
        with open(TRAIN_PATH, encoding="utf-8") as f:
            train_data = json.load(f)

    # Contar usuarios y productos activos en BD
    n_usuarios = (await db.execute(
        select(func.count()).where(Usuario.activo == True)
    )).scalar_one()
    n_productos = (await db.execute(
        select(func.count()).where(Producto.activo == True)
    )).scalar_one()

    # Fecha del último batch
    fecha_batch = None
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT MAX(fecha_generacion) FROM predicciones"
        ).fetchone()
        conn.close()
        if row:
            fecha_batch = row[0]

    # Tasa de conversión: pedidos con ≥1 ítem de recomendación / total pedidos
    total_pedidos = (await db.execute(select(func.count(Pedido.id)))).scalar_one()
    pedidos_con_rec = (await db.execute(
        select(func.count(Pedido.id.distinct()))
        .join(DetallePedido, DetallePedido.pedido_id == Pedido.id)
        .where(DetallePedido.desde_recomendacion == True)
    )).scalar_one()

    tasa_conversion = round(pedidos_con_rec / total_pedidos, 4) if total_pedidos > 0 else None

    return MetricasModelo(
        ndcg_at_10=eval_data.get("NDCG@10"),
        hitrate_at_10=eval_data.get("HitRate@10"),
        precision_at_10=eval_data.get("Precision@10"),
        tasa_conversion=tasa_conversion,
        rotation_coverage=None,   # calculado en evaluate.py si se añade
        n_usuarios=n_usuarios,
        n_productos=n_productos,
        fecha_entrenamiento=str(train_data.get("fecha_entrenamiento", "")),
        fecha_ultimo_batch=fecha_batch,
    )


@router.get("/actividad")
async def actividad_reciente(
    limit:  int  = 10,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Actividad reciente: últimos pedidos, productos y clientes creados."""
    pedidos_res = await db.execute(
        select(Pedido, Usuario, Cliente)
        .join(Usuario, Usuario.id == Pedido.vendedor_id)
        .join(Cliente, Cliente.cliente_id == Pedido.cliente_id)
        .order_by(Pedido.creado_en.desc())
        .limit(limit)
    )
    pedidos = pedidos_res.all()

    actividad = []
    for pedido, vendedor, cliente in pedidos:
        actividad.append({
            "accion":  "Pedido registrado",
            "usuario": vendedor.nombre,
            "fecha":   pedido.creado_en.isoformat(),
            "detalle": f"{cliente.nombre} — S/. {pedido.total:.2f}",
        })

    return {"actividad": actividad}


@router.get("/logs")
async def login_logs(
    limit:  int  = 50,
    solo_fallidos: bool = False,
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    """Historial de intentos de sesión (exitosos y fallidos)."""
    q = select(LoginLog).order_by(LoginLog.creado_en.desc())
    if solo_fallidos:
        q = q.where(LoginLog.exitoso == False)
    q = q.limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [
        {
            "id":           l.id,
            "email":        l.email,
            "nombre":       l.nombre,
            "rol":          l.rol,
            "exitoso":      l.exitoso,
            "motivo_fallo": l.motivo_fallo,
            "ip_address":   l.ip_address,
            "user_agent":   l.user_agent,
            "creado_en":    l.creado_en.isoformat(),
        }
        for l in logs
    ]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Estado general del sistema."""
    modelo_cargado = (ROOT_DIR / "data" / "processed" / "modelo_ncf.pt").exists()
    batch_ok       = DB_PATH.exists()

    return HealthResponse(
        status="ok" if modelo_cargado and batch_ok else "degraded",
        modelo_cargado=modelo_cargado,
        batch_disponible=batch_ok,
        mensaje=(
            "Sistema operativo." if modelo_cargado and batch_ok
            else "Falta modelo o predicciones. Ejecutar train.py y batch_inference.py."
        ),
    )
