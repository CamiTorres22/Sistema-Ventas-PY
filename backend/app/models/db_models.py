"""
db_models.py — Modelos SQLAlchemy (ORM)

Define las tablas de la BD local. La tabla `predicciones` es creada
directamente por batch_inference.py (SQLite nativo), por lo que no
se incluye aquí como modelo ORM para evitar conflictos de esquema.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


# ──────────────────────────────────────────────────────────────────────────────
# USUARIOS (vendedores y administradores)
# ──────────────────────────────────────────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"

    id:             Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre:         Mapped[str]  = mapped_column(String(100), nullable=False)
    email:          Mapped[str]  = mapped_column(String(150), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    rol:            Mapped[str]  = mapped_column(String(20), nullable=False)  # "vendedor" | "admin"
    activo:         Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en:      Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relaciones
    clientes: Mapped[list["ClienteVendedor"]] = relationship(back_populates="vendedor")
    pedidos:  Mapped[list["Pedido"]]          = relationship(back_populates="vendedor")


# ──────────────────────────────────────────────────────────────────────────────
# CLIENTES (negocio HORECA)
# ──────────────────────────────────────────────────────────────────────────────

class Cliente(Base):
    __tablename__ = "clientes"

    cliente_id:    Mapped[str]  = mapped_column(String(20), primary_key=True)
    nombre:        Mapped[str]  = mapped_column(String(150), nullable=False)
    ruc:           Mapped[str | None] = mapped_column(String(11))
    telefono:      Mapped[str | None] = mapped_column(String(20))
    rubro_cliente: Mapped[str]  = mapped_column(String(50), nullable=False)
    subrubro_1:    Mapped[str | None] = mapped_column(String(50))
    subrubro_2:    Mapped[str | None] = mapped_column(String(50))
    sede_cliente:  Mapped[str]  = mapped_column(String(30), nullable=False)
    tipo:          Mapped[str | None] = mapped_column(String(30))   # Mayorista | Minorista | Corporativo
    activo:        Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en:     Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relaciones
    vendedores: Mapped[list["ClienteVendedor"]] = relationship(back_populates="cliente")
    pedidos:    Mapped[list["Pedido"]]          = relationship(back_populates="cliente")


# ──────────────────────────────────────────────────────────────────────────────
# ASIGNACIÓN CLIENTE ↔ VENDEDOR
# ──────────────────────────────────────────────────────────────────────────────

class ClienteVendedor(Base):
    __tablename__ = "cliente_vendedor"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id:  Mapped[str] = mapped_column(ForeignKey("clientes.cliente_id"), nullable=False)
    vendedor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    activo:      Mapped[bool] = mapped_column(Boolean, default=True)

    cliente:  Mapped["Cliente"]  = relationship(back_populates="vendedores")
    vendedor: Mapped["Usuario"]  = relationship(back_populates="clientes")


# ──────────────────────────────────────────────────────────────────────────────
# PRODUCTOS
# ──────────────────────────────────────────────────────────────────────────────

class Producto(Base):
    __tablename__ = "productos"

    producto_id:           Mapped[str]   = mapped_column(String(20), primary_key=True)
    nombre:                Mapped[str]   = mapped_column(String(200), nullable=False)
    categoria_producto:    Mapped[str]   = mapped_column(String(50), nullable=False)
    descripcion:           Mapped[str | None] = mapped_column(Text)
    precio_unitario:       Mapped[float] = mapped_column(Float, nullable=False)
    costo_unitario:        Mapped[float] = mapped_column(Float, nullable=False)
    stock:                 Mapped[int]   = mapped_column(Integer, default=0)
    dias_en_stock:         Mapped[int]   = mapped_column(Integer, default=0)
    sede:                  Mapped[str]   = mapped_column(String(30), nullable=False)
    fecha_ingreso_catalogo: Mapped[str | None] = mapped_column(String(10))  # ISO date
    fecha_min_caducidad:   Mapped[str | None] = mapped_column(String(10))   # ISO date
    rotacion_diaria:       Mapped[float] = mapped_column(Float, default=0.0)
    baja_rotacion:         Mapped[int]   = mapped_column(Integer, default=0)  # 0|1
    activo:                Mapped[bool]  = mapped_column(Boolean, default=True)
    actualizado_en:        Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    detalles: Mapped[list["DetallePedido"]] = relationship(back_populates="producto")


# ──────────────────────────────────────────────────────────────────────────────
# PEDIDOS
# ──────────────────────────────────────────────────────────────────────────────

class Pedido(Base):
    __tablename__ = "pedidos"

    id:           Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero:       Mapped[str]   = mapped_column(String(20), unique=True, nullable=False)
    cliente_id:   Mapped[str]   = mapped_column(ForeignKey("clientes.cliente_id"), nullable=False)
    vendedor_id:  Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    estado:       Mapped[str]   = mapped_column(String(20), default="pendiente")
    # estados: pendiente | en_proceso | completado | cancelado
    subtotal:     Mapped[float] = mapped_column(Float, default=0.0)
    impuesto:     Mapped[float] = mapped_column(Float, default=0.0)
    descuento:    Mapped[float] = mapped_column(Float, default=0.0)
    total:        Mapped[float] = mapped_column(Float, default=0.0)
    forma_pago:   Mapped[str | None] = mapped_column(String(50))
    notas:        Mapped[str | None] = mapped_column(Text)
    creado_en:    Mapped[datetime]   = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    cliente:  Mapped["Cliente"]          = relationship(back_populates="pedidos")
    vendedor: Mapped["Usuario | None"]   = relationship(back_populates="pedidos")
    detalles: Mapped[list["DetallePedido"]] = relationship(back_populates="pedido", cascade="all, delete-orphan")


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE DE PEDIDO (líneas del carrito)
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# LOGS DE SESIÓN (auditoría de accesos)
# ──────────────────────────────────────────────────────────────────────────────

class LoginLog(Base):
    __tablename__ = "login_logs"

    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    email:       Mapped[str]        = mapped_column(String(150), nullable=False, index=True)
    usuario_id:  Mapped[int | None] = mapped_column(Integer, nullable=True)   # NULL si credenciales inválidas
    nombre:      Mapped[str | None] = mapped_column(String(100))
    rol:         Mapped[str | None] = mapped_column(String(20))
    exitoso:     Mapped[bool]       = mapped_column(Boolean, nullable=False)
    motivo_fallo: Mapped[str | None] = mapped_column(String(100))             # ej: "Contraseña incorrecta"
    ip_address:  Mapped[str | None] = mapped_column(String(45))               # IPv4 o IPv6
    user_agent:  Mapped[str | None] = mapped_column(String(200))
    creado_en:   Mapped[datetime]   = mapped_column(DateTime, server_default=func.now(), index=True)


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"

    id:          Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id:   Mapped[int]   = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    producto_id: Mapped[str]   = mapped_column(ForeignKey("productos.producto_id"), nullable=False)
    cantidad:    Mapped[int]   = mapped_column(Integer, nullable=False)
    precio_unit: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal:    Mapped[float] = mapped_column(Float, nullable=False)
    # Flag: indica si este ítem vino de una recomendación
    desde_recomendacion: Mapped[bool] = mapped_column(Boolean, default=False)

    pedido:   Mapped["Pedido"]   = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship(back_populates="detalles")
