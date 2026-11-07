"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, ShoppingCart, Package, Plus, Minus } from "lucide-react";
import { api } from "@/lib/api";
import { useCart } from "@/lib/cart-context";
import type { Producto } from "@/lib/types";

const categorias = [
  "Todas",
  "Abarrotes",
  "Bebidas",
  "Carnes",
  "Congelados",
  "Frutas",
  "Lácteos",
  "Limpieza",
  "Panadería",
  "Snacks",
  "Verduras",
];

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
}

export default function ProductosPage() {
  const { addItem, items } = useCart();
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [buscar, setBuscar] = useState("");
  const [categoria, setCategoria] = useState("Todas");
  const [added, setAdded] = useState<string | null>(null);

  useEffect(() => {
    api.productos
      .list({ limit: 1000 })
      .then(setProductos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = productos.filter((p) => {
    const q = buscar.toLowerCase();
    const matchQ = !q ||
      p.producto_id.toLowerCase().includes(q) ||
      (p.nombre ?? "").toLowerCase().includes(q) ||
      p.categoria_producto.toLowerCase().includes(q);
    const matchCat = categoria === "Todas" || p.categoria_producto === categoria;
    return matchQ && matchCat;
  });

  function handleAdd(p: Producto, cantidad: number) {
    for (let i = 0; i < cantidad; i++) addItem(p, false);
    setAdded(p.producto_id);
    setTimeout(() => setAdded(null), 1200);
  }

  const inCart = (id: string) => items.some((i) => i.producto.producto_id === id);

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Catálogo de Productos</h1>
        <p className="text-gray-500 mt-1">{filtered.length} productos disponibles</p>
      </div>

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar producto..."
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>
        <select
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          className="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          {categorias.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando productos...</div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center text-gray-400">No se encontraron productos.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((p) => (
            <ProductCard
              key={p.producto_id}
              producto={p}
              inCart={inCart(p.producto_id)}
              justAdded={added === p.producto_id}
              onAdd={(cantidad) => handleAdd(p, cantidad)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ProductCard({
  producto,
  inCart,
  justAdded,
  onAdd,
}: {
  producto: Producto;
  inCart: boolean;
  justAdded: boolean;
  onAdd: (cantidad: number) => void;
}) {
  const [cantidad, setCantidad] = useState(1);
  const stockBajo = producto.stock > 0 && producto.stock < 10;
  const sinStock = producto.stock <= 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col hover:shadow-md transition-shadow">
      {/* Badge stock */}
      <div className="h-1.5" style={{ backgroundColor: sinStock ? "#e03131" : stockBajo ? "#f76707" : "#2f9e44" }} />

      <div className="p-4 flex-1 flex flex-col">
        <div className="mb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <Package size={20} className="text-gray-400" />
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium mt-0.5 ${
              sinStock
                ? "bg-red-100 text-red-700"
                : stockBajo
                ? "bg-orange-100 text-orange-700"
                : "bg-green-100 text-green-700"
            }`}>
              {sinStock ? "Sin stock" : `${producto.stock} uds.`}
            </span>
          </div>
          <Link
            href={`/productos/${producto.producto_id}`}
            className="font-semibold text-gray-900 text-sm mt-2 line-clamp-2 hover:text-blue-600 transition-colors"
          >
            {producto.nombre ?? producto.producto_id}
          </Link>
          <p className="text-xs text-gray-400 mt-0.5">{producto.categoria_producto} · {producto.sede}</p>
        </div>

        <div className="mt-auto">
          <p className="text-lg font-bold text-gray-900 mb-3">
            {new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(
              producto.precio_unitario
            )}
          </p>

          {/* Selector de cantidad + botón agregar */}
          <div className="flex items-center gap-2">
            <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden flex-shrink-0">
              <button
                onClick={() => setCantidad((q) => Math.max(1, q - 1))}
                disabled={sinStock}
                className="px-2 py-1.5 text-white disabled:opacity-40"
                style={{ backgroundColor: "#3B5BDB" }}
              >
                <Minus size={12} />
              </button>
              <span className="px-2 text-sm font-semibold text-gray-900 min-w-[24px] text-center">
                {cantidad}
              </span>
              <button
                onClick={() => setCantidad((q) => Math.min(producto.stock, q + 1))}
                disabled={sinStock || cantidad >= producto.stock}
                className="px-2 py-1.5 text-white disabled:opacity-40"
                style={{ backgroundColor: "#3B5BDB" }}
              >
                <Plus size={12} />
              </button>
            </div>
            <button
              onClick={() => { onAdd(cantidad); setCantidad(1); }}
              disabled={sinStock}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-sm font-medium transition-all disabled:cursor-not-allowed ${
                justAdded
                  ? "bg-green-500 text-white"
                  : inCart
                  ? "bg-blue-50 border border-blue-300 text-blue-700"
                  : sinStock
                  ? "bg-gray-100 text-gray-400"
                  : "text-white"
              }`}
              style={!justAdded && !inCart && !sinStock ? { backgroundColor: "#3B5BDB" } : {}}
            >
              <ShoppingCart size={13} />
              {justAdded ? "¡Agregado!" : inCart ? "En carrito" : "Agregar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
