"""
clean.py — ETL: SQLite (o dataset_ml.csv) → artefactos de entrada para NeuMF

Genera los 3 archivos que necesita el pipeline de ML:
  1. pares_entrenamiento.parquet  — interacciones implícitas + negative sampling (1:4)
  2. contexto_productos.parquet   — metadatos de productos para business scores
  3. indices.json                 — mapeo cliente_id/producto_id ↔ índice entero

FUENTES DE DATOS:
  --source db   (por defecto) → lee pedidos + detalle_pedido + productos de ico.db
                                 Solo pedidos con creado_en < hoy y estado != cancelado
  --source csv  → lee data/processed/dataset_ml.csv (comportamiento original)

CÓMO EJECUTAR:
    python ml/clean.py                   # lee desde SQLite (recomendado)
    python ml/clean.py --source csv      # lee desde dataset_ml.csv
    python ml/clean.py --out data/processed/
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rutas por defecto ──────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).resolve().parent.parent
DATASET_PATH  = ROOT_DIR / "data" / "processed" / "dataset_ml.csv"
DB_PATH       = ROOT_DIR / "data" / "db" / "ico.db"
OUTPUT_DIR    = ROOT_DIR / "data" / "processed"

# ── Parámetros ─────────────────────────────────────────────────────────────────
NEG_RATIO     = 4       # negativos por cada positivo (1:4)
TAU_DIAS      = 180     # media-vida de recencia (días)
RANDOM_SEED   = 42


# ──────────────────────────────────────────────────────────────────────────────
# 1. CARGA Y VALIDACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def load_from_db(db_path: Path) -> pd.DataFrame:
    """
    Carga el historial de compras directamente desde SQLite (ico.db).

    JOIN: pedidos × detalle_pedido × productos
    Filtros:
      - pedidos.creado_en < hoy      (no incluir pedidos futuros/en curso)
      - pedidos.estado != 'cancelado'

    Devuelve un DataFrame con las mismas columnas que dataset_ml.csv
    para que el resto del pipeline sea idéntico.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"No se encontró la BD en {db_path}. "
            "Ejecuta seed.py y migrate_historical.py primero."
        )

    logger.info("Cargando datos desde SQLite: %s ...", db_path)

    conn = sqlite3.connect(db_path)

    query = """
        SELECT
            p.cliente_id,
            dp.producto_id,
            p.creado_en                  AS fecha_venta,
            pr.categoria_producto,
            pr.precio_unitario,
            pr.costo_unitario            AS COSTO_UNITARIO,
            pr.stock,
            pr.dias_en_stock,
            pr.sede,
            pr.fecha_ingreso_catalogo,
            pr.fecha_min_caducidad,
            pr.rotacion_diaria,
            pr.baja_rotacion
        FROM pedidos p
        JOIN detalle_pedido dp ON dp.pedido_id = p.id
        JOIN productos pr      ON pr.producto_id = dp.producto_id
        WHERE p.estado != 'cancelado'
          AND DATE(p.creado_en) < DATE('now')
          AND pr.activo = 1
    """

    df = pd.read_sql_query(
        query,
        conn,
        parse_dates=["fecha_venta", "fecha_ingreso_catalogo", "fecha_min_caducidad"],
    )
    conn.close()

    # dias_para_vencer: calculado respecto a hoy
    FECHA_HOY = pd.Timestamp(date.today())
    df["dias_para_vencer"] = (
        pd.to_datetime(df["fecha_min_caducidad"]) - FECHA_HOY
    ).dt.days

    logger.info(
        "Datos cargados desde BD: %d filas | %d clientes | %d productos",
        len(df), df["cliente_id"].nunique(), df["producto_id"].nunique(),
    )
    return df


def load_dataset(path: Path) -> pd.DataFrame:
    logger.info("Cargando dataset desde %s ...", path)
    df = pd.read_csv(
        path,
        parse_dates=["fecha_venta", "fecha_ingreso_catalogo", "fecha_min_caducidad"],
    )
    logger.info(
        "Dataset cargado: %d filas | %d clientes | %d productos",
        len(df), df["cliente_id"].nunique(), df["producto_id"].nunique(),
    )
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 2. ÍNDICES — mapeo ID string ↔ entero (requerido por los embeddings)
# ──────────────────────────────────────────────────────────────────────────────

