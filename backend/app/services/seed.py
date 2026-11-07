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
from backend.app.models import Cliente, ClienteVendedor, Producto, Usuario, Venta, DetalleVenta
from backend.app.routers.auth import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
RAW_DIR  = ROOT_DIR / "data" / "raw"
PROC_DIR = ROOT_DIR / "data" / "processed"


async def seed_usuarios(db: AsyncSession) -> dict[str, int]:
    """Crea usuarios de ejemplo si no existen. Devuelve {email: id}."""
    usuarios = [
        {"nombre": "Maria Andrade",  "email": "admin@ico.com",    "password": "admin123",   "rol": "admin",     "zona": None},
        {"nombre": "Juan Ramirez",   "email": "juan@ico.com",     "password": "vend123",    "rol": "vendedor",  "zona": "Lima"},
        {"nombre": "Minato Perez",   "email": "minato@ico.com",   "password": "vend123",    "rol": "vendedor",  "zona": "Lima"},
        {"nombre": "Sofia Paredes",  "email": "sofia@ico.com",    "password": "vend123",    "rol": "vendedor",  "zona": "Arequipa"},
        {"nombre": "Carlos Ruiz",    "email": "carlos@ico.com",   "password": "vend123",    "rol": "vendedor",  "zona": "Piura"},
        {"nombre": "Ana Flores",     "email": "ana@ico.com",      "password": "vend123",    "rol": "vendedor",  "zona": "Cusco"},
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
                zona=u_data["zona"],
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

    for _, row in df.iterrows():
        cliente = Cliente(
            cliente_id=str(row["cliente_id"]),
            rubro_cliente=str(row.get("rubro_cliente", "")),
            subrubro_1=str(row.get("subrubro_1", "")) or None,
            subrubro_2=str(row.get("subrubro_2", "")) or None,
            sede_cliente=str(row.get("sede_cliente", "")),
        )
        db.add(cliente)

    await db.commit()
    logger.info("  Clientes importados: %d", len(df))


async def seed_productos(db: AsyncSession) -> None:
    """Importa productos desde dataset_ml.csv o productos.csv (fallback)."""
    count = (await db.execute(select(Producto))).scalars().first()
    if count:
        logger.info("  Productos ya cargados, saltando.")
        return

    ds_path  = PROC_DIR / "dataset_ml.csv"
    raw_path = RAW_DIR  / "productos.csv"

    if ds_path.exists():
        df = pd.read_csv(
            ds_path,
            parse_dates=["fecha_ingreso_catalogo", "fecha_min_caducidad"],
        )
        df = df.sort_values("stock", ascending=False).drop_duplicates("producto_id", keep="first")
        source = "dataset_ml.csv"
    elif raw_path.exists():
        df = pd.read_csv(
            raw_path,
            parse_dates=["fecha_ingreso_catalogo", "fecha_min_caducidad"],
        )
        # Un producto por id (mayor stock entre sedes)
        df = df.sort_values("stock", ascending=False).drop_duplicates("producto_id", keep="first")
        if "COSTO_UNITARIO" not in df.columns:
            df["COSTO_UNITARIO"] = df["precio_unitario"] * 0.6
        source = "productos.csv"
    else:
        logger.warning("  No se encontro dataset_ml.csv ni productos.csv.")
        return

    for _, row in df.iterrows():
        prod = Producto(
            producto_id=str(row["producto_id"]),
            categoria_producto=str(row["categoria_producto"]),
            precio_unitario=float(row["precio_unitario"]),
            costo_unitario=float(row.get("COSTO_UNITARIO", row.get("costo_unitario", row["precio_unitario"] * 0.6))),
            stock=int(row["stock"]),
            dias_en_stock=int(row.get("dias_en_stock", 0)),
            sede=str(row["sede"]),
            fecha_ingreso_catalogo=(
                row["fecha_ingreso_catalogo"].strftime("%Y-%m-%d")
                if pd.notna(row["fecha_ingreso_catalogo"]) else None
            ) if "fecha_ingreso_catalogo" in row and pd.notna(row.get("fecha_ingreso_catalogo")) else None,
            fecha_min_caducidad=(
                row["fecha_min_caducidad"].strftime("%Y-%m-%d")
                if pd.notna(row["fecha_min_caducidad"]) else None
            ) if "fecha_min_caducidad" in row and pd.notna(row.get("fecha_min_caducidad")) else None,
        )
        db.add(prod)

    await db.commit()
    logger.info("  Productos importados: %d (fuente: %s)", len(df), source)


async def seed_asignaciones(db: AsyncSession, user_ids: dict[str, int]) -> None:
    """Asigna cada cliente al vendedor cuya zona coincide con la sede del cliente."""
    count = (await db.execute(select(ClienteVendedor))).scalars().first()
    if count:
        logger.info("  Asignaciones ya cargadas, saltando.")
        return

    clientes = (await db.execute(select(Cliente))).scalars().all()

    # Construir mapa zona → lista de vendedor_ids (una zona puede tener varios vendedores)
    vendedores_db = (
        await db.execute(select(Usuario).where(Usuario.rol == "vendedor"))
    ).scalars().all()
    zona_a_vendedores: dict[str, list[int]] = {}
    for v in vendedores_db:
        if v.zona:
            zona_a_vendedores.setdefault(v.zona, []).append(v.id)

    if not zona_a_vendedores or not clientes:
        return

    # Fallback: todos los vendedores en orden para clientes sin zona coincidente
    fallback = [vid for ids in zona_a_vendedores.values() for vid in ids]

    # Contador por zona para repartir en round-robin entre vendedores de la misma zona
    zona_counter: dict[str, int] = {zona: 0 for zona in zona_a_vendedores}

    sin_zona = 0
    for i, cliente in enumerate(clientes):
        sede = cliente.sede_cliente
        if sede in zona_a_vendedores:
            ids_zona = zona_a_vendedores[sede]
            vendedor_id = ids_zona[zona_counter[sede] % len(ids_zona)]
            zona_counter[sede] += 1
        else:
            vendedor_id = fallback[i % len(fallback)]
            sin_zona += 1
        db.add(ClienteVendedor(cliente_id=cliente.cliente_id, vendedor_id=vendedor_id))

    await db.commit()
    logger.info("  Asignaciones creadas: %d (sin zona coincidente: %d)", len(clientes), sin_zona)


async def seed_ventas(db: AsyncSession) -> None:
    """Importa historial de ventas desde dataset_ml.csv si la tabla está vacía."""
    count = (await db.execute(select(Venta))).scalars().first()
    if count:
        logger.info("  Ventas ya cargadas, saltando.")
        return

    path = PROC_DIR / "dataset_ml.csv"
    if not path.exists():
        logger.warning("  dataset_ml.csv no encontrado en %s", PROC_DIR)
        return

    df = pd.read_csv(path, dtype={"venta_id": str, "cliente_id": str, "producto_id": str})
    df["fecha_venta"] = pd.to_datetime(df["fecha_venta"]).dt.strftime("%Y-%m-%d")

    # Ventas únicas
    ventas_df = (
        df[["venta_id", "cliente_id", "fecha_venta", "monto_total"]]
        .drop_duplicates("venta_id")
    )
    for _, row in ventas_df.iterrows():
        db.add(Venta(
            venta_id=row["venta_id"],
            cliente_id=row["cliente_id"],
            fecha_venta=row["fecha_venta"],
            monto_total=float(row["monto_total"]),
        ))
    await db.flush()

    # Detalles
    for _, row in df.iterrows():
        db.add(DetalleVenta(
            venta_id=row["venta_id"],
            producto_id=row["producto_id"],
            cantidad_producto=int(row["cantidad_producto"]),
            subtotal=float(row["subtotal"]),
        ))

    await db.commit()
    logger.info("  Ventas importadas: %d | Detalles: %d", len(ventas_df), len(df))


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

        logger.info("Importando historial de ventas ...")
        await seed_ventas(db)

    logger.info("══ Seed completado ══")
    logger.info("")
    logger.info("Usuarios de prueba:")
    logger.info("  Admin:    admin@ico.com    / admin123")
    logger.info("  Vendedor: juan@ico.com     / vend123")
    logger.info("  Vendedor: sofia@ico.com    / vend123")


if __name__ == "__main__":
    asyncio.run(main())
