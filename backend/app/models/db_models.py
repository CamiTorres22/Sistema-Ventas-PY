"""db_models.py -- Modelos alineados con tablas Supabase."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre:          Mapped[str]      = mapped_column(String(100), nullable=False)
    email:           Mapped[str]      = mapped_column(String(150), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str]      = mapped_column(String(200), nullable=False)
    rol:             Mapped[str]      = mapped_column(String(20), nullable=False)
    zona:            Mapped[str|None] = mapped_column(String(30))
    activo:          Mapped[bool]     = mapped_column(Boolean, default=True)
    creado_en:       Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    clientes: Mapped[list["ClienteVendedor"]] = relationship(back_populates="vendedor")

# CSV: cliente_id, rubro_cliente, subrubro_1, subrubro_2, sede_cliente
class Cliente(Base):
    __tablename__ = "clientes"
    cliente_id:    Mapped[str]        = mapped_column(String(20), primary_key=True)
    rubro_cliente: Mapped[str]        = mapped_column(String(50), nullable=False)
    subrubro_1:    Mapped[str | None] = mapped_column(String(50))
    subrubro_2:    Mapped[str | None] = mapped_column(String(50))
    sede_cliente:  Mapped[str]        = mapped_column(String(30), nullable=False)
    vendedores: Mapped[list["ClienteVendedor"]] = relationship(back_populates="cliente")
    ventas:     Mapped[list["Venta"]]           = relationship(back_populates="cliente")

class ClienteVendedor(Base):
    __tablename__ = "cliente_vendedor"
    id:          Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id:  Mapped[str]  = mapped_column(ForeignKey("clientes.cliente_id"), nullable=False)
    vendedor_id: Mapped[int]  = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    activo:      Mapped[bool] = mapped_column(Boolean, default=True)
    cliente:  Mapped["Cliente"]  = relationship(back_populates="vendedores")
    vendedor: Mapped["Usuario"]  = relationship(back_populates="clientes")

# CSV: producto_id, sede, categoria_producto, precio_unitario, costo_unitario,
#      stock, dias_en_stock, fecha_ingreso_catalogo, fecha_min_caducidad
class Producto(Base):
    __tablename__ = "productos"
    producto_id:            Mapped[str]        = mapped_column(String(20), primary_key=True)
    sede:                   Mapped[str]        = mapped_column(String(30), primary_key=True)
    nombre:                 Mapped[str | None] = mapped_column(String(100))
    categoria_producto:     Mapped[str]        = mapped_column(String(50), nullable=False)
    precio_unitario:        Mapped[float]      = mapped_column(Float, nullable=False)
    costo_unitario:         Mapped[float]      = mapped_column(Float, nullable=False)
    stock:                  Mapped[int]        = mapped_column(Integer, default=0)
    dias_en_stock:          Mapped[int]        = mapped_column(Integer, default=0)
    fecha_ingreso_catalogo: Mapped[str | None] = mapped_column(String(10))
    fecha_min_caducidad:    Mapped[str | None] = mapped_column(String(10))

# CSV: venta_id, cliente_id, fecha_venta, monto_total
class Venta(Base):
    __tablename__ = "ventas"
    venta_id:    Mapped[str]   = mapped_column(String(20), primary_key=True)
    cliente_id:  Mapped[str]   = mapped_column(ForeignKey("clientes.cliente_id"), nullable=False)
    fecha_venta: Mapped[str]   = mapped_column(String(10), nullable=False)
    monto_total: Mapped[float] = mapped_column(Float, default=0.0)
    cliente:  Mapped["Cliente"]            = relationship(back_populates="ventas")
    detalles: Mapped[list["DetalleVenta"]] = relationship(back_populates="venta", cascade="all, delete-orphan")

# CSV: venta_id, producto_id, cantidad_producto, subtotal
class DetalleVenta(Base):
    __tablename__ = "detalle_venta"
    venta_id:          Mapped[str]   = mapped_column(ForeignKey("ventas.venta_id"), primary_key=True)
    producto_id:       Mapped[str]   = mapped_column(String(20), primary_key=True)
    cantidad_producto: Mapped[int]   = mapped_column(Integer, nullable=False)
    subtotal:          Mapped[float] = mapped_column(Float, nullable=False)
    venta: Mapped["Venta"] = relationship(back_populates="detalles")

class LoginLog(Base):
    __tablename__ = "login_logs"
    id:           Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    email:        Mapped[str]        = mapped_column(String(150), nullable=False, index=True)
    usuario_id:   Mapped[int | None] = mapped_column(Integer)
    nombre:       Mapped[str | None] = mapped_column(String(100))
    rol:          Mapped[str | None] = mapped_column(String(20))
    exitoso:      Mapped[bool]       = mapped_column(Boolean, nullable=False)
    motivo_fallo: Mapped[str | None] = mapped_column(String(100))
    ip_address:   Mapped[str | None] = mapped_column(String(45))
    user_agent:   Mapped[str | None] = mapped_column(String(200))
    creado_en:    Mapped[datetime]   = mapped_column(DateTime, server_default=func.now(), index=True)

class Prediccion(Base):
    __tablename__ = "predicciones"
    cliente_id:       Mapped[str]          = mapped_column(String(20), primary_key=True)
    producto_id:      Mapped[str]          = mapped_column(String(20), primary_key=True)
    rank_general:     Mapped[int]          = mapped_column(Integer, nullable=False)
    score_final:      Mapped[float]        = mapped_column(Float, nullable=False)
    ncf_score:        Mapped[float]        = mapped_column(Float, nullable=False)
    s_urgency:        Mapped[float]        = mapped_column(Float, nullable=False)
    s_rotation:       Mapped[float]        = mapped_column(Float, nullable=False)
    s_novelty:        Mapped[float]        = mapped_column(Float, nullable=False)
    es_urgente:       Mapped[int]          = mapped_column(Integer, nullable=False, default=0)
    es_nuevo:         Mapped[int]          = mapped_column(Integer, nullable=False, default=0)
    es_baja_rotacion: Mapped[int]          = mapped_column(Integer, nullable=False, default=0)
    dias_para_vencer: Mapped[int | None]   = mapped_column(Integer)
    dias_en_catalogo: Mapped[int | None]   = mapped_column(Integer)
    rotacion_diaria:  Mapped[float | None] = mapped_column(Float)
    stock:            Mapped[int | None]   = mapped_column(Integer)
    fecha_generacion: Mapped[str]          = mapped_column(String(10), nullable=False)
