"""
main.py — FastAPI — ICO Distribuidora v2 (NeuMF)

FastAPI NO carga el modelo en memoria. Las recomendaciones se leen
desde la tabla `predicciones` en SQLite, generada por batch_inference.py.

CÓMO EJECUTAR:
    uvicorn backend.app.main:app --reload --port 8000

DOCUMENTACIÓN INTERACTIVA:
    http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import init_db
from backend.app.routers import admin, auth, clients, orders, products, recommendations, sellers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando base de datos ...")
    await init_db()
    logger.info("Base de datos lista.")
    yield
    logger.info("Servidor detenido.")


app = FastAPI(
    title="ICO Distribuidora — API de Recomendaciones NeuMF",
    description="""
## Sistema de Recomendación NeuMF — ICO Distribuidora

Score final: `0.55 × ncf_score + 0.20 × score_urgency + 0.15 × score_rotation + 0.10 × score_novelty`

Las recomendaciones se pre-calculan diariamente (batch_inference.py).
FastAPI solo ejecuta SELECT en SQLite → latencia < 20ms.
    """,
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(recommendations.router)
app.include_router(products.router)
app.include_router(clients.router)
app.include_router(sellers.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
