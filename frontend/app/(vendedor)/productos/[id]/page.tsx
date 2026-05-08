"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Package, ShoppingCart, AlertTriangle, Sparkles, TrendingDown } from "lucide-react";
import { api } from "@/lib/api";
import { useCart } from "@/lib/cart-context";
import type { Producto } from "@/lib/types";

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
}

function diasRestantes(fecha: string): number {
  const hoy = new Date();
  const vence = new Date(fecha);
  return Math.ceil((vence.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24));
}

export default function DetalleProductoPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { addItem, items } = useCart();
  const [producto, setProducto] = useState<Producto | null>(null);
  const [loading, setLoading] = useState(true);
  const [cantidad, setCantidad] = useState(1);
  const [justAdded, setJustAdded] = useState(false);

  useEffect(() => {
    api.productos
      .get(id)
      .then(setProducto)
      .catch(() => router.back())
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="p-6 text-gray-400">Cargando producto...</div>;
  }

  if (!producto) return null;

  const sinStock = producto.stock <= 0;
  const stockBajo = producto.stock > 0 && producto.stock < 10;
  const esNuevo = producto.baja_rotacion === 0 && producto.rotacion_diaria === 0;
  const esBajaRotacion = producto.baja_rotacion === 1;
  const inCart = items.some((i) => i.producto.producto_id === id);

  const diasVence = producto.fecha_min_caducidad
    ? diasRestantes(producto.fecha_min_caducidad)
    : null;
  const proxVencer = diasVence !== null && diasVence <= 30;

  function handleAgregar() {
    for (let i = 0; i < cantidad; i++) {
      addItem(producto!, false);
    }
    setJustAdded(true);
    setTimeout(() => setJustAdded(false), 1500);
  }

  return (
    <div className="p-6 max-w-5xl">
      {/* Volver */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-6 transition-colors"
      >
        <ArrowLeft size={15} />
        Volver al Catálogo
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Panel izquierdo — imagen y código */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col items-center">
          {/* Badges */}
          <div className="w-full flex gap-2 mb-4">
            {esNuevo && (
              <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-700">
                <Sparkles size={11} /> NUEVO
              </span>
            )}
            {esBajaRotacion && (
              <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-orange-100 text-orange-700">
                <TrendingDown size={11} /> BAJA ROTACIÓN
              </span>
            )}
            {proxVencer && (
              <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-red-100 text-red-700">
                <AlertTriangle size={11} /> PRÓX. A VENCER
              </span>
            )}
          </div>

          {/* Imagen placeholder */}
          <div className="w-48 h-48 bg-gray-100 rounded-xl flex items-center justify-center mb-6">
            <Package size={64} className="text-gray-300" />
          </div>

          <p className="text-xs text-gray-400 font-mono mb-1">{producto.producto_id}</p>
          <p className="font-semibold text-gray-900 text-center text-sm">{producto.nombre}</p>
        </div>

        {/* Panel derecho — información */}
        <div className="flex flex-col gap-4">
          {/* Precio */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-3xl font-bold" style={{ color: "#3B5BDB" }}>
              {formatCurrency(producto.precio_unitario)}
            </p>
            <p className="text-sm text-gray-400 mt-0.5">precio unitario</p>
          </div>

          {/* Info del producto */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Información del Producto</h2>
            <div className="space-y-3 text-sm">
              <InfoRow
                label="Stock disponible"
                value={
                  sinStock ? (
                    <span className="text-red-600 font-semibold">Sin stock</span>
                  ) : (
                    <span className={stockBajo ? "text-orange-600 font-semibold" : "font-semibold text-gray-900"}>
                      {producto.stock} unidades{stockBajo ? " (stock bajo)" : ""}
                    </span>
                  )
                }
              />
              {producto.fecha_min_caducidad && (
                <InfoRow
                  label="Fecha de vencimiento"
                  value={
                    <span className={proxVencer ? "text-red-600 font-semibold" : "font-semibold text-gray-900"}>
                      {producto.fecha_min_caducidad}
                      {diasVence !== null && (
                        <span className="text-xs ml-1 font-normal text-gray-400">
                          ({diasVence > 0 ? `${diasVence} días restantes` : "vencido"})
                        </span>
                      )}
                    </span>
                  }
                />
              )}
              {producto.fecha_ingreso_catalogo && (
                <InfoRow
                  label="Ingreso al catálogo"
                  value={<span className="font-semibold text-gray-900">{producto.fecha_ingreso_catalogo}</span>}
                />
              )}
              <InfoRow
                label="Categoría"
                value={<span className="font-semibold text-gray-900">{producto.categoria_producto}</span>}
              />
              <InfoRow
                label="Sede"
                value={<span className="font-semibold text-gray-900">{producto.sede}</span>}
              />
              <InfoRow
                label="Rotación diaria"
                value={
                  <span className="font-semibold text-gray-900">
                    {producto.rotacion_diaria.toFixed(2)} uds/día
                  </span>
                }
              />
            </div>
          </div>

          {/* Agregar al carrito */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <p className="text-sm text-gray-600 font-medium">Cantidad:</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCantidad((q) => Math.max(1, q - 1))}
                  className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-600 hover:bg-gray-50 font-bold"
                >
                  −
                </button>
                <span className="w-10 text-center font-semibold text-gray-900">{cantidad}</span>
                <button
                  onClick={() => setCantidad((q) => Math.min(producto.stock, q + 1))}
                  disabled={sinStock}
                  className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-600 hover:bg-gray-50 font-bold disabled:opacity-40"
                >
                  +
                </button>
              </div>
            </div>
            <button
              onClick={handleAgregar}
              disabled={sinStock}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: justAdded ? "#2f9e44" : "#3B5BDB" }}
            >
              <ShoppingCart size={16} />
              {justAdded ? "¡Agregado al carrito!" : inCart ? "Agregar más al carrito" : "Agregar al carrito"}
            </button>
          </div>
        </div>
      </div>

      {/* Descripción */}
      {producto.descripcion && (
        <div className="mt-4 bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-3">Descripción del Producto</h2>
          <p className="text-sm text-gray-600 leading-relaxed">{producto.descripcion}</p>
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-4">
      <span className="text-gray-500 flex-shrink-0">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}
