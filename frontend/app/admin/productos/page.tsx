"use client";

import { useEffect, useState } from "react";
import { Search, Package, ArrowLeft, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Producto } from "@/lib/types";

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
}

const CATEGORIAS = ["Todas", "Abarrotes", "Bebidas", "Carnes", "Congelados", "Frutas", "Lácteos", "Limpieza", "Panadería", "Snacks", "Verduras"];

type Tab = "lista" | "agregar" | "editar";

// ── Modal Agregar Stock ────────────────────────────────────────────────────────
function ModalStock({
  producto,
  onClose,
  onSaved,
}: {
  producto: Producto;
  onClose: () => void;
  onSaved: (updated: Producto) => void;
}) {
  const [cantidad, setCantidad] = useState(0);
  const [motivo, setMotivo] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleConfirmar() {
    if (cantidad <= 0) { setError("La cantidad debe ser mayor a 0."); return; }
    setSaving(true);
    try {
      const updated = await api.productos.addStock(producto.producto_id, cantidad);
      onSaved(updated);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al actualizar stock.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-bold text-gray-900">Agregar Stock</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>
        <p className="text-sm text-gray-400 mb-5">Actualiza el inventario disponible del producto</p>

        {/* Info producto */}
        <div className="bg-gray-50 rounded-xl px-4 py-3 mb-5 flex items-center gap-3">
          <Package size={18} className="text-gray-400 flex-shrink-0" />
          <div>
            <p className="font-semibold text-gray-900 text-sm">{producto.nombre}</p>
            <p className="text-xs text-gray-400">{producto.producto_id} · Stock actual: {producto.stock} unidades</p>
          </div>
        </div>

        {/* Cantidad */}
        <p className="text-sm font-medium text-gray-700 mb-2">Cantidad a agregar *</p>
        <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden mb-4">
          <button
            onClick={() => setCantidad((q) => Math.max(0, q - 1))}
            className="px-5 py-3 text-xl text-gray-500 hover:bg-gray-50 font-bold"
          >
            −
          </button>
          <input
            type="number"
            min={0}
            value={cantidad}
            onChange={(e) => setCantidad(Math.max(0, Number(e.target.value)))}
            className="flex-1 text-center text-2xl font-bold text-gray-900 focus:outline-none py-3 bg-white"
          />
          <button
            onClick={() => setCantidad((q) => q + 1)}
            className="px-5 py-3 text-xl text-white font-bold"
            style={{ backgroundColor: "#3B5BDB" }}
          >
            +
          </button>
        </div>

        {/* Motivo */}
        <p className="text-sm font-medium text-gray-700 mb-2">Motivo del ajuste</p>
        <input
          type="text"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          placeholder="Ej: Reposición semanal, Inventario inicial..."
          className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
        />

        {/* Preview */}
        <div className="bg-blue-50 rounded-xl px-4 py-2.5 mb-4 text-sm text-blue-700">
          Stock resultante: {producto.stock} + {cantidad} = <strong>{producto.stock + cantidad} unidades</strong>
        </div>

        {error && <p className="text-xs text-red-500 mb-3">{error}</p>}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirmar}
            disabled={saving}
            className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50"
            style={{ backgroundColor: "#3B5BDB" }}
          >
            {saving ? "Guardando..." : "Confirmar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Formulario Agregar / Editar ───────────────────────────────────────────────
function FormProducto({
  inicial,
  onBack,
  onSaved,
}: {
  inicial?: Producto;
  onBack: () => void;
  onSaved: (p: Producto) => void;
}) {
  const esEditar = !!inicial;
  const [form, setForm] = useState({
    producto_id: inicial?.producto_id ?? "",
    nombre: inicial?.nombre ?? "",
    categoria_producto: inicial?.categoria_producto ?? "Lácteos",
    precio_unitario: inicial?.precio_unitario?.toString() ?? "",
    costo_unitario: inicial?.costo_unitario?.toString() ?? "",
    stock: inicial?.stock?.toString() ?? "0",
    sede: inicial?.sede ?? "Lima",
    fecha_min_caducidad: inicial?.fecha_min_caducidad ?? "",
    descripcion: inicial?.descripcion ?? "",
    activo: inicial?.activo ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(k: string, v: string | boolean) {
    setForm((prev) => ({ ...prev, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!form.producto_id || !form.nombre || !form.precio_unitario || !form.costo_unitario) {
      setError("Completa los campos obligatorios.");
      return;
    }
    setSaving(true);
    try {
      let result: Producto;
      if (esEditar) {
        result = await api.productos.update(form.producto_id, {
          nombre: form.nombre,
          categoria_producto: form.categoria_producto,
          precio_unitario: Number(form.precio_unitario),
          costo_unitario: Number(form.costo_unitario),
          fecha_min_caducidad: form.fecha_min_caducidad || undefined,
          descripcion: form.descripcion || undefined,
          activo: form.activo,
        });
      } else {
        result = await api.productos.create({
          producto_id: form.producto_id,
          nombre: form.nombre,
          categoria_producto: form.categoria_producto,
          precio_unitario: Number(form.precio_unitario),
          costo_unitario: Number(form.costo_unitario),
          stock: Number(form.stock),
          sede: form.sede,
          fecha_min_caducidad: form.fecha_min_caducidad || undefined,
          descripcion: form.descripcion || undefined,
        });
      }
      onSaved(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al guardar.");
    } finally {
      setSaving(false);
    }
  }

  const inputClass = "w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-6 transition-colors">
        <ArrowLeft size={15} /> Volver a la lista
      </button>

      <h2 className="text-xl font-bold text-gray-900 mb-1">
        {esEditar ? "Editar Producto" : "Agregar Producto"}
      </h2>
      <p className="text-sm text-gray-400 mb-6">
        {esEditar
          ? "Los cambios se reflejarán inmediatamente en el catálogo visible para los vendedores"
          : "Complete los datos del nuevo producto para agregarlo al catálogo."}
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Formulario */}
        <form onSubmit={handleSubmit} className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h3 className="font-semibold text-gray-900 mb-2">Información del Producto</h3>

          <div>
            <label className={labelClass}>Nombre del Producto *</label>
            <input className={inputClass} value={form.nombre} onChange={(e) => set("nombre", e.target.value)} placeholder="Ej: Leche Evaporada Gloria 390g" required />
          </div>

          <div>
            <label className={labelClass}>Código / SKU *</label>
            <input className={inputClass} value={form.producto_id} onChange={(e) => set("producto_id", e.target.value)} placeholder="Ej: LAC-001" required disabled={esEditar} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Precio Unitario (S/.) *</label>
              <input type="number" step="0.01" min="0.01" className={inputClass} value={form.precio_unitario} onChange={(e) => set("precio_unitario", e.target.value)} placeholder="3.50" required />
            </div>
            <div>
              <label className={labelClass}>Costo Unitario (S/.)</label>
              <input type="number" step="0.01" min="0.01" className={inputClass} value={form.costo_unitario} onChange={(e) => set("costo_unitario", e.target.value)} placeholder="2.80" required />
            </div>
          </div>

          {!esEditar && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Stock inicial</label>
                <input type="number" min="0" className={inputClass} value={form.stock} onChange={(e) => set("stock", e.target.value)} placeholder="0" />
              </div>
              <div>
                <label className={labelClass}>Sede</label>
                <input className={inputClass} value={form.sede} onChange={(e) => set("sede", e.target.value)} placeholder="Lima" />
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 items-end">
            <div>
              <label className={labelClass}>Categoría *</label>
              <select className={inputClass + " bg-white"} value={form.categoria_producto} onChange={(e) => set("categoria_producto", e.target.value)}>
                {CATEGORIAS.filter((c) => c !== "Todas").map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Estado *</label>
              <div className="flex gap-2">
                <button type="button" onClick={() => set("activo", true)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${form.activo ? "text-white" : "border border-gray-200 text-gray-500"}`}
                  style={form.activo ? { backgroundColor: "#2f9e44" } : {}}>
                  Activo
                </button>
                <button type="button" onClick={() => set("activo", false)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${!form.activo ? "bg-gray-200 text-gray-700" : "border border-gray-200 text-gray-500"}`}>
                  Inactivo
                </button>
              </div>
            </div>
          </div>

          <div>
            <label className={labelClass}>Fecha de Vencimiento</label>
            <input type="date" className={inputClass} value={form.fecha_min_caducidad} onChange={(e) => set("fecha_min_caducidad", e.target.value)} />
          </div>

          <div>
            <label className={labelClass}>Descripción del Producto</label>
            <textarea rows={3} className={inputClass + " resize-none"} value={form.descripcion} onChange={(e) => set("descripcion", e.target.value)} placeholder="Descripción del producto..." />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onBack} className="px-5 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white disabled:opacity-50" style={{ backgroundColor: "#3B5BDB" }}>
              {saving ? "Guardando..." : esEditar ? "Guardar Cambios" : "Agregar Producto"}
            </button>
            {esEditar && (
              <button type="button" onClick={async () => {
                if (!confirm("¿Desactivar este producto?")) return;
                try {
                  const r = await api.productos.update(form.producto_id, { activo: false });
                  onSaved(r); onBack();
                } catch {}
              }} className="ml-auto px-5 py-2.5 border border-red-300 rounded-lg text-sm font-semibold text-red-500 hover:bg-red-50">
                Eliminar Producto
              </button>
            )}
          </div>
        </form>

        {/* Vista previa */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Vista Previa</h3>
            <div className="flex justify-center mb-4">
              <div className="w-28 h-28 bg-gray-100 rounded-xl flex items-center justify-center">
                <Package size={40} className="text-gray-300" />
              </div>
            </div>
            <p className="font-semibold text-gray-900 text-sm text-center mb-0.5">{form.nombre || "Nombre del producto"}</p>
            <p className="text-xs text-gray-400 text-center">
              {form.producto_id || "SKU"} · {form.categoria_producto} · {form.precio_unitario ? `S/ ${Number(form.precio_unitario).toFixed(2)}` : "S/ 0.00"}
            </p>
          </div>

          {esEditar && inicial && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Stock Actual</h3>
              <p className="text-3xl font-bold mb-1" style={{ color: "#3B5BDB" }}>{inicial.stock}</p>
              <p className="text-xs text-gray-400">unidades disponibles</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────
export default function AdminProductosPage() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(true);
  const [buscar, setBuscar] = useState("");
  const [categoria, setCategoria] = useState("Todas");
  const [tab, setTab] = useState<Tab>("lista");
  const [editando, setEditando] = useState<Producto | null>(null);
  const [stockModal, setStockModal] = useState<Producto | null>(null);

  useEffect(() => {
    api.productos.list({ limit: 2000 })
      .then(setProductos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = productos.filter((p) => {
    const q = buscar.toLowerCase();
    const matchQ = !q || p.nombre.toLowerCase().includes(q) || p.producto_id.toLowerCase().includes(q);
    const matchCat = categoria === "Todas" || p.categoria_producto === categoria;
    return matchQ && matchCat;
  });

  function handleSaved(p: Producto) {
    setProductos((prev) => {
      const idx = prev.findIndex((x) => x.producto_id === p.producto_id);
      return idx >= 0 ? prev.map((x) => (x.producto_id === p.producto_id ? p : x)) : [p, ...prev];
    });
    setTab("lista");
    setEditando(null);
  }

  // Formulario agregar/editar
  if (tab === "agregar" || (tab === "editar" && editando)) {
    return (
      <div className="p-6 max-w-5xl">
        <FormProducto
          inicial={tab === "editar" ? editando! : undefined}
          onBack={() => { setTab("lista"); setEditando(null); }}
          onSaved={handleSaved}
        />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Productos</h1>
          <p className="text-gray-500 mt-1">{productos.length} productos en catálogo</p>
        </div>
        <button
          onClick={() => setTab("agregar")}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-semibold"
          style={{ backgroundColor: "#2f9e44" }}
        >
          + Agregar Producto
        </button>
      </div>

      {/* Búsqueda */}
      <div className="relative mb-4">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar producto..."
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        />
      </div>

      {/* Pills de categoría */}
      <div className="flex flex-wrap gap-2 mb-5">
        {CATEGORIAS.map((c) => (
          <button
            key={c}
            onClick={() => setCategoria(c)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all border ${
              categoria === c
                ? "text-white border-transparent"
                : "bg-white border-gray-200 text-gray-600 hover:border-gray-300"
            }`}
            style={categoria === c ? { backgroundColor: "#2f9e44" } : {}}
          >
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700">Productos en Catálogo ({filtered.length})</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-5 py-3 font-medium text-gray-500">Producto</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Categoría</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500">Precio</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500">Stock</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Vencimiento</th>
                <th className="text-center px-4 py-3 font-medium text-gray-500">Estado</th>
                <th className="text-center px-4 py-3 font-medium text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((p) => {
                const sinStock = p.stock <= 0;
                const stockBajo = p.stock > 0 && p.stock < 10;
                const esBajaRot = p.baja_rotacion === 1;
                const diasVence = p.fecha_min_caducidad
                  ? Math.ceil((new Date(p.fecha_min_caducidad).getTime() - Date.now()) / 86400000)
                  : null;
                const proxVencer = diasVence !== null && diasVence <= 30;

                return (
                  <tr key={p.producto_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900 line-clamp-1">{p.nombre}</p>
                      <div className="flex gap-1 mt-0.5 flex-wrap">
                        {proxVencer && (
                          <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-red-100 text-red-600">PROX. VENCER</span>
                        )}
                        {esBajaRot && (
                          <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-orange-100 text-orange-600">BAJA ROT.</span>
                        )}
                        {!esBajaRot && !proxVencer && p.rotacion_diaria === 0 && (
                          <span className="text-xs px-1.5 py-0.5 rounded font-medium bg-blue-100 text-blue-600">NUEVO</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{p.categoria_producto}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      {formatCurrency(p.precio_unitario)}
                    </td>
                    <td className={`px-4 py-3 text-right font-semibold ${sinStock ? "text-red-500" : stockBajo ? "text-orange-500" : "text-gray-900"}`}>
                      {p.stock} uds
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {p.fecha_min_caducidad ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${p.activo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {p.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => { setEditando(p); setTab("editar"); }}
                          className="px-3 py-1 rounded-lg border border-gray-200 text-xs text-gray-600 hover:bg-gray-50 font-medium"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => setStockModal(p)}
                          className="px-3 py-1 rounded-lg text-xs font-medium text-white"
                          style={{ backgroundColor: "#3B5BDB" }}
                        >
                          + Stock
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal stock */}
      {stockModal && (
        <ModalStock
          producto={stockModal}
          onClose={() => setStockModal(null)}
          onSaved={(updated) => {
            setProductos((prev) => prev.map((p) => (p.producto_id === updated.producto_id ? updated : p)));
            setStockModal(null);
          }}
        />
      )}
    </div>
  );
}
