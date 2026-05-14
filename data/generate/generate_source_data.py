"""
Script de generación de datos sintéticos para variables fuente.
Genera 4 CSVs alineados con las entidades del modelo:
  - clientes.csv
  - productos.csv
  - ventas.csv
  - detalle_venta.csv

CAMBIO PRINCIPAL v2:
  Cada cliente tiene un perfil de productos favoritos (15-40 productos del catálogo).
  En cada venta el cliente compra principalmente de sus favoritos (80%) y
  ocasionalmente explora el catálogo (20%).

CAMBIO PRINCIPAL v3:
  Clientes: nueva columna sede_cliente.
  Productos: nueva columna sede_producto (sedes separadas por "|").
  Consistencia sede: cliente solo compra productos disponibles en su sede.

CAMBIO PRINCIPAL v4:
  Clientes: 2 nuevas columnas subrubro_1 (especialidad) y subrubro_2 (formato servicio).

CAMBIO PRINCIPAL v5:
  1. Sedes reales: Lima, Piura, Arequipa, Cusco.
  2. Stock por sede: productos.csv ahora incluye columnas de stock
     y dias_en_stock por cada sede, con nombre stock_{sede} y
     dias_en_stock_{sede} (ej: stock_Lima, dias_en_stock_Piura).
     Si el producto no está disponible en una sede, el valor es NULL (vacío).
  3. Un cliente solo puede comprar productos disponibles en su propia sede.
"""

import csv
import random
import string
import sys
import io
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─────────────────────────────────────────
# PARÁMETROS CONFIGURABLES
# ─────────────────────────────────────────
N_CLIENTES              = 800
N_PRODUCTOS             = 950
N_VENTAS                = 7_950
N_DETALLE_POR_VENTA_MIN = 1
N_DETALLE_POR_VENTA_MAX = 8
FECHA_INICIO_VENTAS     = date(2025, 1, 1)
FECHA_FIN_VENTAS        = date(2026, 5, 5)
SEED                    = 42

FAVORITOS_MIN = 15
FAVORITOS_MAX = 40
PROB_FAVORITO = 0.80

random.seed(SEED)

OUTPUT_DIR = "C:/Users/Camila/Downloads/"

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def rand_id(prefix: str, n: int = 6) -> str:
    return f"{prefix}_{''.join(random.choices(string.digits, k=n))}"

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def round2(x: float) -> float:
    return round(x, 2)

# ─────────────────────────────────────────
# SEDES  [ACTUALIZADO v5]
# ─────────────────────────────────────────
# Sedes reales del distribuidor (antes eran zonas de Lima).
# Cada cliente pertenece a una sola sede.
# Cada producto puede estar disponible en 1, 2 o todas las sedes,
# y cada disponibilidad tiene su propio stock independiente.
SEDES = ["Lima", "Piura", "Arequipa", "Cusco"]

# Probabilidad de cobertura de sedes por producto:
#   50% → solo 1 sede  (producto local / perecedero)
#   30% → 2 sedes      (producto regional)
#   20% → todas sedes  (producto de distribución nacional)
PROB_SEDE_UNA   = 0.50
PROB_SEDE_DOS   = 0.30
# PROB_SEDE_TODAS = 0.20

def elegir_sedes_producto(sede_origen: str) -> list:
    """
    Retorna la lista de sedes donde el producto estará disponible.
    La sede de origen siempre está incluida.
    """
    r = random.random()
    if r < PROB_SEDE_UNA:
        return [sede_origen]
    elif r < PROB_SEDE_UNA + PROB_SEDE_DOS:
        otras = [s for s in SEDES if s != sede_origen]
        segunda = random.choice(otras)
        return [sede_origen, segunda]
    else:
        return list(SEDES)   # disponible en todas

# ─────────────────────────────────────────
# 1. CLIENTES
# ─────────────────────────────────────────
RUBROS = [
    "Restaurante", "Panadería", "Supermercado", "Minimarket",
    "Cafetería", "Hotel", "Catering", "Bodega", "Farmacia", "Ferretería",
    "Bar", "Fast Food",
]

