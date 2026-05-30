from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database import get_db
from backend.app.models import Cliente, LoginLog, Producto, Usuario, Venta
from backend.app.routers.auth import require_admin
from backend.app.schemas import HealthResponse, MetricasModelo

router = APIRouter(prefix="/admin", tags=["Admin"])
ROOT_DIR  = Path(__file__).resolve().parent.parent.parent.parent
EVAL_PATH = ROOT_DIR / "data" / "processed" / "eval_metrics.json"

@router.get("/metricas", response_model=MetricasModelo)
async def metricas_modelo(
    db:     AsyncSession = Depends(get_db),
    _admin: Usuario      = Depends(require_admin),
):
    eval_data = json.loads(EVAL_PATH.read_text()) if EVAL_PATH.exists() else {}
    n_usuarios = (await db.execute(select(func.count()).select_from(Usuario))).scalar_one()
    n_productos = (await db.execute(select(func.count()).select_from(Producto))).scalar_one()
    fecha_batch = None
    try:
        row = (await db.execute(text("SELECT MAX(fecha_generacion) FROM predicciones"))).fetchone()
        if row: fecha_batch = row[0]
    except Exception:
        pass
    return MetricasModelo(
        ndcg_at_10=eval_data.get("NDCG@10"),
        hitrate_at_10=eval_data.get("HitRate@10"),
        n_usuarios=n_usuarios, n_productos=n_productos,
        fecha_ultimo_batch=fecha_batch,
    )

@router.get("/actividad")
async def actividad_reciente(
    limit: int = 10,
    db:    AsyncSession = Depends(get_db),
    _admin: Usuario     = Depends(require_admin),
):
    result = await db.execute(
        select(Venta).order_by(Venta.fecha_venta.desc()).limit(limit)
    )
    ventas = result.scalars().all()
    return [{"venta_id": v.venta_id, "cliente_id": v.cliente_id,
             "fecha_venta": v.fecha_venta, "monto_total": v.monto_total} for v in ventas]

@router.get("/logs")
async def login_logs(
    limit: int = 50,
    db:    AsyncSession = Depends(get_db),
    _admin: Usuario     = Depends(require_admin),
):
    result = await db.execute(select(LoginLog).order_by(LoginLog.creado_en.desc()).limit(limit))
    return [{"id": l.id, "email": l.email, "exitoso": l.exitoso,
             "motivo_fallo": l.motivo_fallo, "creado_en": str(l.creado_en)} for l in result.scalars()]

@router.get("/health", response_model=HealthResponse)
async def health_check():
    modelo_ok = (ROOT_DIR / "data" / "processed" / "modelo_ncf.pt").exists()
    return HealthResponse(status="ok", modelo_cargado=modelo_ok,
                         batch_disponible=True,
                         mensaje="Sistema operativo." if modelo_ok else "Sin modelo ML. Ejecutar train.py.")
