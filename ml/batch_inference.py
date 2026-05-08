"""
batch_inference.py — Inferencia diaria: genera predicciones pre-calculadas

Ejecuta el cross-join completo (n_usuarios × n_productos) y calcula el
score_final para cada par. Guarda los Top-10 por usuario en la BD SQLite,
listos para ser servidos por FastAPI con latencia < 20ms.

score_final = 0.55 × ncf_score
            + 0.20 × score_urgency(dias_para_vencer)
            + 0.15 × score_rotation(rotacion_diaria)
            + 0.10 × score_novelty(dias_en_catalogo)

Filtros duros:
  - stock <= 0            → score_final = 0  (sin stock, no recomendar)
  - dias_para_vencer < 0  → score_final = 0  (producto vencido)

CÓMO EJECUTAR:
    python ml/batch_inference.py
    python ml/batch_inference.py --db data/db/ico.db
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.ncf.model import NeuMF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rutas ──────────────────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODEL_PATH    = PROCESSED_DIR / "modelo_ncf.pt"
INDICES_PATH  = PROCESSED_DIR / "indices.json"
CTX_PATH      = PROCESSED_DIR / "contexto_productos.parquet"
DB_PATH       = ROOT_DIR / "data" / "db" / "ico.db"

# ── Pesos del score final (He et al. 2017 + ajuste de negocio ICO) ────────────
# score_final = 0.50*ncf + 0.25*urgency + 0.15*novelty + 0.10*rotation
W_NCF      = 0.50
W_URGENCY  = 0.25
W_NOVELTY  = 0.15
W_ROTATION = 0.10

# ── Parámetros de las funciones sigmoide ──────────────────────────────────────
SIGMA_URGENCY  = 15.0   # inflexión en d=15 días para vencer (curva suave)
SIGMA_NOVELTY  = 15.0   # inflexión en dc=30 días en catálogo
SIGMA_ROTATION = 0.2    # inflexión en p25 de rotación_diaria

# ── Umbrales para flags de negocio ────────────────────────────────────────────
UMBRAL_URGENCIA = 30    # días: <= 30 → es_urgente
UMBRAL_NOVEDAD  = 90    # días: <= 90 → es_nuevo (decisión de negocio: ventana amplia)

TOP_K = 10


# ──────────────────────────────────────────────────────────────────────────────
# BUSINESS SCORES (funciones sigmoide continuas)
# ──────────────────────────────────────────────────────────────────────────────

def score_urgency(dias_para_vencer: np.ndarray) -> np.ndarray:
    """
    Sigmoide inversa con inflexión en 15 días.
    Productos vencidos (< 0) → score = 0.
    d=2  → 0.88 | d=5  → 0.72 | d=15 → 0.50 | d=30 → 0.27 | d=60 → 0.02
    """
    x = np.clip((dias_para_vencer.astype(np.float64) - 15.0) / SIGMA_URGENCY, -500, 500)
    scores = (1.0 / (1.0 + np.exp(x))).astype(np.float32)
    scores[dias_para_vencer < 0] = 0.0   # filtro duro: vencidos = 0
    return scores


def score_novelty(dias_en_catalogo: np.ndarray) -> np.ndarray:
    """
    Sigmoide decreciente con inflexión en 30 días.
    dc=1  → 0.88 | dc=15 → 0.73 | dc=30 → 0.50 | dc=60 → 0.27 | dc=90 → 0.12
    """
    x = np.clip((dias_en_catalogo.astype(np.float64) - 30.0) / SIGMA_NOVELTY, -500, 500)
    return (1.0 / (1.0 + np.exp(x))).astype(np.float32)


def score_rotation(rotacion_diaria: np.ndarray, rot_p25: float) -> np.ndarray:
    """
    Sigmoide inversa de rotación: score alto = baja rotación = necesita impulso.
    Inflexión en el percentil 25 de rotación del catálogo.
    rot << p25 → score ≈ 0.88 | rot == p25 → score = 0.50 | rot >> p25 → score ≈ 0.07
    """
    x = np.clip((rotacion_diaria.astype(np.float64) - rot_p25) / SIGMA_ROTATION, -500, 500)
    scores = (1.0 / (1.0 + np.exp(x)))
    return scores.astype(np.float32)


# ──────────────────────────────────────────────────────────────────────────────
# INICIALIZACIÓN DE LA TABLA EN SQLITE
# ──────────────────────────────────────────────────────────────────────────────

def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predicciones (
            cliente_id        TEXT    NOT NULL,
            producto_id       TEXT    NOT NULL,
            rank_general      INTEGER NOT NULL,
            score_final       REAL    NOT NULL,
            ncf_score         REAL    NOT NULL,
            s_urgency         REAL    NOT NULL,
            s_rotation        REAL    NOT NULL,
            s_novelty         REAL    NOT NULL,
            es_urgente        INTEGER NOT NULL DEFAULT 0,
            es_nuevo          INTEGER NOT NULL DEFAULT 0,
            es_baja_rotacion  INTEGER NOT NULL DEFAULT 0,
            dias_para_vencer  INTEGER,
            dias_en_catalogo  INTEGER,
            rotacion_diaria   REAL,
            stock             INTEGER,
            fecha_generacion  TEXT    NOT NULL,
            PRIMARY KEY (cliente_id, producto_id)
        )
    """)
    # Índices para acelerar las consultas del API
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_cliente ON predicciones(cliente_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_urgente ON predicciones(cliente_id, es_urgente)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_rotacion ON predicciones(cliente_id, es_baja_rotacion)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_nuevo ON predicciones(cliente_id, es_nuevo)")
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# INFERENCIA BATCH
# ──────────────────────────────────────────────────────────────────────────────

def run_batch(db_path: Path = DB_PATH) -> None:
    t_start = time.time()
    FECHA_HOY = date.today().isoformat()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Dispositivo: %s", device)

    # ── Cargar modelo ──────────────────────────────────────────────────────────
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo no encontrado en {MODEL_PATH}. Ejecuta primero: python ml/train.py"
        )
    checkpoint = torch.load(MODEL_PATH, map_location=device)
    model = NeuMF(
        n_users=checkpoint["n_users"],
        n_items=checkpoint["n_items"],
        k=checkpoint["k"],
        mlp_layers=checkpoint["mlp_layers"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    logger.info(
        "Modelo cargado: epoch %d | val_AUC: %.4f",
        checkpoint["epoch"], checkpoint["val_auc"],
    )

    # ── Cargar índices ─────────────────────────────────────────────────────────
    with open(INDICES_PATH, encoding="utf-8") as f:
        indices = json.load(f)

    n_users  = indices["n_users"]
    n_items  = indices["n_items"]
    idx2user = {int(k): v for k, v in indices["idx2user"].items()}
    idx2item = {int(k): v for k, v in indices["idx2item"].items()}

    logger.info("Usuarios: %d | Ítems: %d | Pares totales: %d", n_users, n_items, n_users * n_items)

    # ── Cargar contexto de productos ───────────────────────────────────────────
    ctx = pd.read_parquet(CTX_PATH).set_index("item_idx")

    rot_p25 = float(ctx["rot_p25"].iloc[0])
    logger.info("Percentil 25 de rotación (inflexión score_rotation): %.4f", rot_p25)

    # Vectores de features (alineados por item_idx 0..n_items-1)
    dias_vencer_vec  = np.zeros(n_items, dtype=np.float32)
    dias_catalogo_vec = np.zeros(n_items, dtype=np.float32)
    rotacion_vec     = np.zeros(n_items, dtype=np.float32)
    stock_vec        = np.zeros(n_items, dtype=np.int32)
    baja_rot_vec     = np.zeros(n_items, dtype=np.int8)

    for j in range(n_items):
        if j in ctx.index:
            row = ctx.loc[j]
            dias_vencer_vec[j]   = row["dias_para_vencer"]
            dias_catalogo_vec[j] = row["dias_en_catalogo"]
            rotacion_vec[j]      = row["rotacion_diaria"]
            stock_vec[j]         = int(row["stock"])
            baja_rot_vec[j]      = int(row["baja_rotacion"])

    # ── Calcular business scores para todos los ítems (una sola vez) ──────────
    s_urgency_vec  = score_urgency(dias_vencer_vec)
    s_novelty_vec  = score_novelty(dias_catalogo_vec)
    s_rotation_vec = score_rotation(rotacion_vec, rot_p25)

    # Máscara de ítems no recomendables (sin stock o vencidos)
    excluir_mask = (stock_vec <= 0) | (dias_vencer_vec < 0)

    # ── Inicializar BD ─────────────────────────────────────────────────────────
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM predicciones")   # limpiar predicciones anteriores
    conn.commit()

    rows_batch = []
    BATCH_INSERT = 5000

    logger.info("Iniciando inferencia batch (%d usuarios) ...", n_users)
    for u in range(n_users):
        cliente_id = idx2user[u]

        # ncf_score para todos los ítems
        ncf_scores = model.predict_all(u, n_items, device).numpy()

        # Score final: 0.50*ncf + 0.25*urgency + 0.15*novelty + 0.10*rotation
        score_final = (
            W_NCF      * ncf_scores
            + W_URGENCY  * s_urgency_vec
            + W_NOVELTY  * s_novelty_vec
            + W_ROTATION * s_rotation_vec
        )

        # Aplicar filtros duros
        score_final[excluir_mask] = 0.0

        # Top-K por score_final (solo ítems con score > 0)
        top_indices = np.argsort(score_final)[::-1][:TOP_K]

        for rank, j in enumerate(top_indices, start=1):
            if score_final[j] <= 0:
                break
            producto_id = idx2item[j]
            rows_batch.append((
                cliente_id,
                producto_id,
                rank,
                round(float(score_final[j]), 6),
                round(float(ncf_scores[j]), 6),
                round(float(s_urgency_vec[j]), 6),
                round(float(s_rotation_vec[j]), 6),
                round(float(s_novelty_vec[j]), 6),
                int(dias_vencer_vec[j] <= UMBRAL_URGENCIA and dias_vencer_vec[j] >= 0),
                int(dias_catalogo_vec[j] <= UMBRAL_NOVEDAD),
                int(baja_rot_vec[j]),
                int(dias_vencer_vec[j]),
                int(dias_catalogo_vec[j]),
                round(float(rotacion_vec[j]), 6),
                int(stock_vec[j]),
                FECHA_HOY,
            ))

        # Insertar en batches para no saturar memoria
        if len(rows_batch) >= BATCH_INSERT:
            conn.executemany(
                """INSERT OR REPLACE INTO predicciones
                   (cliente_id, producto_id, rank_general, score_final,
                    ncf_score, s_urgency, s_rotation, s_novelty,
                    es_urgente, es_nuevo, es_baja_rotacion,
                    dias_para_vencer, dias_en_catalogo, rotacion_diaria,
                    stock, fecha_generacion)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows_batch,
            )
            conn.commit()
            rows_batch = []

        if (u + 1) % 100 == 0:
            logger.info("  Procesados %d/%d usuarios ...", u + 1, n_users)

    # Insertar filas restantes
    if rows_batch:
        conn.executemany(
            """INSERT OR REPLACE INTO predicciones
               (cliente_id, producto_id, rank_general, score_final,
                ncf_score, s_urgency, s_rotation, s_novelty,
                es_urgente, es_nuevo, es_baja_rotacion,
                dias_para_vencer, dias_en_catalogo, rotacion_diaria,
                stock, fecha_generacion)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows_batch,
        )
        conn.commit()

    total_rows = conn.execute("SELECT COUNT(*) FROM predicciones").fetchone()[0]
    conn.close()

    elapsed = time.time() - t_start
    logger.info("─" * 60)
    logger.info("Batch completado en %.1fs", elapsed)
    logger.info("Predicciones guardadas: %d filas en %s", total_rows, db_path)
    logger.info("─" * 60)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Inference NeuMF — ICO Distribuidora")
    parser.add_argument(
        "--db", type=Path, default=DB_PATH,
        help="Ruta a la base de datos SQLite.",
    )
    args = parser.parse_args()
    run_batch(db_path=args.db)
