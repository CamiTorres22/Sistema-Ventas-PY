"""
recommendations.py — Endpoints de recomendación

Lee las predicciones pre-calculadas desde SQLite (tabla `predicciones`)
generada por ml/batch_inference.py. FastAPI NO carga el modelo en memoria.

Endpoints:
  GET /recomendar/{cliente_id}                     → Top-K general
  GET /recomendar/dashboard/{cliente_id}           → 3 secciones sin duplicados
  GET /recomendar/proximos-vencer/{cliente_id}     → solo urgentes
  GET /recomendar/baja-rotacion/{cliente_id}       → solo baja rotación
  GET /recomendar/nuevos/{cliente_id}              → solo nuevos
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Producto, Usuario
from backend.app.routers.auth import get_current_user
from backend.app.schemas import DashboardResponse, ProductoRecomendado, RecomendacionResponse

router = APIRouter(prefix="/recomendar", tags=["Recomendaciones"])

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH  = ROOT_DIR / "data" / "db" / "ico.db"

DEFAULT_TOP_K = 10


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: leer predicciones desde SQLite
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_predictions(
    cliente_id: str,
    top_k: int,
    filtro: str | None = None,   # "urgentes" | "baja_rotacion" | "nuevos" | None
    db_path: Path = DB_PATH,
) -> list[dict]:
    """
    Ejecuta un SELECT en la tabla predicciones.
    Une con la tabla productos para obtener el nombre del producto.
    """
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Predicciones no disponibles. Ejecuta ml/batch_inference.py primero.",
        )

    where_extra = ""
    if filtro == "urgentes":
        where_extra = "AND p.es_urgente = 1"
    elif filtro == "baja_rotacion":
        where_extra = "AND p.es_baja_rotacion = 1"
    elif filtro == "nuevos":
        where_extra = "AND p.es_nuevo = 1"

    sql = f"""
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
        WHERE p.cliente_id = ?
              {where_extra}
        ORDER BY p.score_final DESC
        LIMIT ?
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, (cliente_id, top_k)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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


def _get_fecha_calculo(cliente_id: str, db_path: Path = DB_PATH) -> str | None:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT fecha_generacion FROM predicciones WHERE cliente_id = ? LIMIT 1",
        (cliente_id,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_general(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
):
    """Top-K recomendaciones generales (score_final sin filtro de tipo)."""
    rows    = _fetch_predictions(cliente_id, top_k)
    prods   = _rows_to_recomendados(rows)
    fecha   = _get_fecha_calculo(cliente_id)

    if not prods:
        raise HTTPException(404, f"No hay predicciones para el cliente '{cliente_id}'.")

    return RecomendacionResponse(
        cliente_id=cliente_id,
        tipo="general",
        total=len(prods),
        productos=prods,
        fecha_calculo=fecha,
    )


@router.get("/proximos-vencer/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_urgentes(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
):
    """Productos próximos a vencer (es_urgente = 1)."""
    rows  = _fetch_predictions(cliente_id, top_k, filtro="urgentes")
    prods = _rows_to_recomendados(rows)
    fecha = _get_fecha_calculo(cliente_id)

    return RecomendacionResponse(
        cliente_id=cliente_id,
        tipo="urgentes",
        total=len(prods),
        productos=prods,
        fecha_calculo=fecha,
    )


@router.get("/baja-rotacion/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_baja_rotacion(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
):
    """Productos con baja rotación (es_baja_rotacion = 1)."""
    rows  = _fetch_predictions(cliente_id, top_k, filtro="baja_rotacion")
    prods = _rows_to_recomendados(rows)
    fecha = _get_fecha_calculo(cliente_id)

    return RecomendacionResponse(
        cliente_id=cliente_id,
        tipo="baja_rotacion",
        total=len(prods),
        productos=prods,
        fecha_calculo=fecha,
    )


@router.get("/nuevos/{cliente_id}", response_model=RecomendacionResponse)
async def recomendar_nuevos(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
):
    """Productos nuevos en catálogo (es_nuevo = 1)."""
    rows  = _fetch_predictions(cliente_id, top_k, filtro="nuevos")
    prods = _rows_to_recomendados(rows)
    fecha = _get_fecha_calculo(cliente_id)

    return RecomendacionResponse(
        cliente_id=cliente_id,
        tipo="nuevos",
        total=len(prods),
        productos=prods,
        fecha_calculo=fecha,
    )


@router.get("/dashboard/{cliente_id}", response_model=DashboardResponse)
async def recomendar_dashboard(
    cliente_id: str,
    top_k: int = Query(default=DEFAULT_TOP_K, ge=1, le=50),
    _user: Usuario = Depends(get_current_user),
):
    """
    Dashboard unificado: 3 secciones sin productos duplicados.
    Jerarquía de asignación: urgentes → baja_rotacion → nuevos.
    """
    pool = top_k * 3   # pool amplio para asegurar top_k por sección tras exclusión

    # Obtener candidatos por sección
    urgentes_rows  = _fetch_predictions(cliente_id, pool, filtro="urgentes")
    baja_rot_rows  = _fetch_predictions(cliente_id, pool, filtro="baja_rotacion")
    nuevos_rows    = _fetch_predictions(cliente_id, pool, filtro="nuevos")
    fecha          = _get_fecha_calculo(cliente_id)

    # Asignación sin duplicados (cascada)
    urgentes = _rows_to_recomendados(urgentes_rows[:top_k])
    ids_usados = {p.producto_id for p in urgentes}

    baja_rotacion = _rows_to_recomendados([
        r for r in baja_rot_rows if r["producto_id"] not in ids_usados
    ][:top_k])
    ids_usados |= {p.producto_id for p in baja_rotacion}

    nuevos = _rows_to_recomendados([
        r for r in nuevos_rows if r["producto_id"] not in ids_usados
    ][:top_k])

    return DashboardResponse(
        cliente_id=cliente_id,
        urgentes=urgentes,
        baja_rotacion=baja_rotacion,
        nuevos=nuevos,
        total=len(urgentes) + len(baja_rotacion) + len(nuevos),
        fecha_calculo=fecha,
    )
