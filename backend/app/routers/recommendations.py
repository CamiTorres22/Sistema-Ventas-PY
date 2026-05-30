"""
recommendations.py -- Endpoints de recomendacion

Lee las predicciones pre-calculadas desde Supabase (tabla predicciones)
generada por ml/batch_inference.py. FastAPI NO carga el modelo en memoria.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Usuario
from backend.app.routers.auth import get_current_user
from backend.app.schemas import DashboardResponse, ProductoRecomendado, RecomendacionResponse

router = APIRouter(prefix="/recomendar", tags=["Recomendaciones"])
DEFAULT_TOP_K = 10


async def _fetch_predictions(
    db: AsyncSession,
    cliente_id: str,
    top_k: int,
    filtro: str | None = None,
) -> list[dict]:
    """
    Lee predicciones desde Supabase via SQLAlchemy async.
    filtro: "urgentes" | "baja_rotacion" | "nuevos" | None
    """
    where_extra = ""
    if filtro == "urgentes":
        where_extra = "AND p.es_urgente = 1"
    elif filtro == "baja_rotacion":
        where_extra = "AND p.es_baja_rotacion = 1"
    elif filtro == "nuevos":
        where_extra = "AND p.es_nuevo = 1"

    sql = text(f"""
        SELECT
            p.cliente_id, p.producto_id,
            COALESCE(pr.nombre, p.producto_id) AS nombre,
            COALESCE(pr.categoria_producto, '') AS categoria_producto,
            COALESCE(pr.precio_unitario, 0.0)  AS precio_unitario,
            p.stock,
            p.score_final, p.ncf_score,
            p.s_urgency, p.s_rotation, p.s_novelty,
            p.es_urgente, p.es_nuevo, p.es_baja_rotacion,
            p.dias_para_vencer, p.dias_en_catalogo, p.rotacion_diaria,
            p.fecha_generacion
        FROM predicciones p
        LEFT JOIN productos pr ON pr.producto_id = p.producto_id
        WHERE p.cliente_id = :cliente_id
              {where_extra}
        ORDER BY p.score_final DESC
        LIMIT :top_k
    """)

    result = await db.execute(sql, {"cliente_id": cliente_id, "top_k": top_k})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def _get_fecha_calculo(db: AsyncSession, cliente_id: str) -> str | None:
    result = await db.execute(
        text("SELECT fecha_generacion FROM predicciones WHERE cliente_id = :cid LIMIT 1"),
        {"cid": cliente_id},
    )
    row = result.fetchone()
    return row[0] if row else None


def _rows_to_recomendados(rows: list[dict]) -> list[ProductoRecomendado]:
    return [
        ProductoRecomendado(
            producto_id=r["producto_id"],
            nombre=r["nombre"],
            categoria_producto=r["categoria_producto"],
            precio_unitario=r["precio_unitario"],
            stock=r["stock"],
            score_final=r["score_final"],
            ncf_score=r["ncf_score"],
            s_urgency=r["s_urgency"],
            s_rotation=r["s_rotation"],
            s_novelty=r["s_novelty"],
            es_urgente=bool(r["es_urgente"]),
            es_nuevo=bool(r["es_nuevo"]),
            es_baja_rotacion=bool(r["es_baja_rotacion"]),
            dias_para_vencer=r.get("dias_para_vencer"),
            dias_en_catalogo=r.get("dias_en_catalogo"),
            rotacion_diaria=r.get("rotacion_diaria"),
        )
        for r in rows
    ]


@router.get("/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_general(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Top-K recomendaciones generales (score_final sin filtro de tipo)."""
    rows  = await _fetch_predictions(db, cliente_id, top_k)
    prods = _rows_to_recomendados(rows)
    fecha = await _get_fecha_calculo(db, cliente_id)
    if not prods:
        raise HTTPException(404, f"No hay predicciones para el cliente '{cliente_id}'.")
    return RecomendacionResponse(
        cliente_id=cliente_id, tipo="general", total=len(prods),
        productos=prods, fecha_calculo=fecha,
    )


@router.get("/proximos-vencer/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_urgentes(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Productos proximos a vencer (es_urgente = 1)."""
    rows  = await _fetch_predictions(db, cliente_id, top_k, filtro="urgentes")
    prods = _rows_to_recomendados(rows)
    fecha = await _get_fecha_calculo(db, cliente_id)
    return RecomendacionResponse(
        cliente_id=cliente_id, tipo="urgentes", total=len(prods),
        productos=prods, fecha_calculo=fecha,
    )


@router.get("/baja-rotacion/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_baja_rotacion(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Productos con baja rotacion (es_baja_rotacion = 1)."""
    rows  = await _fetch_predictions(db, cliente_id, top_k, filtro="baja_rotacion")
    prods = _rows_to_recomendados(rows)
    fecha = await _get_fecha_calculo(db, cliente_id)
    return RecomendacionResponse(
        cliente_id=cliente_id, tipo="baja_rotacion", total=len(prods),
        productos=prods, fecha_calculo=fecha,
    )


@router.get("/nuevos/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_nuevos(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Productos nuevos en catalogo (es_nuevo = 1)."""
    rows  = await _fetch_predictions(db, cliente_id, top_k, filtro="nuevos")
    prods = _rows_to_recomendados(rows)
    fecha = await _get_fecha_calculo(db, cliente_id)
    return RecomendacionResponse(
        cliente_id=cliente_id, tipo="nuevos", total=len(prods),
        productos=prods, fecha_calculo=fecha,
    )


@router.get("/dashboard/{cliente_id}", response_model=DashboardResponse)
async def recomendar_dashboard(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard unificado: 3 secciones sin productos duplicados."""
    pool          = top_k * 3
    urgentes_rows = await _fetch_predictions(db, cliente_id, pool, filtro="urgentes")
    baja_rot_rows = await _fetch_predictions(db, cliente_id, pool, filtro="baja_rotacion")
    nuevos_rows   = await _fetch_predictions(db, cliente_id, pool, filtro="nuevos")
    fecha         = await _get_fecha_calculo(db, cliente_id)
    urgentes   = _rows_to_recomendados(urgentes_rows[:top_k])
    ids_usados = {p.producto_id for p in urgentes}
    baja_rotacion = _rows_to_recomendados(
        [r for r in baja_rot_rows if r["producto_id"] not in ids_usados][:top_k]
    )
    ids_usados |= {p.producto_id for p in baja_rotacion}
    nuevos = _rows_to_recomendados(
        [r for r in nuevos_rows if r["producto_id"] not in ids_usados][:top_k]
    )
    return DashboardResponse(
        cliente_id=cliente_id,
        urgentes=urgentes,
        baja_rotacion=baja_rotacion,
        nuevos=nuevos,
        total=len(urgentes) + len(baja_rotacion) + len(nuevos),
        fecha_calculo=fecha,
    )
