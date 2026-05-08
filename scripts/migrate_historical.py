"""
migrate_historical.py — Migra el historial de ventas (CSVs) a SQLite

Lee data/raw/ventas.csv + detalle_venta.csv e inserta los registros
en las tablas pedidos + detalle_pedido de ico.db.

Los pedidos históricos quedan con:
  - vendedor_id = NULL  (no había vendedor asignado)
  - estado      = "entregado"
  - desde_recomendacion = False

CÓMO EJECUTAR (una sola vez, antes del primer entrenamiento):
    python scripts/migrate_historical.py

Si ya se ejecutó antes, el script detecta los números de pedido
existentes y no duplica registros.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import AsyncSessionLocal, init_db
from backend.app.models import DetallePedido, Pedido, Producto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR  = ROOT_DIR / "data" / "raw"


async def migrar(db: AsyncSession) -> None:
    ventas_path   = RAW_DIR / "ventas.csv"
    detalle_path  = RAW_DIR / "detalle_venta.csv"

    if not ventas_path.exists() or not detalle_path.exists():
        logger.error("No se encontraron ventas.csv o detalle_venta.csv en %s", RAW_DIR)
        return

    # ── Cargar CSVs ───────────────────────────────────────────────────────────
    ventas  = pd.read_csv(ventas_path,  parse_dates=["fecha_venta"])
    detalle = pd.read_csv(detalle_path, dtype={"producto_id": str})

    logger.info("ventas.csv:         %d filas", len(ventas))
    logger.info("detalle_venta.csv:  %d filas", len(detalle))

    # ── Precios desde tabla productos (ya cargada por seed) ───────────────────
    result   = await db.execute(select(Producto))
    productos = {p.producto_id: p for p in result.scalars().all()}

    if not productos:
        logger.error("La tabla productos está vacía. Ejecuta seed.py primero.")
        return

    # ── Detectar pedidos ya migrados (evitar duplicados) ─────────────────────
    existentes_res = await db.execute(select(Pedido.numero))
    existentes     = {row[0] for row in existentes_res.all()}
    logger.info("Pedidos ya en BD: %d", len(existentes))

    # ── Migrar ────────────────────────────────────────────────────────────────
    insertados  = 0
    omitidos    = 0
    sin_producto = 0

    for _, venta in ventas.iterrows():
        numero = str(venta["venta_id"])

        if numero in existentes:
            omitidos += 1
            continue

        filas_det = detalle[detalle["venta_id"] == venta["venta_id"]]
        if filas_det.empty:
            continue

        # Calcular subtotal desde los detalles (ignorar monto_total del CSV)
        subtotal = float(venta.get("monto_total", 0))

        pedido = Pedido(
            numero     = numero,
            cliente_id = str(venta["cliente_id"]),
            vendedor_id= None,          # histórico: sin vendedor asignado
            estado     = "entregado",
            subtotal   = subtotal,
            impuesto   = 0.0,
            descuento  = 0.0,
            total      = subtotal,
            forma_pago = "historico",
            notas      = "Migrado desde ventas.csv",
            creado_en  = venta["fecha_venta"].to_pydatetime(),
        )
        db.add(pedido)
        await db.flush()   # genera pedido.id

        for _, fila in filas_det.iterrows():
            pid = str(fila["producto_id"])
            prod = productos.get(pid)

            if prod is None:
                sin_producto += 1
                continue

            precio_unit = prod.precio_unitario
            cantidad    = int(fila["cantidad_producto"])
            sub         = float(fila.get("subtotal", precio_unit * cantidad))

            db.add(DetallePedido(
                pedido_id            = pedido.id,
                producto_id          = pid,
                cantidad             = cantidad,
                precio_unit          = precio_unit,
                subtotal             = sub,
                desde_recomendacion  = False,
            ))

        insertados += 1

    await db.commit()

    logger.info("══ Migración completada ══")
    logger.info("  Insertados:          %d pedidos", insertados)
    logger.info("  Omitidos (ya exist): %d", omitidos)
    logger.info("  Detalles sin prod.:  %d (producto no en catálogo)", sin_producto)


async def main() -> None:
    logger.info("Inicializando BD ...")
    await init_db()
    async with AsyncSessionLocal() as db:
        await migrar(db)


if __name__ == "__main__":
    asyncio.run(main())
