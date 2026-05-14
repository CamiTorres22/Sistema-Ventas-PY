"""
train.py — Entrenamiento del modelo NCF

Lee los artefactos generados por clean.py y entrena el modelo NCF.
Al finalizar guarda:
  - data/processed/modelo_ncf.pt    (pesos del modelo)
  - data/processed/train_metrics.json (métricas de entrenamiento)

CÓMO EJECUTAR:
    python ml/train.py
    python ml/train.py --epochs 20 --batch 256 --k 64 --lr 0.001
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import mlflow
import mlflow.pytorch
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# Importar modelo relativo al root del proyecto
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.ncf.model import NCF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# ── Rutas ──────────────────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PARES_PATH    = PROCESSED_DIR / "pares_entrenamiento.parquet"
INDICES_PATH  = PROCESSED_DIR / "indices.json"
MODEL_PATH    = PROCESSED_DIR / "modelo_ncf.pt"
METRICS_PATH  = PROCESSED_DIR / "train_metrics.json"

# ── Hiperparámetros por defecto ────────────────────────────────────────────────
DEFAULT_K          = 64
DEFAULT_MLP_LAYERS = [128, 64, 32]
DEFAULT_EPOCHS     = 20
DEFAULT_BATCH      = 1024   # alineado con documentación técnica
DEFAULT_LR         = 1e-3
DEFAULT_VAL_SPLIT  = 0.2    # 80/20 split según documentación técnica


# ──────────────────────────────────────────────────────────────────────────────
# DATASET
# ──────────────────────────────────────────────────────────────────────────────

class InteractionDataset(Dataset):
    """Dataset PyTorch para pares (usuario, ítem, label, weight)."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.users   = torch.tensor(df["user_idx"].values, dtype=torch.long)
        self.items   = torch.tensor(df["item_idx"].values, dtype=torch.long)
        self.labels  = torch.tensor(df["label"].values,   dtype=torch.float32)
        self.weights = torch.tensor(df["weight"].values,  dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.users)

    def __getitem__(self, idx: int) -> tuple:
        return (
            self.users[idx],
            self.items[idx],
            self.labels[idx],
            self.weights[idx],
        )


# ──────────────────────────────────────────────────────────────────────────────
# MÉTRICAS
# ──────────────────────────────────────────────────────────────────────────────

def compute_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    """AUC aproximado usando ranking (eficiente para datasets grandes)."""
    from sklearn.metrics import roc_auc_score
    try:
        return float(roc_auc_score(labels, scores))
    except Exception:
        return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# EVALUACIÓN NDCG@10 (leave-one-out, 99 negativos)
# ──────────────────────────────────────────────────────────────────────────────

_TOP_K_EVAL      = 10
_NEG_SAMPLES_EVAL = 99


def _ndcg_at_k(ranked_list: list, relevant: set, k: int) -> float:
    """NDCG@K estándar: DCG / IDCG."""
    dcg  = 0.0
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    for i, item in enumerate(ranked_list[:k]):
        if item in relevant:
            dcg += 1.0 / np.log2(i + 2)
    return dcg / idcg if idcg > 0 else 0.0


