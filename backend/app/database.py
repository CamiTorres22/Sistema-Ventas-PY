"""
database.py — Configuración de SQLAlchemy + SQLite (async)

Usa aiosqlite para I/O no bloqueante en FastAPI.
En producción, reemplazar DATABASE_URL por PostgreSQL o SQL Server.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ── URL de la BD (desde .env o valor por defecto local) ───────────────────────
ROOT_DIR     = Path(__file__).resolve().parent.parent.parent
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{ROOT_DIR / 'data' / 'db' / 'ico.db'}",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # True para debug SQL
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency de FastAPI: abre y cierra sesión por request."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Crea todas las tablas si no existen (llamado en startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
