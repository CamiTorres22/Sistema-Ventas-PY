"""
run_daily_batch.py — Entry point del pipeline diario

Ejecuta en secuencia:
  1. clean.py  — regenera pares de entrenamiento y contexto de productos
                 (solo si el dataset_ml.csv fue modificado hoy)
  2. batch_inference.py — calcula scores y actualiza la tabla predicciones

El modelo (train.py) NO se re-entrena en este job; eso ocurre mensualmente
o de forma manual ante crecimiento significativo del dataset.

CÓMO EJECUTAR:
    python scripts/run_daily_batch.py
    python scripts/run_daily_batch.py --force-clean  (fuerza re-ETL aunque no haya cambios)
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DATASET_PATH  = PROCESSED_DIR / "dataset_ml.csv"
PARES_PATH    = PROCESSED_DIR / "pares_entrenamiento.parquet"


def run_step(script: Path, label: str) -> None:
    logger.info("── Iniciando: %s ──", label)
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT_DIR),
    )
    if result.returncode != 0:
        logger.error("FALLO en %s (código %d)", label, result.returncode)
        sys.exit(result.returncode)
    logger.info("── Completado: %s (%.1fs) ──", label, time.time() - t0)


def dataset_updated_today() -> bool:
    """Verifica si dataset_ml.csv fue modificado hoy."""
    from datetime import date
    import os
    if not DATASET_PATH.exists():
        return False
    mtime = os.path.getmtime(DATASET_PATH)
    mod_date = __import__("datetime").datetime.fromtimestamp(mtime).date()
    return mod_date == date.today()


def main(force_clean: bool = False) -> None:
    logger.info("═" * 60)
    logger.info("PIPELINE DIARIO — ICO Distribuidora NeuMF")
    logger.info("═" * 60)

    t_total = time.time()

    # Paso 1: ETL (solo si dataset fue actualizado o se fuerza)
    if force_clean or not PARES_PATH.exists() or dataset_updated_today():
        run_step(ROOT_DIR / "ml" / "clean.py", "ETL (clean.py)")
    else:
        logger.info("dataset_ml.csv sin cambios hoy. Saltando ETL.")

    # Paso 2: Inferencia batch
    run_step(ROOT_DIR / "ml" / "batch_inference.py", "Batch Inference")

    logger.info("═" * 60)
    logger.info("Pipeline completado en %.1fs", time.time() - t_total)
    logger.info("═" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-clean", action="store_true",
        help="Fuerza re-ejecución del ETL aunque el dataset no haya cambiado.",
    )
    args = parser.parse_args()
    main(force_clean=args.force_clean)
