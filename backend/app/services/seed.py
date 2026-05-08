"""
seed.py — Carga inicial de datos desde los CSVs al SQLite

Importa clientes y productos del dataset_ml.csv / CSVs crudos
y crea un usuario admin y uno vendedor de ejemplo.

CÓMO EJECUTAR (una sola vez al inicio):
    python -m backend.app.services.seed
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import AsyncSessionLocal, init_db
from backend.app.models import Cliente, ClienteVendedor, Producto, Usuario
from backend.app.routers.auth import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DIR  = ROOT_DIR / "data" / "raw"
PROC_DIR = ROOT_DIR / "data" / "processed"


async def seed_usuarios(db: AsyncSession) -> dict[str, int]:
    """Crea usuarios de ejemplo si no existen. Devuelve {email: id}."""
    usuarios = [
        {"nombre": "Maria Andrade",  "email": "admin@ico.com",    "password": "admin123",   "rol": "admin"},
        {"nombre": "Juan Ramirez",   "email": "juan@ico.com",     "password": "vend123",    "rol": "vendedor"},
        {"nombre": "Sofia Paredes",  "email": "sofia@ico.com",    "password": "vend123",    "rol": "vendedor"},
        {"nombre": "Carlos Ruiz",    "email": "carlos@ico.com",   "password": "vend123",    "rol": "vendedor"},
        {"nombre": "Ana Flores",     "email": "ana@ico.com",      "password": "vend123",    "rol": "vendedor"},
    ]
    ids = {}
    for u_data in usuarios:
        res = await db.execute(select(Usuario).where(Usuario.email == u_data["email"]))
        user = res.scalar_one_or_none()
        if not user:
            user = Usuario(
                nombre=u_data["nombre"],
                email=u_data["email"],
                hashed_password=hash_password(u_data["password"]),
                rol=u_data["rol"],
            )
            db.add(user)
            await db.flush()
            logger.info("  Usuario creado: %s (%s)", u_data["email"], u_data["rol"])
        ids[u_data["email"]] = user.id
    await db.commit()
    return ids


async def seed_clientes(db: AsyncSession) -> None:
    """Importa clientes desde clientes.csv si la tabla está vacía."""
    count = (await db.execute(select(Cliente))).scalars().first()
    if count:
        logger.info("  Clientes ya cargados, saltando.")
        return

    path = RAW_DIR / "clientes.csv"
    if not path.exists():
        logger.warning("  clientes.csv no encontrado en %s", RAW_DIR)
        return

    df = pd.read_csv(path, dtype=str)
    # Generar nombre de negocio a partir de rubro (placeholder si no existe columna nombre)
    if "nombre" not in df.columns:
        df["nombre"] = df["cliente_id"]

    for _, row in df.iterrows():
        cliente = Cliente(
            cliente_id=str(row["cliente_id"]),
            nombre=str(row.get("nombre", row["cliente_id"])),
            rubro_cliente=str(row.get("rubro_cliente", "")),
            subrubro_1=str(row.get("subrubro_1", "")) or None,
            subrubro_2=str(row.get("subrubro_2", "")) or None,
            sede_cliente=str(row.get("sede_cliente", "")),
        )
        db.add(cliente)

    await db.commit()
    logger.info("  Clientes importados: %d", len(df))


async def seed_productos(db: AsyncSession) -> None:
    """Importa productos desde dataset_ml.csv (un producto único por producto_id)."""
    count = (await db.execute(select(Producto))).scalars().first()
    if count:
        logger.info("  Productos ya cargados, saltando.")
        return

    # Usar dataset_ml.csv para obtener los campos calculados (rotacion, baja_rotacion, etc.)
    ds_path = PROC_DIR / "dataset_ml.csv"
    if not ds_path.exists():
        logger.warning("  dataset_ml.csv no encontrado en %s", PROC_DIR)
        return

    df = pd.read_csv(
        ds_path,
        parse_dates=["fecha_ingreso_catalogo", "fecha_min_caducidad"],
        usecols=[
            "producto_id", "categoria_producto", "precio_unitario", "COSTO_UNITARIO",
            "stock", "dias_en_stock", "sede",
            "fecha_ingreso_catalogo", "fecha_min_caducidad",
            "rotacion_diaria", "baja_rotacion",
        ],
    )
    # Un producto por sede (mayor stock)
    df = df.sort_values("stock", ascending=False).drop_duplicates("producto_id", keep="first")

    for _, row in df.iterrows():
        prod = Producto(
            producto_id=str(row["producto_id"]),
            nombre=str(row["producto_id"]),       # placeholder hasta tener nombre real
            categoria_producto=str(row["categoria_producto"]),
            precio_unitario=float(row["precio_unitario"]),
            costo_unitario=float(row["COSTO_UNITARIO"]),
            stock=int(row["stock"]),
            dias_en_stock=int(row["dias_en_stock"]),
            sede=str(row["sede"]),
            fecha_ingreso_catalogo=(
                row["fecha_ingreso_catalogo"].strftime("%Y-%m-%d")
                if pd.notna(row["fecha_ingreso_catalogo"]) else None
            ),
            fecha_min_caducidad=(
                row["fecha_min_caducidad"].strftime("%Y-%m-%d")
                if pd.notna(row["fecha_min_caducidad"]) else None
            ),
            rotacion_diaria=float(row["rotacion_diaria"]),
            baja_rotacion=int(row["baja_rotacion"]),
        )
        db.add(prod)

    await db.commit()
    logger.info("  Productos importados: %d", len(df))


async def seed_asignaciones(db: AsyncSession, user_ids: dict[str, int]) -> None:
    """Asigna clientes a vendedores de forma distribuida (demo)."""
    count = (await db.execute(select(ClienteVendedor))).scalars().first()
    if count:
        logger.info("  Asignaciones ya cargadas, saltando.")
        return

    clientes = (await db.execute(select(Cliente))).scalars().all()
    vendedores = [v for k, v in user_ids.items() if k != "admin@ico.com"]

    if not vendedores or not clientes:
        return

    for i, cliente in enumerate(clientes):
        vendedor_id = vendedores[i % len(vendedores)]
        db.add(ClienteVendedor(cliente_id=cliente.cliente_id, vendedor_id=vendedor_id))

    await db.commit()
    logger.info("  Asignaciones creadas: %d", len(clientes))


async def main() -> None:
    logger.info("══ Inicializando base de datos ══")
    await init_db()

    async with AsyncSessionLocal() as db:
        logger.info("Creando usuarios ...")
        user_ids = await seed_usuarios(db)

        logger.info("Importando clientes ...")
        await seed_clientes(db)

        logger.info("Importando productos ...")
        await seed_productos(db)

        logger.info("Asignando clientes a vendedores ...")
        await seed_asignaciones(db, user_ids)

    logger.info("══ Seed completado ══")
    logger.info("")
    logger.info("Usuarios de prueba:")
    logger.info("  Admin:    admin@ico.com    / admin123")
    logger.info("  Vendedor: juan@ico.com     / vend123")
    logger.info("  Vendedor: sofia@ico.com    / vend123")


if __name__ == "__main__":
    asyncio.run(main())