# subrubro_1: especialidad principal del negocio
SUBRUBRO_1_POR_RUBRO = {
    "Restaurante":  ["Chifa", "Pollería", "Criollo", "Carnes", "Marino",
                     "Italiano", "Japonés", "Vegetariano", "Fusión", "Buffet"],
    "Panadería":    ["Artesanal", "Industrial", "Pastelería", "Francesa",
                     "Integral", "Repostería"],
    "Supermercado": ["Formato Grande", "Formato Mediano", "Gourmet",
                     "Mayorista", "Orgánico"],
    "Minimarket":   ["Barrio", "24 Horas", "Gasolinera", "Express", "Universitario"],
    "Cafetería":    ["Tradicional", "Moderna", "Temática", "Saludable", "Especialidad"],
    "Hotel":        ["Boutique", "Business", "Turístico", "Resort", "Hostal", "Apart-hotel"],
    "Catering":     ["Eventos Corporativos", "Matrimonios", "Escolar", "Industrial", "Social"],
    "Bodega":       ["Barrio", "Mayorista", "Abarrotes", "Licorería", "Mixta"],
    "Farmacia":     ["Independiente", "Cadena", "Naturista", "Homeopática"],
    "Ferretería":   ["General", "Especializada", "Mayorista", "Industrial"],
    "Bar":          ["Karaoke", "Sports Bar", "Cocteles", "Cervecería",
                     "Vinos", "Lounge", "Pub"],
    "Fast Food":    ["Hamburguesas", "Pollo", "Pizza", "Tacos",
                     "Sándwiches", "Wraps", "Árabe"],
}

# subrubro_2: formato de servicio del negocio
SUBRUBRO_2_POR_RUBRO = {
    "Restaurante":  ["Salón", "Delivery", "Para Llevar", "Delivery + Salón", "Dark Kitchen"],
    "Panadería":    ["Local Propio", "Distribución", "Local + Distribución"],
    "Supermercado": ["Tienda Física", "Online + Tienda", "Solo Online"],
    "Minimarket":   ["Tienda Física", "24 Horas", "Tienda + Delivery"],
    "Cafetería":    ["Salón", "Para Llevar", "Co-Working", "Salón + Delivery"],
    "Hotel":        ["Restaurante Propio", "Desayuno Incluido", "Solo Alojamiento", "Todo Incluido"],
    "Catering":     ["On-Site", "Off-Site", "Mixto"],
    "Bodega":       ["Mostrador", "Autoservicio", "Mostrador + Delivery"],
    "Farmacia":     ["Mostrador", "Autoservicio", "Drive-Thru"],
    "Ferretería":   ["Mostrador", "Autoservicio", "Catálogo Online"],
    "Bar":          ["Presencial", "Reservas", "Presencial + Eventos"],
    "Fast Food":    ["Salón", "Drive-Thru", "Delivery", "Salón + Delivery", "Solo Delivery"],
}

def asignar_subrubros(rubro: str) -> tuple:
    sr1 = random.choice(SUBRUBRO_1_POR_RUBRO.get(rubro, ["General"]))
    sr2 = random.choice(SUBRUBRO_2_POR_RUBRO.get(rubro, ["Presencial"]))
    return sr1, sr2

clientes = []
for _ in range(N_CLIENTES):
    rubro = random.choice(RUBROS)
    sr1, sr2 = asignar_subrubros(rubro)
    clientes.append({
        "cliente_id":    rand_id("CLI"),
        "rubro_cliente": rubro,
        "subrubro_1":    sr1,
        "subrubro_2":    sr2,
        "sede_cliente":  random.choice(SEDES),   # [v5] sedes reales
    })

seen = set()
for c in clientes:
    while c["cliente_id"] in seen:
        c["cliente_id"] = rand_id("CLI")
    seen.add(c["cliente_id"])

clientes_ids = [c["cliente_id"] for c in clientes]

with open(f"{OUTPUT_DIR}/clientes.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=["cliente_id", "rubro_cliente", "subrubro_1", "subrubro_2", "sede_cliente"]
    )
    writer.writeheader()
    writer.writerows(clientes)

