"""
database.py — Configuración de SQLAlchemy + PostgreSQL (async via asyncpg)

Usa asyncpg para I/O no bloqueante en FastAPI.
Conecta a Supabase usando la cadena DATABASE_URL del archivo .env.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
)

# El pooler de transacciones de Supabase (puerto 6543 / PgBouncer) no soporta
# prepared statements — se deshabilitan via statement_cache_size=0.
_pgbouncer = ":6543/" in DATABASE_URL
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"statement_cache_size": 0} if _pgbouncer else {},
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
