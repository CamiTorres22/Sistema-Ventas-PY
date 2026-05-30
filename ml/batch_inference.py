"""
batch_inference.py -- Inferencia diaria: genera predicciones pre-calculadas

Ejecuta el cross-join completo (n_usuarios x n_productos) y calcula el
score_final para cada par. Guarda los Top-10 por usuario en Supabase (PG).
COMO EJECUTAR: python ml/batch_inference.py
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import torch
from dotenv import load_dotenv

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.ncf.model import NCF

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODEL_PATH    = PROCESSED_DIR / "modelo_ncf.pt"
INDICES_PATH  = PROCESSED_DIR / "indices.json"
CTX_PATH      = PROCESSED_DIR / "contexto_productos.parquet"

W_NCF      = 0.50
W_URGENCY  = 0.25
W_NOVELTY  = 0.15
W_ROTATION = 0.10
SIGMA_URGENCY  = 15.0
SIGMA_NOVELTY  = 15.0
SIGMA_ROTATION = 0.2
UMBRAL_URGENCIA = 30
UMBRAL_NOVEDAD  = 200
TOP_K = 10


def score_urgency(dias_para_vencer: np.ndarray) -> np.ndarray:
    """Sigmoide inversa con inflexion en 15 dias. Vencidos -> score=0."""
    x = np.clip((dias_para_vencer.astype(np.float64) - 15.0) / SIGMA_URGENCY, -500, 500)
    scores = (1.0 / (1.0 + np.exp(x))).astype(np.float32)
    scores[dias_para_vencer < 0] = 0.0
    return scores


def score_novelty(dias_en_catalogo: np.ndarray) -> np.ndarray:
    """Sigmoide decreciente con inflexion en 30 dias."""
    x = np.clip((dias_en_catalogo.astype(np.float64) - 30.0) / SIGMA_NOVELTY, -500, 500)
    return (1.0 / (1.0 + np.exp(x))).astype(np.float32)


def score_rotation(rotacion_diaria: np.ndarray, rot_p25: float) -> np.ndarray:
    """Sigmoide inversa de rotacion: score alto = baja rotacion = necesita impulso."""
    x = np.clip((rotacion_diaria.astype(np.float64) - rot_p25) / SIGMA_ROTATION, -500, 500)
    return (1.0 / (1.0 + np.exp(x))).astype(np.float32)


def _init_predicciones_table(conn) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predicciones (
            cliente_id        VARCHAR(20) NOT NULL,
            producto_id       VARCHAR(20) NOT NULL,
            rank_general      INTEGER     NOT NULL,
            score_final       REAL        NOT NULL,
            ncf_score         REAL        NOT NULL,
            s_urgency         REAL        NOT NULL,
            s_rotation        REAL        NOT NULL,
            s_novelty         REAL        NOT NULL,
            es_urgente        INTEGER     NOT NULL DEFAULT 0,
            es_nuevo          INTEGER     NOT NULL DEFAULT 0,
            es_baja_rotacion  INTEGER     NOT NULL DEFAULT 0,
            dias_para_vencer  INTEGER,
            dias_en_catalogo  INTEGER,
            rotacion_diaria   REAL,
            stock             INTEGER,
            fecha_generacion  VARCHAR(10) NOT NULL,
            PRIMARY KEY (cliente_id, producto_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_cliente    ON predicciones(cliente_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_urgente    ON predicciones(cliente_id, es_urgente)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_rotacion   ON predicciones(cliente_id, es_baja_rotacion)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_nuevo      ON predicciones(cliente_id, es_nuevo)")
    conn.commit()
    cur.close()


def run_batch() -> None:
    t_start = time.time()
    FECHA_HOY = date.today().isoformat()
    direct_url = os.getenv("DIRECT_URL")
    if not direct_url:
        raise RuntimeError("DIRECT_URL no esta definido en el archivo .env")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Dispositivo: %s", device)
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modelo no encontrado en {MODEL_PATH}. Ejecuta: python ml/train.py")
    checkpoint = torch.load(MODEL_PATH, map_location=device)
    model = NCF(
        n_users=checkpoint["n_users"],
        n_items=checkpoint["n_items"],
        k=checkpoint["k"],
        mlp_layers=checkpoint["mlp_layers"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    logger.info("Modelo cargado: epoch %d | val_AUC: %.4f", checkpoint["epoch"], checkpoint["val_auc"])
    with open(INDICES_PATH, encoding="utf-8") as f:
        indices = json.load(f)
    n_users  = indices["n_users"]
    n_items  = indices["n_items"]
    idx2user = {int(k): v for k, v in indices["idx2user"].items()}
    idx2item = {int(k): v for k, v in indices["idx2item"].items()}
    logger.info("Usuarios: %d | Items: %d | Pares totales: %d", n_users, n_items, n_users * n_items)
    ctx     = pd.read_parquet(CTX_PATH).set_index("item_idx")
    rot_p25 = float(ctx["rot_p25"].iloc[0])
    logger.info("Percentil 25 de rotacion: %.4f", rot_p25)
    dias_vencer_vec   = np.zeros(n_items, dtype=np.float32)
    dias_catalogo_vec = np.zeros(n_items, dtype=np.float32)
    rotacion_vec      = np.zeros(n_items, dtype=np.float32)
    stock_vec         = np.zeros(n_items, dtype=np.int32)
    baja_rot_vec      = np.zeros(n_items, dtype=np.int8)
    for j in range(n_items):
        if j in ctx.index:
            row = ctx.loc[j]
            dias_vencer_vec[j]   = row["dias_para_vencer"]
            dias_catalogo_vec[j] = row["dias_en_catalogo"]
            rotacion_vec[j]      = row["rotacion_diaria"]
            stock_vec[j]         = int(row["stock"])
            baja_rot_vec[j]      = int(row["baja_rotacion"])
    s_urgency_vec  = score_urgency(dias_vencer_vec)
    s_novelty_vec  = score_novelty(dias_catalogo_vec)
    s_rotation_vec = score_rotation(rotacion_vec, rot_p25)
    excluir_mask   = (stock_vec <= 0) | (dias_vencer_vec < 0)
    conn = psycopg2.connect(direct_url)
    _init_predicciones_table(conn)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE predicciones")
    conn.commit()
    INSERT_SQL = """
        INSERT INTO predicciones
            (cliente_id, producto_id, rank_general, score_final,
             ncf_score, s_urgency, s_rotation, s_novelty,
             es_urgente, es_nuevo, es_baja_rotacion,
             dias_para_vencer, dias_en_catalogo, rotacion_diaria,
             stock, fecha_generacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (cliente_id, producto_id) DO UPDATE SET
            rank_general     = EXCLUDED.rank_general,
            score_final      = EXCLUDED.score_final,
            ncf_score        = EXCLUDED.ncf_score,
            s_urgency        = EXCLUDED.s_urgency,
            s_rotation       = EXCLUDED.s_rotation,
            s_novelty        = EXCLUDED.s_novelty,
            es_urgente       = EXCLUDED.es_urgente,
            es_nuevo         = EXCLUDED.es_nuevo,
            es_baja_rotacion = EXCLUDED.es_baja_rotacion,
            dias_para_vencer = EXCLUDED.dias_para_vencer,
            dias_en_catalogo = EXCLUDED.dias_en_catalogo,
            rotacion_diaria  = EXCLUDED.rotacion_diaria,
            stock            = EXCLUDED.stock,
            fecha_generacion = EXCLUDED.fecha_generacion
    """
    rows_batch   = []
    BATCH_INSERT = 5000
    logger.info("Iniciando inferencia batch (%d usuarios) ...", n_users)
    for u in range(n_users):
        cliente_id = idx2user[u]
        ncf_scores = model.predict_all(u, n_items, device).numpy()
        score_final = (
            W_NCF * ncf_scores
            + W_URGENCY  * s_urgency_vec
            + W_NOVELTY  * s_novelty_vec
            + W_ROTATION * s_rotation_vec
        )
        score_final[excluir_mask] = 0.0
        top_general = np.argsort(score_final)[::-1][:TOP_K]
        rank_map    = {int(j): rank for rank, j in enumerate(top_general, start=1)}
        def _top_k_cat(mask: np.ndarray) -> set:
            idx = np.where(mask & (score_final > 0))[0]
            if len(idx) == 0:
                return set()
            order = np.argsort(score_final[idx])[::-1][:TOP_K]
            return set(idx[order].tolist())
        top_baja_rot = _top_k_cat(baja_rot_vec == 1)
        top_urgentes = _top_k_cat((dias_vencer_vec <= UMBRAL_URGENCIA) & (dias_vencer_vec >= 0))
        top_nuevos   = _top_k_cat(dias_catalogo_vec <= UMBRAL_NOVEDAD)
        all_indices  = sorted(set(top_general.tolist()) | top_baja_rot | top_urgentes | top_nuevos)
        for j in all_indices:
            if score_final[j] <= 0:
                continue
            rank        = rank_map.get(j, TOP_K + 1)
            producto_id = idx2item[j]
            rows_batch.append((
                cliente_id, producto_id, rank,
                round(float(score_final[j]),    6),
                round(float(ncf_scores[j]),     6),
                round(float(s_urgency_vec[j]),  6),
                round(float(s_rotation_vec[j]), 6),
                round(float(s_novelty_vec[j]),  6),
                int(dias_vencer_vec[j] <= UMBRAL_URGENCIA and dias_vencer_vec[j] >= 0),
                int(dias_catalogo_vec[j] <= UMBRAL_NOVEDAD),
                int(baja_rot_vec[j]),
                int(dias_vencer_vec[j]),
                int(dias_catalogo_vec[j]),
                round(float(rotacion_vec[j]), 6),
                int(stock_vec[j]),
                FECHA_HOY,
            ))
        if len(rows_batch) >= BATCH_INSERT:
            cur.executemany(INSERT_SQL, rows_batch)
            conn.commit()
            rows_batch = []
        if (u + 1) % 100 == 0:
            logger.info("  Procesados %d/%d usuarios ...", u + 1, n_users)
    if rows_batch:
        cur.executemany(INSERT_SQL, rows_batch)
        conn.commit()
    cur.execute("SELECT COUNT(*) FROM predicciones")
    total_rows = cur.fetchone()[0]
    cur.close()
    conn.close()
    elapsed = time.time() - t_start
    logger.info("-" * 60)
    logger.info("Batch completado en %.1fs", elapsed)
    logger.info("Predicciones guardadas: %d filas en Supabase", total_rows)
    logger.info("-" * 60)


if __name__ == "__main__":
    run_batch()
