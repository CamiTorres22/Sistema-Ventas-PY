"""schemas.py -- Modelos Pydantic v2 para request/response de la API."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field

# AUTH
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
    id:     int
    nombre: str
    email:  str
    rol:    str
    zona:   Optional[str] = None
    activo: bool
    model_config = {"from_attributes": True}

# CLIENTES -- columnas exactas del CSV
class ClienteOut(BaseModel):
    cliente_id:    str
    rubro_cliente: str
    subrubro_1:    Optional[str] = None
    subrubro_2:    Optional[str] = None
    sede_cliente:  str
    vendedor_id:   Optional[int] = None
    model_config = {"from_attributes": True}

class ClienteCreate(BaseModel):
    cliente_id:    str
    rubro_cliente: str
    subrubro_1:    Optional[str] = None
    subrubro_2:    Optional[str] = None
    sede_cliente:  str

class ClienteUpdate(BaseModel):
    rubro_cliente: Optional[str] = None
    subrubro_1:    Optional[str] = None
    subrubro_2:    Optional[str] = None
    sede_cliente:  Optional[str] = None

# PRODUCTOS -- columnas exactas del CSV
class ProductoOut(BaseModel):
    producto_id:            str
    sede:                   str
    categoria_producto:     str
    precio_unitario:        float
    costo_unitario:         float
    stock:                  int
    dias_en_stock:          int
    fecha_ingreso_catalogo: Optional[str] = None
    fecha_min_caducidad:    Optional[str] = None
    model_config = {"from_attributes": True}

class ProductoCreate(BaseModel):
    producto_id:            str
    sede:                   str
    categoria_producto:     str
    precio_unitario:        float = Field(gt=0)
    costo_unitario:         float = Field(gt=0)
    stock:                  int   = Field(ge=0, default=0)
    dias_en_stock:          int   = Field(ge=0, default=0)
    fecha_ingreso_catalogo: Optional[str] = None
    fecha_min_caducidad:    Optional[str] = None

class StockUpdate(BaseModel):
    incremento: int = Field(ge=1)

# VENTAS -- columnas exactas del CSV
class ItemCarrito(BaseModel):
    producto_id: str
    sede:        str
    cantidad:    int = Field(ge=1)

class PedidoCreate(BaseModel):
    cliente_id: str
    fecha_venta: str
    items: list[ItemCarrito] = Field(min_length=1)

class DetallePedidoOut(BaseModel):
    producto_id:       str
    cantidad_producto: int
    subtotal:          float
    model_config = {"from_attributes": True}

class PedidoOut(BaseModel):
    venta_id:    str
    cliente_id:  str
    fecha_venta: str
    monto_total: float
    detalles:    list[DetallePedidoOut] = []
    model_config = {"from_attributes": True}

class PedidoResumen(BaseModel):
    venta_id:    str
    cliente_id:  str
    fecha_venta: str
    monto_total: float
    n_productos: int
    model_config = {"from_attributes": True}

# RECOMENDACIONES
class ProductoRecomendado(BaseModel):
    producto_id:        str
    categoria_producto: str
    precio_unitario:    float
    stock:              int
    score_final:        float
    ncf_score:          float
    s_urgency:          float
    s_rotation:         float
    s_novelty:          float
    es_urgente:         bool
    es_nuevo:           bool
    es_baja_rotacion:   bool
    dias_para_vencer:   Optional[int]   = None
    dias_en_catalogo:   Optional[int]   = None
    rotacion_diaria:    Optional[float] = None

class RecomendacionResponse(BaseModel):
    cliente_id:    str
    tipo:          Literal["general", "urgentes", "baja_rotacion", "nuevos"]
    total:         int
    productos:     list[ProductoRecomendado]
    fecha_calculo: Optional[str] = None

class DashboardResponse(BaseModel):
    cliente_id:    str
    urgentes:      list[ProductoRecomendado]
    baja_rotacion: list[ProductoRecomendado]
    nuevos:        list[ProductoRecomendado]
    total:         int
    fecha_calculo: Optional[str] = None

# ADMIN
class MetricasModelo(BaseModel):
    ndcg_at_10:          Optional[float] = None
    hitrate_at_10:       Optional[float] = None
    n_usuarios:          int
    n_productos:         int
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
    zona:     Optional[str] = None

class VendedorUpdate(BaseModel):
    nombre: Optional[str] = None
    email:  Optional[EmailStr] = None
    zona:   Optional[str] = None
    activo: Optional[bool] = None
