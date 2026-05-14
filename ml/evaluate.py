"""
evaluate.py — Evaluación del modelo NCF con NDCG@10

Calcula NDCG@10 (Normalized Discounted Cumulative Gain) sobre un conjunto
de test leave-one-out: para cada usuario, se toma su interacción más reciente
como item de test y se evalúa si aparece en el Top-10 del modelo.

También calcula:
  - HitRate@10: % de usuarios donde el ítem test está en el Top-10
  - Precision@10: relevantes en top-10 / 10

CÓMO EJECUTAR:
    python ml/evaluate.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.ncf.model import NCF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODEL_PATH    = PROCESSED_DIR / "modelo_ncf.pt"
PARES_PATH    = PROCESSED_DIR / "pares_entrenamiento.parquet"
INDICES_PATH  = PROCESSED_DIR / "indices.json"
EVAL_PATH     = PROCESSED_DIR / "eval_metrics.json"

TOP_K = 10
NEG_SAMPLES_EVAL = 99   # 99 negativos + 1 positivo = 100 candidatos (protocolo estándar)


# ──────────────────────────────────────────────────────────────────────────────
# NDCG@K (fórmula estándar)
# ──────────────────────────────────────────────────────────────────────────────

def ndcg_at_k(ranked_list: list[int], relevant: set[int], k: int) -> float:
    """
    Calcula NDCG@K para una lista de ítems rankeados.

    DCG  = Σ (rel_i / log2(i+2))  para i en 0..k-1
    IDCG = DCG del ranking perfecto (todos los relevantes primero)
    NDCG = DCG / IDCG
    """
    dcg  = 0.0
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))

    for i, item in enumerate(ranked_list[:k]):
        if item in relevant:
            dcg += 1.0 / np.log2(i + 2)

    return dcg / idcg if idcg > 0 else 0.0


def hit_at_k(ranked_list: list[int], relevant: set[int], k: int) -> int:
    return int(bool(set(ranked_list[:k]) & relevant))


# ──────────────────────────────────────────────────────────────────────────────
# EVALUACIÓN LEAVE-ONE-OUT
# ──────────────────────────────────────────────────────────────────────────────

def evaluate() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Dispositivo: %s", device)

    # ── Cargar modelo ──────────────────────────────────────────────────────────
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo no encontrado en {MODEL_PATH}. Ejecuta primero: python ml/train.py"
        )

    checkpoint = torch.load(MODEL_PATH, map_location=device)
    model = NCF(
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

    # ── Cargar datos ───────────────────────────────────────────────────────────
    with open(INDICES_PATH, encoding="utf-8") as f:
        indices = json.load(f)

    n_items  = indices["n_items"]
    item2idx = indices["item2idx"]

    # Solo pares positivos del historial
    pares = pd.read_parquet(PARES_PATH)
    positivos = pares[pares["label"] == 1][["user_idx", "item_idx"]].copy()

    rng = np.random.default_rng(42)
    all_items = np.arange(n_items, dtype=np.int32)

    ndcg_scores = []
    hit_scores  = []
    prec_scores = []

    usuarios = positivos["user_idx"].unique()
    logger.info("Evaluando %d usuarios (leave-one-out) ...", len(usuarios))

    for u in usuarios:
        user_items = set(
            positivos[positivos["user_idx"] == u]["item_idx"].tolist()
        )
        if len(user_items) < 2:
            # No hay suficiente historial para leave-one-out
            continue

        # El ítem test = el de mayor índice (proxy de "más reciente")
        test_item = max(user_items)
        train_items = user_items - {test_item}

        # 99 negativos aleatorios (no comprados)
        candidatos_neg = all_items[~np.isin(all_items, list(user_items))]
        neg_sample = rng.choice(
            candidatos_neg,
            size=min(NEG_SAMPLES_EVAL, len(candidatos_neg)),
            replace=False,
        )

        # Pool de evaluación: 1 positivo + 99 negativos
        eval_items = np.concatenate([[test_item], neg_sample])

        # Predicción
        user_t = torch.tensor([u] * len(eval_items), dtype=torch.long, device=device)
        item_t = torch.tensor(eval_items, dtype=torch.long, device=device)

        with torch.no_grad():
            scores = model(user_t, item_t).cpu().numpy()

        # Ranking
        ranked_indices = np.argsort(scores)[::-1]
        ranked_items   = eval_items[ranked_indices].tolist()

        ndcg = ndcg_at_k(ranked_items, {test_item}, TOP_K)
        hit  = hit_at_k(ranked_items, {test_item}, TOP_K)
        prec = hit / TOP_K

        ndcg_scores.append(ndcg)
        hit_scores.append(hit)
        prec_scores.append(prec)

    results = {
        "n_usuarios_evaluados": len(ndcg_scores),
        f"NDCG@{TOP_K}":        round(float(np.mean(ndcg_scores)), 4),
        f"HitRate@{TOP_K}":     round(float(np.mean(hit_scores)), 4),
        f"Precision@{TOP_K}":   round(float(np.mean(prec_scores)), 4),
        "top_k":                TOP_K,
        "neg_samples_eval":     NEG_SAMPLES_EVAL,
    }

    logger.info("─" * 50)
    logger.info("NDCG@%d    : %.4f", TOP_K, results[f"NDCG@{TOP_K}"])
    logger.info("HitRate@%d : %.4f", TOP_K, results[f"HitRate@{TOP_K}"])
    logger.info("Precision@%d: %.4f", TOP_K, results[f"Precision@{TOP_K}"])
    logger.info("─" * 50)

    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info("Métricas guardadas en: %s", EVAL_PATH)


if __name__ == "__main__":
    evaluate()
