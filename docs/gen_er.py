"""Genera el diagrama ER en formato Draw.io para el proyecto ICO."""
import os

tables = [
    {
        "id": 10, "x": 40, "y": 100, "w": 250, "name": "usuarios",
        "color": "#dae8fc", "stroke": "#6c8ebf",
        "fields": [
            ("PK", "id", "INT"),
            ("",   "nombre", "VARCHAR(100)"),
            ("",   "email", "VARCHAR(150)"),
            ("",   "hashed_password", "VARCHAR(200)"),
            ("",   "rol", "VARCHAR(20)"),
            ("",   "activo", "BOOL"),
            ("",   "creado_en", "DATETIME"),
        ]
    },
    {
        "id": 80, "x": 700, "y": 100, "w": 250, "name": "clientes",
        "color": "#d5e8d4", "stroke": "#82b366",
        "fields": [
            ("PK", "cliente_id", "VARCHAR(20)"),
            ("",   "nombre", "VARCHAR(150)"),
            ("",   "ruc", "VARCHAR(11)"),
            ("",   "telefono", "VARCHAR(20)"),
            ("",   "rubro_cliente", "VARCHAR(50)"),
            ("",   "subrubro_1", "VARCHAR(50)"),
            ("",   "subrubro_2", "VARCHAR(50)"),
            ("",   "sede_cliente", "VARCHAR(30)"),
            ("",   "tipo", "VARCHAR(30)"),
            ("",   "activo", "BOOL"),
            ("",   "creado_en", "DATETIME"),
        ]
    },
    {
        "id": 170, "x": 360, "y": 290, "w": 250, "name": "cliente_vendedor",
        "color": "#ffe6cc", "stroke": "#d6b656",
        "fields": [
            ("PK", "id", "INT"),
            ("FK", "cliente_id", "VARCHAR(20)"),
            ("FK", "vendedor_id", "INT"),
            ("",   "activo", "BOOL"),
        ]
    },
    {
        "id": 200, "x": 1200, "y": 100, "w": 270, "name": "productos",
        "color": "#e1d5e7", "stroke": "#9673a6",
        "fields": [
            ("PK", "producto_id", "VARCHAR(20)"),
            ("",   "nombre", "VARCHAR(200)"),
            ("",   "categoria_producto", "VARCHAR(50)"),
            ("",   "descripcion", "TEXT"),
            ("",   "precio_unitario", "FLOAT"),
            ("",   "costo_unitario", "FLOAT"),
            ("",   "stock", "INT"),
            ("",   "dias_en_stock", "INT"),
            ("",   "sede", "VARCHAR(30)"),
            ("",   "fecha_ingreso_catalogo", "VARCHAR(10)"),
            ("",   "fecha_min_caducidad", "VARCHAR(10)"),
            ("",   "rotacion_diaria", "FLOAT"),
            ("",   "baja_rotacion", "INT"),
            ("",   "activo", "BOOL"),
            ("",   "actualizado_en", "DATETIME"),
        ]
    },
    {
        "id": 300, "x": 700, "y": 530, "w": 250, "name": "pedidos",
        "color": "#fff2cc", "stroke": "#d6b656",
        "fields": [
            ("PK", "id", "INT"),
            ("",   "numero", "VARCHAR(20)"),
            ("FK", "cliente_id", "VARCHAR(20)"),
            ("FK", "vendedor_id", "INT"),
            ("",   "estado", "VARCHAR(20)"),
            ("",   "subtotal", "FLOAT"),
            ("",   "impuesto", "FLOAT"),
            ("",   "descuento", "FLOAT"),
            ("",   "total", "FLOAT"),
            ("",   "forma_pago", "VARCHAR(50)"),
            ("",   "notas", "TEXT"),
            ("",   "creado_en", "DATETIME"),
            ("",   "actualizado_en", "DATETIME"),
        ]
    },
    {
        "id": 400, "x": 1200, "y": 590, "w": 270, "name": "detalle_pedido",
        "color": "#f8cecc", "stroke": "#b85450",
        "fields": [
            ("PK", "id", "INT"),
            ("FK", "pedido_id", "INT"),
            ("FK", "producto_id", "VARCHAR(20)"),
            ("",   "cantidad", "INT"),
            ("",   "precio_unit", "FLOAT"),
            ("",   "subtotal", "FLOAT"),
            ("",   "desde_recomendacion", "BOOL"),
        ]
    },
    {
        "id": 450, "x": 1560, "y": 100, "w": 280, "name": "predicciones",
        "color": "#d5e8d4", "stroke": "#82b366",
        "fields": [
            ("PK,FK", "cliente_id", "VARCHAR(20)"),
            ("PK,FK", "producto_id", "VARCHAR(20)"),
            ("",      "rank_general", "INT"),
            ("",      "score_final", "FLOAT"),
            ("",      "ncf_score", "FLOAT"),
            ("",      "s_urgency", "FLOAT"),
            ("",      "s_rotation", "FLOAT"),
            ("",      "s_novelty", "FLOAT"),
            ("",      "es_urgente", "INT"),
            ("",      "es_nuevo", "INT"),
            ("",      "es_baja_rotacion", "INT"),
            ("",      "dias_para_vencer", "INT"),
            ("",      "dias_en_catalogo", "INT"),
            ("",      "rotacion_diaria", "FLOAT"),
            ("",      "stock", "INT"),
            ("",      "fecha_generacion", "VARCHAR(10)"),
        ]
    },
    {
        "id": 550, "x": 40, "y": 490, "w": 250, "name": "login_logs",
        "color": "#f5f5f5", "stroke": "#666666",
        "fields": [
            ("PK", "id", "INT"),
            ("",   "email", "VARCHAR(150)"),
            ("",   "usuario_id", "INT"),
            ("",   "nombre", "VARCHAR(100)"),
            ("",   "rol", "VARCHAR(20)"),
            ("",   "exitoso", "BOOL"),
            ("",   "motivo_fallo", "VARCHAR(100)"),
            ("",   "ip_address", "VARCHAR(45)"),
            ("",   "user_agent", "VARCHAR(200)"),
            ("",   "creado_en", "DATETIME"),
        ]
    },
]

