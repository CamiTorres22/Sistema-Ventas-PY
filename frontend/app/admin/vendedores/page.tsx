"use client";

import { useEffect, useState } from "react";
import { UserPlus, Eye, EyeOff, ChevronDown, Users } from "lucide-react";
import { api } from "@/lib/api";
import type { VendedorOut, Cliente } from "@/lib/types";

export default function AdminVendedoresPage() {
  const [vendedores, setVendedores] = useState<VendedorOut[]>([]);
  const [carteras, setCarteras] = useState<Record<number, Cliente[]>>({});
  const [expandido, setExpandido] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nombre: "", email: "", password: "", rol: "vendedor" });
  const [showPwd, setShowPwd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    api.vendedores.list()
      .then(setVendedores)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function toggleCartera(id: number) {
    if (expandido === id) {
      setExpandido(null);
      return;
    }
    setExpandido(id);
    // Siempre recarga para mostrar datos actualizados
    try {
      const clientes = await api.vendedores.cartera(id);
      setCarteras((prev) => ({ ...prev, [id]: clientes }));
    } catch {}
  }

  async function handleCrear(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const nuevo = await api.vendedores.create(form);
      setVendedores((prev) => [...prev, nuevo]);
      setSuccess(`Usuario "${nuevo.nombre}" creado correctamente.`);
      setForm({ nombre: "", email: "", password: "", rol: "vendedor" });
      setShowForm(false);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear usuario");
    } finally {
      setSaving(false);
    }
  }

  const soloVendedores = vendedores.filter((v) => v.rol === "vendedor");

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Vendedores</h1>
          <p className="text-gray-500 mt-1">{soloVendedores.length} vendedores activos</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium"
          style={{ backgroundColor: "#3B5BDB" }}
        >
          <UserPlus size={16} />
          Nuevo usuario
        </button>
      </div>

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {/* Formulario nuevo usuario */}
      {showForm && (
        <div className="mb-6 bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 mb-4">Crear nuevo usuario</h2>
          <form onSubmit={handleCrear} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nombre completo</label>
              <input type="text" required value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ej: María García" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Correo electrónico</label>
              <input type="email" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="correo@ico.pe" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Contraseña</label>
              <div className="relative">
                <input type={showPwd ? "text" : "password"} required value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full px-3 py-2 pr-9 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Mínimo 8 caracteres" />
                <button type="button" onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400">
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Rol</label>
              <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
                <option value="vendedor">Vendedor</option>
                <option value="admin">Administrador</option>
              </select>
            </div>
            {error && (
              <div className="sm:col-span-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <p className="text-xs text-red-600">{error}</p>
              </div>
            )}
            <div className="sm:col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => { setShowForm(false); setError(""); }}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
                Cancelar
              </button>
              <button type="submit" disabled={saving}
                className="px-4 py-2 text-sm text-white rounded-lg disabled:opacity-50"
                style={{ backgroundColor: "#3B5BDB" }}>
                {saving ? "Guardando..." : "Crear usuario"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Lista de vendedores */}
      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando...</div>
      ) : soloVendedores.length === 0 ? (
        <div className="py-16 text-center text-gray-400 text-sm">No hay vendedores registrados.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {soloVendedores.map((v) => (
            <div key={v.id}>
              {/* Fila principal */}
              <div className="px-5 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0"
                    style={{ backgroundColor: "#3B5BDB" }}>
                    {v.nombre.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">{v.nombre}</p>
                    <p className="text-xs text-gray-400">{v.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs text-gray-400">ID vendedor</p>
                    <p className="text-sm font-bold text-gray-700">#{v.id}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    v.activo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"
                  }`}>
                    {v.activo ? "Activo" : "Inactivo"}
                  </span>
                  <button
                    onClick={() => toggleCartera(v.id)}
                    className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    <Users size={13} />
                    Clientes asignados
                    <ChevronDown size={13} className={`transition-transform ${expandido === v.id ? "rotate-180" : ""}`} />
                  </button>
                </div>
              </div>

              {/* Panel expandible de cartera */}
              {expandido === v.id && (
                <div className="px-5 pb-4 bg-gray-50 border-t border-gray-100">
                  {!carteras[v.id] ? (
                    <p className="py-4 text-center text-xs text-gray-400">Cargando clientes...</p>
                  ) : carteras[v.id].length === 0 ? (
                    <p className="py-4 text-center text-xs text-gray-400">Sin clientes asignados.</p>
                  ) : (
                    <>
                      <p className="text-xs font-medium text-gray-500 pt-3 pb-2">
                        {carteras[v.id].length} clientes asignados
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
                        {carteras[v.id].map((c) => (
                          <div key={c.cliente_id}
                            className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-gray-100">
                            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                              style={{ backgroundColor: "#4c6ef5" }}>
                              {c.nombre.charAt(0)}
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-gray-900 truncate">{c.nombre}</p>
                              <p className="text-xs text-gray-400">{c.sede_cliente} · {c.rubro_cliente}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