print(f"✔ clientes.csv  ({len(clientes)} filas)")

# ─────────────────────────────────────────
# 2. PRODUCTOS  [ACTUALIZADO v5]
# ─────────────────────────────────────────
# Stock por sede en productos.csv [v5]
# ─────────────────────────────────────────
# productos.csv tiene UNA FILA por cada combinación (producto_id, sede)
# donde el producto está disponible.
# La clave primaria es compuesta: (producto_id, sede).
# producto_id solo NO es único — el mismo producto puede tener
# filas distintas para Lima, Piura, etc. con su propio stock.
#
# Ejemplo:
#   producto_id | sede     | stock | dias_en_stock | categoria | ...
#   PROD_001    | Lima     |  145  |      12       | Lácteos   | ...
#   PROD_001    | Piura    |    8  |      45       | Lácteos   | ...
#   PROD_002    | Arequipa |    0  |      90       | Bebidas   | ...
#
# Rangos de stock con sesgo realista:
#   15% agotado (0), 25% stock bajo (1–9), 60% stock normal (10–300)

CATEGORIAS = [
    "Lácteos", "Panadería", "Bebidas", "Carnes", "Verduras",
    "Frutas", "Abarrotes", "Limpieza", "Snacks", "Congelados"
]

def generar_stock():
    """Genera stock aleatorio con distribución realista para una sede."""
    r = random.random()
    if r < 0.15:
        return 0                        # agotado en esta sede
    elif r < 0.40:
        return random.randint(1, 9)     # stock bajo
    else:
        return random.randint(10, 300)  # stock normal

# productos_base: características intrínsecas del producto (iguales en todas las sedes)
productos_base = []
for _ in range(N_PRODUCTOS):
    precio_unitario = round2(random.uniform(1.5, 150.0))
    costo_unitario  = round2(precio_unitario * random.uniform(0.40, 0.75))
    fecha_ingreso   = rand_date(date(2022, 1, 1), date(2026, 5, 31))
    fecha_caducidad = date.today() + timedelta(days=random.randint(-5, 365))

    sede_origen = random.choice(SEDES)
    sedes_prod  = elegir_sedes_producto(sede_origen)

    productos_base.append({
        "producto_id":            rand_id("PROD"),
        "categoria_producto":     random.choice(CATEGORIAS),
        "precio_unitario":        precio_unitario,
        "COSTO_UNITARIO":         costo_unitario,
        "fecha_ingreso_catalogo": fecha_ingreso.isoformat(),
        "fecha_min_caducidad":    fecha_caducidad.isoformat(),
        "_sedes_list":            sedes_prod,   # interno
    })

# Deduplicar producto_id
seen = set()
for p in productos_base:
    while p["producto_id"] in seen:
        p["producto_id"] = rand_id("PROD")
    seen.add(p["producto_id"])

# productos: una fila por (producto_id, sede) — clave compuesta
# Expande cada producto en N filas según cuántas sedes tenga asignadas
productos = []
for p in productos_base:
    for sede in p["_sedes_list"]:
        productos.append({
            "producto_id":            p["producto_id"],
            "sede":                   sede,           # parte de la clave compuesta
            "categoria_producto":     p["categoria_producto"],
            "precio_unitario":        p["precio_unitario"],
            "COSTO_UNITARIO":         p["COSTO_UNITARIO"],
            "stock":                  generar_stock(),
            "dias_en_stock":          random.randint(0, 180),
            "fecha_ingreso_catalogo": p["fecha_ingreso_catalogo"],
            "fecha_min_caducidad":    p["fecha_min_caducidad"],
        })

productos_ids = [p["producto_id"] for p in productos_base]
precio_map    = {p["producto_id"]: p["precio_unitario"] for p in productos_base}

# Índice: stock por (producto_id, sede) para usar en selección de ventas
stock_por_sede = {
    (row["producto_id"], row["sede"]): row["stock"]
    for row in productos
}