edges = [
    (10,  170, "1:N", "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"),
    (80,  170, "1:N", "exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;"),
    (80,  300, "1:N", "exitX=0;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0;entryDx=0;entryDy=0;"),
    (10,  300, "1:N", "exitX=1;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0;entryDx=0;entryDy=0;"),
    (300, 400, "1:N", "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"),
    (200, 400, "1:N", "exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0;entryDx=0;entryDy=0;"),
    (80,  450, "1:N", "exitX=1;exitY=0;exitDx=0;exitDy=0;entryX=0;entryY=0;entryDx=0;entryDy=0;"),
    (200, 450, "1:N", "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"),
]

IND_COLORS = {"PK": "#fff2cc", "FK": "#dae8fc", "PK,FK": "#f8cecc", "": "none"}
ROW_H, HEADER_H, IND_W = 25, 30, 45

def ind_style(ind):
    c = IND_COLORS.get(ind, "none")
    fs = "fontStyle=1;" if ind else ""
    return (f"shape=partialRectangle;connectable=0;fillColor={c};strokeColor=#cccccc;"
            f"top=0;left=0;bottom=0;right=0;{fs}overflow=hidden;fontSize=10;align=center;")

RIGHT_STYLE = ("shape=partialRectangle;connectable=0;fillColor=none;strokeColor=#cccccc;"
               "top=0;left=0;bottom=0;right=0;overflow=hidden;fontSize=11;")
ROW_STYLE   = ("shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=0;"
               "fillColor=none;collapsible=0;dropTarget=0;"
               "points=[[0,0.5],[1,0.5]];portConstraint=eastwest;"
               "fontSize=11;top=0;left=0;right=0;bottom=1;")
EDGE_STYLE  = ("edgeStyle=entityRelationEdgeStyle;endArrow=ERmanyToOne;endFill=0;"
               "startArrow=ERmandOne;startFill=0;fontSize=11;")

lines = []
lines.append('<?xml version="1.0" encoding="UTF-8"?>')
lines.append('<mxGraphModel dx="1800" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2200" pageHeight="1400" math="0" shadow="0">')
lines.append("  <root>")
lines.append('    <mxCell id="0" />')
lines.append('    <mxCell id="1" parent="0" />')
lines.append("")

for t in tables:
    tid = t["id"]
    w   = t["w"]
    h   = HEADER_H + len(t["fields"]) * ROW_H
    tbl_style = (f"shape=table;startSize={HEADER_H};container=1;collapsible=0;"
                 f"childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;"
                 f"resizeLast=1;fontSize=13;fillColor={t['color']};strokeColor={t['stroke']};")
    lines.append(f'    <!-- === {t["name"].upper()} === -->')
    lines.append(f'    <mxCell id="{tid}" value="{t["name"]}" style="{tbl_style}" vertex="1" parent="1">')
    lines.append(f'      <mxGeometry x="{t["x"]}" y="{t["y"]}" width="{w}" height="{h}" as="geometry" />')
    lines.append( "    </mxCell>")
    row_id = tid + 1
    for i, (ind, fname, ftype) in enumerate(t["fields"]):
        y_off    = HEADER_H + i * ROW_H
        field_w  = w - IND_W
        lines.append(f'    <mxCell id="{row_id}" value="" style="{ROW_STYLE}" vertex="1" parent="{tid}">')
        lines.append(f'      <mxGeometry y="{y_off}" width="{w}" height="{ROW_H}" as="geometry" />')
        lines.append( "    </mxCell>")
        lines.append(f'    <mxCell id="{row_id+1}" value="{ind}" style="{ind_style(ind)}" vertex="1" parent="{row_id}" connectable="0">')
        lines.append(f'      <mxGeometry width="{IND_W}" height="{ROW_H}" as="geometry">')
        lines.append(f'        <mxRectangle width="{IND_W}" height="{ROW_H}" as="alternateBounds"/>')
        lines.append( "      </mxGeometry>")
        lines.append( "    </mxCell>")
        lines.append(f'    <mxCell id="{row_id+2}" value="{fname} : {ftype}" style="{RIGHT_STYLE}" vertex="1" parent="{row_id}" connectable="0">')
        lines.append(f'      <mxGeometry x="{IND_W}" width="{field_w}" height="{ROW_H}" as="geometry">')
        lines.append(f'        <mxRectangle width="{field_w}" height="{ROW_H}" as="alternateBounds"/>')
        lines.append( "      </mxGeometry>")
        lines.append( "    </mxCell>")
        row_id += 3
    lines.append("")

eid = 900
for src, tgt, lbl, extra in edges:
    style = EDGE_STYLE + extra
    lines.append(f'    <mxCell id="{eid}" value="{lbl}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">')
    lines.append( '      <mxGeometry relative="1" as="geometry" />')
    lines.append( "    </mxCell>")
    eid += 1

lines.append("  </root>")
lines.append("</mxGraphModel>")

output_path = os.path.join(os.path.dirname(__file__), "er_diagram.drawio")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Generado: {output_path}")
print(f"Tablas: {len(tables)} | Relaciones: {len(edges)} | Lineas: {len(lines)}")