def build_indices(df: pd.DataFrame) -> tuple[dict, dict, dict, dict]:
    """
    Construye los mapas cliente_id ↔ int e producto_id ↔ int.
    El orden es determinístico (sorted) para reproducibilidad entre runs.

    Returns:
        user2idx, idx2user, item2idx, idx2item
    """
    clientes  = sorted(df["cliente_id"].unique())
    productos = sorted(df["producto_id"].unique())

    user2idx = {c: i for i, c in enumerate(clientes)}
    idx2user = {i: c for c, i in user2idx.items()}
    item2idx = {p: j for j, p in enumerate(productos)}
    idx2item = {j: p for p, j in item2idx.items()}

    logger.info(
        "Índices: %d clientes (0..%d) | %d productos (0..%d)",
        len(user2idx), len(user2idx) - 1,
        len(item2idx), len(item2idx) - 1,
    )
    return user2idx, idx2user, item2idx, idx2item


# ──────────────────────────────────────────────────────────────────────────────
# 3. PARES DE ENTRENAMIENTO — interacciones implícitas + negative sampling
# ──────────────────────────────────────────────────────────────────────────────

def build_training_pairs(
    df: pd.DataFrame,
    user2idx: dict,
    item2idx: dict,
    neg_ratio: int = NEG_RATIO,
    tau_dias: int = TAU_DIAS,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Construye el dataset de pares (usuario, ítem, label, weight) para entrenar NeuMF.

    Positivos (label=1):
        Cada par (cliente_id, producto_id) del historial de compras.
        weight = w_recency = exp(-dias_desde_venta / tau_dias)
        Pares duplicados (mismo cliente, mismo producto en distintas ventas)
        se agregan sumando sus pesos: el mismo ítem comprado muchas veces
        debe tener mayor peso total.

    Negativos (label=0):
        Por cada positivo, se samplea 'neg_ratio' ítems que el cliente
        NUNCA ha comprado. weight = 1.0 (sin peso de recencia).
    """
    rng = np.random.default_rng(seed)
    FECHA_HOY = pd.Timestamp(date.today())

    logger.info("Construyendo interacciones positivas ...")
    df = df.copy()
    df["dias_desde_venta"] = (FECHA_HOY - df["fecha_venta"]).dt.days.clip(lower=0)
    df["w_recency"] = np.exp(-df["dias_desde_venta"] / tau_dias)

    # Agregar por (cliente, producto): sumar pesos de recencia
    pos = (
        df.groupby(["cliente_id", "producto_id"])
        .agg(weight=("w_recency", "sum"))
        .reset_index()
    )
    pos["label"] = 1
    pos["user_idx"] = pos["cliente_id"].map(user2idx)
    pos["item_idx"] = pos["producto_id"].map(item2idx)

    logger.info("Positivos: %d pares únicos (cliente × producto)", len(pos))

    # Historial por cliente (set de ítems ya comprados)
    historial = (
        pos.groupby("user_idx")["item_idx"]
        .apply(set)
        .to_dict()
    )

    all_items = np.array(sorted(item2idx.values()))
    n_items   = len(all_items)

    # ── Negative sampling ──────────────────────────────────────────────────────
    logger.info(
        "Negative sampling (ratio 1:%d) → generando ~%d negativos ...",
        neg_ratio, len(pos) * neg_ratio,
    )
    neg_rows = []
    for _, row in pos.iterrows():
        u = int(row["user_idx"])
        comprados = historial.get(u, set())

        # Candidatos negativos: todos los ítems NO comprados por este cliente
        candidatos = all_items[~np.isin(all_items, list(comprados))]
        n_neg = min(neg_ratio, len(candidatos))
        sampled = rng.choice(candidatos, size=n_neg, replace=False)

        for j in sampled:
            neg_rows.append({
                "user_idx": u,
                "item_idx": int(j),
                "label":    0,
                "weight":   1.0,
            })

    neg_df = pd.DataFrame(neg_rows)
    logger.info("Negativos generados: %d", len(neg_df))

    # ── Combinar y mezclar ─────────────────────────────────────────────────────
    pos_out = pos[["user_idx", "item_idx", "label", "weight"]].copy()
    pares   = pd.concat([pos_out, neg_df], ignore_index=True)
    pares   = pares.sample(frac=1, random_state=seed).reset_index(drop=True)

    pares["user_idx"] = pares["user_idx"].astype(np.int32)
    pares["item_idx"] = pares["item_idx"].astype(np.int32)
    pares["label"]    = pares["label"].astype(np.float32)
    pares["weight"]   = pares["weight"].astype(np.float32)

    logger.info(
        "Total pares de entrenamiento: %d (%.1f%% positivos)",
        len(pares), pares["label"].mean() * 100,
    )
    return pares


# ──────────────────────────────────────────────────────────────────────────────
# 4. CONTEXTO DE PRODUCTOS — metadatos para business scores
# ──────────────────────────────────────────────────────────────────────────────

def build_product_context(
    df: pd.DataFrame,
    item2idx: dict,
) -> pd.DataFrame:
    """
    Construye el maestro de productos con las features necesarias para
    calcular los business scores en batch_inference.py.

    Una fila por producto. Cuando un producto aparece en varias sedes,
    se toma la fila con mayor stock disponible (máxima disponibilidad).
    """
    FECHA_HOY = pd.Timestamp(date.today())

    cols = [
        "producto_id", "categoria_producto",
        "precio_unitario", "COSTO_UNITARIO",
        "stock", "dias_en_stock",
        "fecha_ingreso_catalogo", "fecha_min_caducidad",
        "dias_para_vencer", "rotacion_diaria", "baja_rotacion",
    ]

    ctx = (
        df[cols]
        .sort_values("stock", ascending=False)
        .drop_duplicates("producto_id", keep="first")
        .copy()
    )

    # Recalcular dias_para_vencer con fecha de hoy
    ctx["dias_para_vencer"] = (
        ctx["fecha_min_caducidad"] - FECHA_HOY
    ).dt.days.astype(int)

    # días desde ingreso al catálogo
    ctx["dias_en_catalogo"] = (
        FECHA_HOY - ctx["fecha_ingreso_catalogo"]
    ).dt.days.clip(lower=0).astype(int)

    # margen porcentual
    ctx["margen_pct"] = (
        (ctx["precio_unitario"] - ctx["COSTO_UNITARIO"])
        / ctx["precio_unitario"]
    ).clip(0, 1).round(4)

    # índice entero para alinear con los embeddings
    ctx["item_idx"] = ctx["producto_id"].map(item2idx)
    ctx = ctx.dropna(subset=["item_idx"])
    ctx["item_idx"] = ctx["item_idx"].astype(np.int32)

    # Percentil 25 de rotación (umbral de baja rotación)
    p25 = ctx["rotacion_diaria"].quantile(0.25)
    ctx["rot_p25"] = p25   # mismo valor en todas las filas para facilitar lectura

    logger.info(
        "Contexto de productos: %d productos únicos | p25 rotación: %.4f",
        len(ctx), p25,
    )
    return ctx.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# 5. GUARDADO
# ──────────────────────────────────────────────────────────────────────────────

def save_artefacts(
    pares: pd.DataFrame,
    ctx: pd.DataFrame,
    user2idx: dict,
    idx2user: dict,
    item2idx: dict,
    idx2item: dict,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    pares_path = out_dir / "pares_entrenamiento.parquet"
    ctx_path   = out_dir / "contexto_productos.parquet"
    idx_path   = out_dir / "indices.json"

    pares.to_parquet(pares_path, index=False)
    logger.info("Guardado: %s (%d filas)", pares_path, len(pares))

    ctx.to_parquet(ctx_path, index=False)
    logger.info("Guardado: %s (%d productos)", ctx_path, len(ctx))

    indices = {
        "n_users":  len(user2idx),
        "n_items":  len(item2idx),
        "user2idx": user2idx,
        "idx2user": {str(k): v for k, v in idx2user.items()},
        "item2idx": item2idx,
        "idx2item": {str(k): v for k, v in idx2item.items()},
    }
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(indices, f, ensure_ascii=False, indent=2)
    logger.info("Guardado: %s (%d usuarios, %d ítems)", idx_path, len(user2idx), len(item2idx))


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main(source: str, dataset_path: Path, db_path: Path, out_dir: Path) -> None:
    if source == "db":
        df = load_from_db(db_path)
    else:
        df = load_dataset(dataset_path)

    user2idx, idx2user, item2idx, idx2item = build_indices(df)
    pares = build_training_pairs(df, user2idx, item2idx)
    ctx   = build_product_context(df, item2idx)

    save_artefacts(pares, ctx, user2idx, idx2user, item2idx, idx2item, out_dir)
    logger.info("ETL completado exitosamente.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL NeuMF — ICO Distribuidora")
    parser.add_argument(
        "--source", choices=["db", "csv"], default="db",
        help="Fuente de datos: 'db' = SQLite ico.db (recomendado) | 'csv' = dataset_ml.csv",
    )
    parser.add_argument(
        "--dataset", type=Path, default=DATASET_PATH,
        help="Ruta al dataset_ml.csv (solo si --source csv).",
    )
    parser.add_argument(
        "--db", type=Path, default=DB_PATH,
        help="Ruta a ico.db (solo si --source db).",
    )
    parser.add_argument(
        "--out", type=Path, default=OUTPUT_DIR,
        help="Directorio de salida para los artefactos.",
    )
    args = parser.parse_args()
    main(args.source, args.dataset, args.db, args.out)
