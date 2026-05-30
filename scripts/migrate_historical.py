"""
migrate_historical.py -- Migra el historial de ventas a Supabase

Usa COPY FROM (protocolo bulk de PostgreSQL) para insertar
7.950 pedidos y 35.000+ detalles en segundos.

COMO EJECUTAR:
    python -m scripts.migrate_historical
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR  = ROOT_DIR / "data" / "raw"


def df_to_tsv(df: pd.DataFrame, columns: list) -> io.StringIO:
    buf = io.StringIO()
    for _, row in df.iterrows():
        vals = []
        for col in columns:
            v = row[col]
            if pd.isna(v) or v is None:
                vals.append("")
            else:
                vals.append(str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " "))
        buf.write("\t".join(vals) + "\n")
    buf.seek(0)
    return buf


def migrar() -> None:
    direct_url = os.getenv("DIRECT_URL")
    if not direct_url:
        raise RuntimeError("DIRECT_URL no definido en .env")

    ventas_path  = RAW_DIR / "ventas.csv"
    detalle_path = RAW_DIR / "detalle_venta.csv"

    if not ventas_path.exists() or not detalle_path.exists():
        logger.error("No se encontraron los CSVs en %s", RAW_DIR)
        return

    ventas  = pd.read_csv(ventas_path, parse_dates=["fecha_venta"])
    detalle = pd.read_csv(detalle_path, dtype={"producto_id": str})

    logger.info("ventas.csv:         %d filas", len(ventas))
    logger.info("detalle_venta.csv:  %d filas", len(detalle))

    conn = psycopg2.connect(direct_url)
    cur  = conn.cursor()

    # Pedidos ya existentes
    cur.execute("SELECT numero FROM pedidos")
    existentes = {row[0] for row in cur.fetchall()}
    logger.info("Pedidos ya en BD: %d", len(existentes))

    # Productos en BD
    cur.execute("SELECT producto_id FROM productos")
    productos_bd = {row[0] for row in cur.fetchall()}

    # -- Preparar pedidos nuevos --------------------------------------------------
    nuevas = ventas[~ventas["venta_id"].astype(str).isin(existentes)].copy()
    logger.info("Ventas nuevas a insertar: %d", len(nuevas))

    if nuevas.empty:
        logger.info("Nada que hacer.")
        cur.close(); conn.close(); return

    nuevas["numero"]      = nuevas["venta_id"].astype(str)
    nuevas["vendedor_id"] = None
    nuevas["estado"]      = "entregado"
    nuevas["impuesto"]    = 0.0
    nuevas["descuento"]   = 0.0
    nuevas["forma_pago"]  = "historico"
    nuevas["notas"]       = "Migrado desde ventas.csv"
    nuevas["subtotal"]    = nuevas["monto_total"].fillna(0.0)
    nuevas["total"]       = nuevas["monto_total"].fillna(0.0)
    nuevas["creado_en"]   = nuevas["fecha_venta"].dt.strftime("%Y-%m-%d %H:%M:%S")

    pedidos_cols = ["numero", "cliente_id", "vendedor_id", "estado",
                    "subtotal", "impuesto", "descuento", "total",
                    "forma_pago", "notas", "creado_en"]

    # -- COPY pedidos (bulk insert) -----------------------------------------------
    logger.info("COPY pedidos...")
    buf = df_to_tsv(nuevas, pedidos_cols)
    cur.copy_from(buf, "pedidos", columns=pedidos_cols, null="")
    conn.commit()
    logger.info("  Pedidos copiados: %d", len(nuevas))

    # -- Recuperar id -> numero mapping -------------------------------------------
    cur.execute("SELECT id, numero FROM pedidos WHERE forma_pago = 'historico'")
    numero_to_id = {numero: pid for pid, numero in cur.fetchall()}

    # -- Preparar detalles --------------------------------------------------------
    det = detalle.copy()
    det["venta_id_str"] = det["venta_id"].astype(str)
    det["pedido_id"] = det["venta_id_str"].map(numero_to_id)
    det = det.dropna(subset=["pedido_id"])
    det["pedido_id"] = det["pedido_id"].astype(int)

    # Solo productos que existen en BD
    antes = len(det)
    det = det[det["producto_id"].isin(productos_bd)]
    sin_prod = antes - len(det)

    det["precio_unit"] = (det["subtotal"].fillna(0) / det["cantidad_producto"].clip(lower=1)).round(4)
    det["desde_recomendacion"] = False

    det_cols = ["pedido_id", "producto_id", "cantidad_producto", "precio_unit", "subtotal", "desde_recomendacion"]

    # Renombrar columna para coincidir con la tabla
    det = det.rename(columns={"cantidad_producto": "cantidad"})
    det_cols_renamed = ["pedido_id", "producto_id", "cantidad", "precio_unit", "subtotal", "desde_recomendacion"]

    logger.info("COPY detalle_pedido (%d filas)...", len(det))
    buf2 = df_to_tsv(det, det_cols_renamed)
    cur.copy_from(buf2, "detalle_pedido", columns=det_cols_renamed, null="")
    conn.commit()

    # Conteos finales
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE forma_pago = 'historico'")
    total_ped = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM detalle_pedido")
    total_det = cur.fetchone()[0]
    cur.close(); conn.close()

    logger.info("== Migracion completada ==")
    logger.info("  Pedidos historicos en BD:  %d", total_ped)
    logger.info("  Detalles en BD:            %d", total_det)
    logger.info("  Detalles sin producto:     %d", sin_prod)


if __name__ == "__main__":
    migrar()
