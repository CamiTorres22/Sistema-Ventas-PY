"""
schemas.py — Modelos Pydantic v2 para request/response de la API
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    rol:          str
    nombre:       str
    vendedor_id:  int


class UsuarioOut(BaseModel):
    id:        int
    nombre:    str
    email:     str
    rol:       str
    activo:    bool

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# CLIENTES
# ──────────────────────────────────────────────────────────────────────────────

class ClienteOut(BaseModel):
    cliente_id:    str
    nombre:        str
    ruc:           Optional[str] = None
    telefono:      Optional[str] = None
    rubro_cliente: str
    subrubro_1:    Optional[str] = None
    subrubro_2:    Optional[str] = None
    sede_cliente:  str
    tipo:          Optional[str] = None
    activo:        bool
    vendedor_id:   Optional[int] = None   # vendedor actualmente asignado

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    cliente_id:    str
    nombre:        str
    ruc:           Optional[str] = None
    telefono:      Optional[str] = None
    rubro_cliente: str
    subrubro_1:    Optional[str] = None
    subrubro_2:    Optional[str] = None
    sede_cliente:  str
    tipo:          Optional[str] = None


class ClienteUpdate(BaseModel):
    nombre:        Optional[str] = None
    ruc:           Optional[str] = None
    telefono:      Optional[str] = None
    rubro_cliente: Optional[str] = None
    subrubro_1:    Optional[str] = None
    subrubro_2:    Optional[str] = None
    sede_cliente:  Optional[str] = None
    tipo:          Optional[str] = None
    activo:        Optional[bool] = None


# ──────────────────────────────────────────────────────────────────────────────
# PRODUCTOS
# ──────────────────────────────────────────────────────────────────────────────

class ProductoOut(BaseModel):
    producto_id:            str
    nombre:                 str
    categoria_producto:     str
    descripcion:            Optional[str] = None
    precio_unitario:        float
    costo_unitario:         float
    stock:                  int
    sede:                   str
    fecha_ingreso_catalogo: Optional[str] = None
    fecha_min_caducidad:    Optional[str] = None
    rotacion_diaria:        float
    baja_rotacion:          int
    activo:                 bool

    model_config = {"from_attributes": True}


class ProductoCreate(BaseModel):
    producto_id:            str
    nombre:                 str
    categoria_producto:     str
    descripcion:            Optional[str] = None
    precio_unitario:        float = Field(gt=0)
    costo_unitario:         float = Field(gt=0)
    stock:                  int   = Field(ge=0, default=0)
    sede:                   str
    fecha_ingreso_catalogo: Optional[str] = None
    fecha_min_caducidad:    Optional[str] = None


class ProductoUpdate(BaseModel):
    nombre:              Optional[str]   = None
    categoria_producto:  Optional[str]   = None
    descripcion:         Optional[str]   = None
    precio_unitario:     Optional[float] = Field(default=None, gt=0)
    costo_unitario:      Optional[float] = Field(default=None, gt=0)
    fecha_min_caducidad: Optional[str]   = None
    activo:              Optional[bool]  = None


class StockUpdate(BaseModel):
    incremento: int = Field(ge=1, description="Unidades a agregar al stock actual")


# ──────────────────────────────────────────────────────────────────────────────
# PEDIDOS / CARRITO
# ──────────────────────────────────────────────────────────────────────────────

class ItemCarrito(BaseModel):
    producto_id:         str
    cantidad:            int = Field(ge=1)
    desde_recomendacion: bool = False


class PedidoCreate(BaseModel):
    cliente_id:  str
    items:       list[ItemCarrito] = Field(min_length=1)
    forma_pago:  Optional[str] = None
    notas:       Optional[str] = None


class DetallePedidoOut(BaseModel):
    producto_id:         str
    nombre:              str
    categoria_producto:  str
    cantidad:            int
    precio_unit:         float
    subtotal:            float
    desde_recomendacion: bool

    model_config = {"from_attributes": True}


class PedidoOut(BaseModel):
    id:          int
    numero:      str
    cliente_id:  str
    vendedor_id: int
    estado:      str
    subtotal:    float
    impuesto:    float
    descuento:   float
    total:       float
    forma_pago:  Optional[str] = None
    notas:       Optional[str] = None
    creado_en:   datetime
    detalles:    list[DetallePedidoOut] = []

    model_config = {"from_attributes": True}


class PedidoResumen(BaseModel):
    """Vista compacta para listados (sin detalles de línea)."""
    id:         int
    numero:     str
    cliente_id: str
    nombre_cliente: str
    estado:     str
    total:      float
    n_productos: int
    creado_en:  datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────────
# RECOMENDACIONES
# ──────────────────────────────────────────────────────────────────────────────

class ProductoRecomendado(BaseModel):
    producto_id:      str
    nombre:           str
    categoria_producto: str
    precio_unitario:  float
    stock:            int
    score_final:      float
    ncf_score:        float
    s_urgency:        float
    s_rotation:       float
    s_novelty:        float
    es_urgente:       bool
    es_nuevo:         bool
    es_baja_rotacion: bool
    dias_para_vencer: Optional[int] = None
    dias_en_catalogo: Optional[int] = None
    rotacion_diaria:  Optional[float] = None


class RecomendacionResponse(BaseModel):
    cliente_id:   str
    tipo:         Literal["general", "urgentes", "baja_rotacion", "nuevos"]
    total:        int
    productos:    list[ProductoRecomendado]
    fecha_calculo: Optional[str] = None


class DashboardResponse(BaseModel):
    cliente_id:      str
    urgentes:        list[ProductoRecomendado]
    baja_rotacion:   list[ProductoRecomendado]
    nuevos:          list[ProductoRecomendado]
    total:           int
    fecha_calculo:   Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN / MÉTRICAS
# ──────────────────────────────────────────────────────────────────────────────

class MetricasModelo(BaseModel):
    ndcg_at_10:          Optional[float] = None
    hitrate_at_10:       Optional[float] = None
    precision_at_10:     Optional[float] = None
    tasa_conversion:     Optional[float] = None
    rotation_coverage:   Optional[float] = None
    n_usuarios:          int
    n_productos:         int
    fecha_entrenamiento: Optional[str] = None
    fecha_ultimo_batch:  Optional[str] = None


class HealthResponse(BaseModel):
    status:          str
    modelo_cargado:  bool
    batch_disponible: bool
    mensaje:         str


class VendedorCreate(BaseModel):
    nombre:   str
    email:    EmailStr
    password: str
    rol:      Literal["vendedor", "admin"] = "vendedor"


class VendedorUpdate(BaseModel):
    nombre:  Optional[str] = None
    email:   Optional[EmailStr] = None
    activo:  Optional[bool] = None