def _evaluate_ndcg(
    model_path:   Path,
    pares_path:   Path,
    indices_path: Path,
    device:       "torch.device",
    top_k:        int = _TOP_K_EVAL,
    neg_samples:  int = _NEG_SAMPLES_EVAL,
) -> dict:
    """
    Evaluación leave-one-out NDCG@10 sobre el modelo guardado.

    Para cada usuario con ≥ 2 interacciones positivas:
      - ítem test  = el de mayor item_idx (proxy del más reciente)
      - pool eval  = 1 positivo + 99 negativos aleatorios (no comprados)
      - métricas   = NDCG@10, HitRate@10, Precision@10
    """
    checkpoint = torch.load(model_path, map_location=device)
    model = NCF(
        n_users=checkpoint["n_users"],
        n_items=checkpoint["n_items"],
        k=checkpoint["k"],
        mlp_layers=checkpoint["mlp_layers"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    with open(indices_path, encoding="utf-8") as f:
        indices = json.load(f)
    n_items = indices["n_items"]

    pares     = pd.read_parquet(pares_path)
    positivos = pares[pares["label"] == 1][["user_idx", "item_idx"]].copy()

    rng       = np.random.default_rng(42)
    all_items = np.arange(n_items, dtype=np.int32)

    ndcg_scores: list[float] = []
    hit_scores:  list[int]   = []
    prec_scores: list[float] = []

    for u in positivos["user_idx"].unique():
        user_items = set(positivos[positivos["user_idx"] == u]["item_idx"].tolist())
        if len(user_items) < 2:
            continue

        test_item      = max(user_items)
        candidatos_neg = all_items[~np.isin(all_items, list(user_items))]
        neg_sample     = rng.choice(
            candidatos_neg,
            size=min(neg_samples, len(candidatos_neg)),
            replace=False,
        )
        eval_items = np.concatenate([[test_item], neg_sample])

        user_t = torch.tensor([u] * len(eval_items), dtype=torch.long, device=device)
        item_t = torch.tensor(eval_items,             dtype=torch.long, device=device)

        with torch.no_grad():
            scores = model(user_t, item_t).cpu().numpy()

        ranked_items = eval_items[np.argsort(scores)[::-1]].tolist()

        ndcg = _ndcg_at_k(ranked_items, {test_item}, top_k)
        hit  = int(bool(set(ranked_items[:top_k]) & {test_item}))

        ndcg_scores.append(ndcg)
        hit_scores.append(hit)
        prec_scores.append(hit / top_k)

    return {
        "ndcg_at_10":    round(float(np.mean(ndcg_scores)), 4) if ndcg_scores else 0.0,
        "hitrate_at_10": round(float(np.mean(hit_scores)),  4) if hit_scores  else 0.0,
        "precision_at_10": round(float(np.mean(prec_scores)), 4) if prec_scores else 0.0,
        "n_usuarios_evaluados": len(ndcg_scores),
    }


# ──────────────────────────────────────────────────────────────────────────────
# ENTRENAMIENTO
# ──────────────────────────────────────────────────────────────────────────────

def train(
    epochs:     int   = DEFAULT_EPOCHS,
    batch_size: int   = DEFAULT_BATCH,
    k:          int   = DEFAULT_K,
    lr:         float = DEFAULT_LR,
    val_split:  float = DEFAULT_VAL_SPLIT,
) -> None:

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Dispositivo: %s", device)

    # ── Cargar artefactos ──────────────────────────────────────────────────────
    logger.info("Cargando pares de entrenamiento desde %s ...", PARES_PATH)
    pares = pd.read_parquet(PARES_PATH)

    with open(INDICES_PATH, encoding="utf-8") as f:
        indices = json.load(f)

    n_users = indices["n_users"]
    n_items = indices["n_items"]
    logger.info("Usuarios: %d | Ítems: %d | Pares: %d", n_users, n_items, len(pares))

    # ── Train / Validation split ───────────────────────────────────────────────
    # Separar por posición aleatoria (ya mezclado en clean.py)
    val_size  = int(len(pares) * val_split)
    train_df  = pares.iloc[val_size:].reset_index(drop=True)
    val_df    = pares.iloc[:val_size].reset_index(drop=True)

    train_ds  = InteractionDataset(train_df)
    val_ds    = InteractionDataset(val_df)
    train_dl  = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0)
    val_dl    = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0)

    logger.info("Train: %d pares | Val: %d pares", len(train_ds), len(val_ds))

    # ── Modelo ─────────────────────────────────────────────────────────────────
    model = NCF(
        n_users=n_users,
        n_items=n_items,
        k=k,
        mlp_layers=DEFAULT_MLP_LAYERS,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info("Parámetros entrenables: %s", f"{total_params:,}")

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCELoss(reduction="none")   # reduction=none para aplicar weights

    # ── MLflow run ────────────────────────────────────────────────────────────
    mlflow.set_experiment("NCF-ICO")
    run = mlflow.start_run()
    mlflow.log_params({
        "epochs":        epochs,
        "batch_size":    batch_size,
        "k":             k,
        "lr":            lr,
        "val_split":     val_split,
        "mlp_layers":    str(DEFAULT_MLP_LAYERS),
        "n_users":       n_users,
        "n_items":       n_items,
    })

    # ── Loop de entrenamiento ──────────────────────────────────────────────────
    history = []
    best_val_auc = 0.0
    best_epoch   = 0

    n_train_batches = len(train_dl)
    LOG_EVERY = max(1, n_train_batches // 5)   # log ~5 veces por época

    logger.info("=" * 60)
    logger.info(
        "INICIANDO ENTRENAMIENTO: %d épocas × %d batches/época = %d iteraciones totales",
        epochs, n_train_batches, epochs * n_train_batches,
    )
    logger.info("=" * 60)

    t_global = time.time()

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        train_loss = 0.0

        for batch_idx, (users, items, labels, weights) in enumerate(train_dl, start=1):
            users   = users.to(device)
            items   = items.to(device)
            labels  = labels.to(device)
            weights = weights.to(device)

            optimizer.zero_grad()
            preds = model(users, items)
            loss  = (criterion(preds, labels) * weights).mean()
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(users)

            if batch_idx % LOG_EVERY == 0 or batch_idx == n_train_batches:
                pct = batch_idx / n_train_batches * 100
                elapsed_ep = time.time() - t0
                eta_ep = elapsed_ep / batch_idx * (n_train_batches - batch_idx)
                logger.info(
                    "  Época %d/%d | Batch %d/%d (%.0f%%) | loss_batch: %.4f | ETA época: %.0fs",
                    epoch, epochs, batch_idx, n_train_batches, pct,
                    loss.item(), eta_ep,
                )

        train_loss /= len(train_ds)

        # ── Validación ────────────────────────────────────────────────────────
        model.eval()
        val_loss   = 0.0
        all_labels = []
        all_scores = []

        with torch.no_grad():
            for users, items, labels, weights in val_dl:
                users   = users.to(device)
                items   = items.to(device)
                labels  = labels.to(device)
                weights = weights.to(device)

                preds    = model(users, items)
                loss     = (criterion(preds, labels) * weights).mean()
                val_loss += loss.item() * len(users)

                all_labels.extend(labels.cpu().numpy())
                all_scores.extend(preds.cpu().numpy())

        val_loss /= len(val_ds)
        val_auc   = compute_auc(np.array(all_labels), np.array(all_scores))
        elapsed   = time.time() - t0

        epoch_log = {
            "epoch":     epoch,
            "train_loss": round(train_loss, 6),
            "val_loss":   round(val_loss, 6),
            "val_auc":    round(val_auc, 6),
        }
        history.append(epoch_log)

        epochs_restantes = epochs - epoch
        eta_total = elapsed * epochs_restantes
        logger.info(
            "── Época %2d/%d completa | train_loss: %.4f | val_loss: %.4f | val_AUC: %.4f | %.1fs | ETA total: %.0fs",
            epoch, epochs, train_loss, val_loss, val_auc, elapsed, eta_total,
        )

        mlflow.log_metrics(
            {"train_loss": train_loss, "val_loss": val_loss, "val_auc": val_auc},
            step=epoch,
        )

        # Guardar mejor modelo
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_epoch   = epoch
            torch.save(
                {
                    "epoch":       epoch,
                    "model_state": model.state_dict(),
                    "n_users":     n_users,
                    "n_items":     n_items,
                    "k":           k,
                    "mlp_layers":  DEFAULT_MLP_LAYERS,
                    "val_auc":     val_auc,
                },
                MODEL_PATH,
            )

    t_total = time.time() - t_global
    logger.info("=" * 60)
    logger.info("ENTRENAMIENTO COMPLETADO en %.1fs (%.1f min)", t_total, t_total / 60)
    logger.info("Mejor modelo: época %d | val_AUC: %.4f", best_epoch, best_val_auc)
    logger.info("=" * 60)
    logger.info("Modelo guardado en: %s", MODEL_PATH)

    # ── Evaluación NDCG@10 (leave-one-out sobre el mejor modelo) ──────────────
    logger.info("Evaluando NDCG@10 sobre el mejor modelo guardado ...")
    ndcg_result = _evaluate_ndcg(MODEL_PATH, PARES_PATH, INDICES_PATH, device)

    # Guardar métricas
    metrics = {
        "best_epoch":    best_epoch,
        "best_val_auc":  round(best_val_auc, 6),
        "ndcg_at_10":    ndcg_result["ndcg_at_10"],
        "hitrate_at_10": ndcg_result["hitrate_at_10"],
        "precision_at_10": ndcg_result["precision_at_10"],
        "n_users":       n_users,
        "n_items":       n_items,
        "k":             k,
        "epochs":        epochs,
        "batch_size":    batch_size,
        "lr":            lr,
        "history":       history,
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Métricas guardadas en: %s", METRICS_PATH)
    logger.info(
        "NDCG@10: %.4f | HitRate@10: %.4f | Precision@10: %.4f",
        ndcg_result["ndcg_at_10"],
        ndcg_result["hitrate_at_10"],
        ndcg_result["precision_at_10"],
    )

    # ── MLflow: métricas finales + artefacto ──────────────────────────────────
    mlflow.log_metrics({
        "best_val_auc":    best_val_auc,
        "ndcg_at_10":      ndcg_result["ndcg_at_10"],
        "hitrate_at_10":   ndcg_result["hitrate_at_10"],
        "precision_at_10": ndcg_result["precision_at_10"],
    })
    mlflow.log_artifact(str(MODEL_PATH),   artifact_path="modelo")
    mlflow.log_artifact(str(METRICS_PATH), artifact_path="modelo")
    mlflow.end_run()
    logger.info("MLflow run finalizado. Ver con: mlflow ui")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenamiento NCF — ICO Distribuidora")
    parser.add_argument("--epochs", type=int,   default=DEFAULT_EPOCHS)
    parser.add_argument("--batch",  type=int,   default=DEFAULT_BATCH)
    parser.add_argument("--k",      type=int,   default=DEFAULT_K)
    parser.add_argument("--lr",     type=float, default=DEFAULT_LR)
    args = parser.parse_args()

    train(
        epochs=args.epochs,
        batch_size=args.batch,
        k=args.k,
        lr=args.lr,
    )