PROD_FIELDNAMES = [
    "producto_id", "sede",
    "categoria_producto", "precio_unitario", "COSTO_UNITARIO",
    "stock", "dias_en_stock",
    "fecha_ingreso_catalogo", "fecha_min_caducidad",
]

with open(f"{OUTPUT_DIR}/productos.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=PROD_FIELDNAMES)
    writer.writeheader()
    writer.writerows(productos)

n_base = len(productos_base)
n_rows = len(productos)
print(f"✔ productos.csv   ({n_base} productos únicos → {n_rows} filas con sede)")

# Índices de productos disponibles / con stock por sede
prods_por_sede       = {s: [] for s in SEDES}
prods_con_stock_sede = {s: [] for s in SEDES}

for row in productos:
    prods_por_sede[row["sede"]].append(row["producto_id"])
    if row["stock"] > 0:
        prods_con_stock_sede[row["sede"]].append(row["producto_id"])

print("   Productos disponibles / con stock por sede:")
for sede in SEDES:
    total  = len(prods_por_sede[sede])
    con_st = len(prods_con_stock_sede[sede])
    print(f"     {sede:<12}: {total:>4} disponibles  |  {con_st:>4} con stock > 0")

# ─────────────────────────────────────────
# PERFILES DE FAVORITOS POR CLIENTE
# ─────────────────────────────────────────
CATEGORIAS_POR_RUBRO = {
    "Restaurante":   ["Carnes", "Verduras", "Abarrotes", "Bebidas", "Lácteos"],
    "Panadería":     ["Panadería", "Lácteos", "Abarrotes", "Bebidas"],
    "Supermercado":  ["Lácteos", "Bebidas", "Snacks", "Abarrotes", "Limpieza", "Congelados"],
    "Minimarket":    ["Bebidas", "Snacks", "Abarrotes", "Limpieza"],
    "Cafetería":     ["Panadería", "Bebidas", "Lácteos", "Snacks"],
    "Hotel":         ["Lácteos", "Bebidas", "Frutas", "Carnes", "Limpieza"],
    "Catering":      ["Carnes", "Verduras", "Frutas", "Abarrotes", "Bebidas"],
    "Bodega":        ["Abarrotes", "Bebidas", "Snacks", "Limpieza"],
    "Farmacia":      ["Limpieza", "Abarrotes", "Bebidas"],
    "Ferretería":    ["Limpieza", "Abarrotes", "Bebidas"],
    "Bar":           ["Bebidas", "Snacks", "Abarrotes", "Lácteos"],
    "Fast Food":     ["Carnes", "Panadería", "Bebidas", "Snacks", "Abarrotes"],
}

# Índice combinado categoría × sede para asignación eficiente de favoritos
# Usa productos_base (un registro por producto único) con _sedes_list
prods_cat_sede = {}
for p in productos_base:
    cat = p["categoria_producto"]
    for sede in p["_sedes_list"]:
        prods_cat_sede.setdefault((cat, sede), []).append(p["producto_id"])

def asignar_favoritos(rubro: str, sede: str) -> list:
    """
    Favoritos filtrados por sede: solo productos disponibles en la sede del cliente.
    70% de categorías afines al rubro, 30% de otras categorías.
    """
    n_favs = random.randint(FAVORITOS_MIN, FAVORITOS_MAX)

    cats_afines = CATEGORIAS_POR_RUBRO.get(rubro, CATEGORIAS)
    cats_otras  = [c for c in CATEGORIAS if c not in cats_afines]

    n_afines = max(1, int(n_favs * 0.70))
    n_otras  = n_favs - n_afines

    pool_afines = list(set(
        pid for cat in cats_afines
        for pid in prods_cat_sede.get((cat, sede), [])
    ))
    pool_otras = list(set(
        pid for cat in cats_otras
        for pid in prods_cat_sede.get((cat, sede), [])
    ))

    favoritos = random.sample(pool_afines, k=min(n_afines, len(pool_afines)))
    if pool_otras and n_otras > 0:
        favoritos += random.sample(pool_otras, k=min(n_otras, len(pool_otras)))

    return favoritos

perfil_cliente = {}
for c in clientes:
    perfil_cliente[c["cliente_id"]] = {
        "rubro":     c["rubro_cliente"],
        "sede":      c["sede_cliente"],
        "favoritos": asignar_favoritos(c["rubro_cliente"], c["sede_cliente"]),
    }

total_favs = sum(len(v["favoritos"]) for v in perfil_cliente.values())
print(f"   Promedio de favoritos por cliente: {total_favs/N_CLIENTES:.1f}")

# ─────────────────────────────────────────
# 4. VENTAS + 5. DETALLE_VENTA
# ─────────────────────────────────────────
# La selección de productos respeta:
#   1. Favoritos del cliente → siempre de su sede (garantizado en asignar_favoritos)
#   2. Exploración (20%)    → de prods_con_stock_sede[sede] para ser más realista
#      (un cliente no suele pedir algo agotado, aunque el modelo puede hacerlo)

ventas        = []
detalle_venta = []
seen_venta_ids = set()

for _ in range(N_VENTAS):
    venta_id = rand_id("VTA", 8)
    while venta_id in seen_venta_ids:
        venta_id = rand_id("VTA", 8)
    seen_venta_ids.add(venta_id)

    cliente_id  = random.choice(clientes_ids)
    fecha_venta = rand_date(FECHA_INICIO_VENTAS, FECHA_FIN_VENTAS)

    perfil          = perfil_cliente[cliente_id]
    favoritos       = perfil["favoritos"]
    sede_cli        = perfil["sede"]
    # Para exploración usamos productos con stock > 0 en la sede del cliente
    candidatos_sede = prods_con_stock_sede[sede_cli] or prods_por_sede[sede_cli]

    n_items = random.randint(N_DETALLE_POR_VENTA_MIN, N_DETALLE_POR_VENTA_MAX)

    seleccionados = set()
    prods_venta   = []

    intentos = 0
    while len(prods_venta) < n_items and intentos < n_items * 10:
        intentos += 1
        if favoritos and random.random() < PROB_FAVORITO:
            candidato = random.choice(favoritos)
        else:
            candidato = random.choice(candidatos_sede) if candidatos_sede \
                        else random.choice(productos_ids)

        if candidato not in seleccionados:
            seleccionados.add(candidato)
            prods_venta.append(candidato)

    monto_total = 0.0
    for prod_id in prods_venta:
        cantidad = random.randint(1, 20)
        precio   = precio_map[prod_id]
        subtotal = round2(cantidad * precio)
        monto_total += subtotal

        detalle_venta.append({
            "venta_id":          venta_id,
            "producto_id":       prod_id,
            "cantidad_producto": cantidad,
            "subtotal":          subtotal,
        })

    ventas.append({
        "venta_id":    venta_id,
        "cliente_id":  cliente_id,
        "fecha_venta": fecha_venta.isoformat(),
        "monto_total": round2(monto_total),
    })

with open(f"{OUTPUT_DIR}/ventas.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["venta_id", "cliente_id", "fecha_venta", "monto_total"])
    writer.writeheader()
    writer.writerows(ventas)

print(f"✔ ventas.csv        ({len(ventas)} filas)")

with open(f"{OUTPUT_DIR}/detalle_venta.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["venta_id", "producto_id", "cantidad_producto", "subtotal"])
    writer.writeheader()
    writer.writerows(detalle_venta)

print(f"✔ detalle_venta.csv ({len(detalle_venta)} filas)")

# ─────────────────────────────────────────
# VERIFICACIONES
# ─────────────────────────────────────────
from collections import Counter

# Verificación de recompra
cliente_por_venta = {v["venta_id"]: v["cliente_id"] for v in ventas}
cp_counter = Counter()
for d in detalle_venta:
    cid = cliente_por_venta[d["venta_id"]]
    cp_counter[(cid, d["producto_id"])] += 1

recompras    = sum(1 for v in cp_counter.values() if v > 1)
total_pares  = len(cp_counter)
pct_recompra = recompras / total_pares * 100

# Verificación de consistencia de sede
sede_cli_map       = {c["cliente_id"]: c["sede_cliente"]  for c in clientes}
sedes_prod_map     = {p["producto_id"]: set(p["_sedes_list"]) for p in productos_base}

violaciones_sede = 0
for d in detalle_venta:
    cid  = cliente_por_venta[d["venta_id"]]
    sede = sede_cli_map[cid]
    if sede not in sedes_prod_map.get(d["producto_id"], set()):
        violaciones_sede += 1

print(f"")
print(f"── Verificación de recompra ────────────────────────────────────")
print(f"   Pares únicos (cliente, producto):   {total_pares:,}")
print(f"   Pares con recompra (>1 vez):        {recompras:,}  ({pct_recompra:.1f}%)")
print(f"   Pares sin recompra (compra única):  {total_pares-recompras:,}  ({100-pct_recompra:.1f}%)")
print(f"   Densidad matriz:                    {total_pares/(N_CLIENTES*N_PRODUCTOS)*100:.2f}%")
print(f"")
print(f"── Verificación de consistencia de sede ────────────────────────")
print(f"   Violaciones sede cliente ↔ sede producto: {violaciones_sede}  (esperado: 0)")
print(f"   Sedes:       {SEDES}")
print(f"   Rubros:      {sorted(set(c['rubro_cliente'] for c in clientes))}")
print(f"   Subrubros 1 (muestra): {sorted(set(c['subrubro_1'] for c in clientes))[:6]}")
print(f"   Subrubros 2 (muestra): {sorted(set(c['subrubro_2'] for c in clientes))[:6]}")

print("""
╔══════════════════════════════════════════════════════════════════════╗
║  Variables fuente generadas (v5)                                     ║
╠══════════════════════════════╦═════════════╦════════════════════════╣
║ Variable                     ║ Tipo        ║ Archivo                ║
╠══════════════════════════════╬═════════════╬════════════════════════╣
║ cliente_id                   ║ string      ║ clientes.csv           ║
║ rubro_cliente                ║ string cat. ║ clientes.csv           ║
║ subrubro_1                   ║ string cat. ║ clientes.csv           ║
║ subrubro_2                   ║ string cat. ║ clientes.csv           ║
║ sede_cliente                 ║ string cat. ║ clientes.csv           ║
╠══════════════════════════════╬═════════════╬════════════════════════╣
║ producto_id  (PK compuesta)  ║ string      ║ productos.csv          ║
║ sede         (PK compuesta)  ║ string cat. ║ productos.csv          ║
║ categoria_producto           ║ string cat. ║ productos.csv          ║
║ precio_unitario              ║ float       ║ productos.csv          ║
║ COSTO_UNITARIO               ║ float       ║ productos.csv          ║
║ stock             [NEW v5]   ║ integer     ║ productos.csv          ║
║ dias_en_stock     [NEW v5]   ║ integer     ║ productos.csv          ║
║ fecha_ingreso_catalogo       ║ date        ║ productos.csv          ║
║ fecha_min_caducidad          ║ date        ║ productos.csv          ║
╠══════════════════════════════╬═════════════╬════════════════════════╣
║ venta_id                     ║ string      ║ ventas.csv             ║
║ cliente_id (FK)              ║ string      ║ ventas.csv             ║
║ fecha_venta                  ║ date        ║ ventas.csv             ║
║ monto_total                  ║ float       ║ ventas.csv             ║
╠══════════════════════════════╬═════════════╬════════════════════════╣
║ venta_id (FK)                ║ string      ║ detalle_venta.csv      ║
║ producto_id (FK)             ║ string      ║ detalle_venta.csv      ║
║ cantidad_producto            ║ integer     ║ detalle_venta.csv      ║
║ subtotal                     ║ float       ║ detalle_venta.csv      ║
╠══════════════════════════════╩═════════════╩════════════════════════╣
║  Variables a calcular por el equipo (feature engineering)            ║
║  frecuencia_compra, ticket_promedio, mes, semana_anio, es_feriado,   ║
║  descuento_aplicado, dias_para_vencer                                ║
╚══════════════════════════════════════════════════════════════════════╝
""")
