"use client";

import { useEffect, useState } from "react";
import { Eye, EyeOff, ChevronDown, Users, ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import type { VendedorOut, Cliente } from "@/lib/types";

type View = "list" | "agregar" | "editar";

const SEDES = ["Lima", "Arequipa", "Cusco", "Piura"];


const FORM_INICIAL = {
  nombre: "",
  email: "",
  password: "",
  telefono: "",
  sede: "",
  notas: "",
};

export default function AdminVendedoresPage() {
  const [view, setView] = useState<View>("list");
  const [vendedores, setVendedores] = useState<VendedorOut[]>([]);
  const [carteras, setCarteras] = useState<Record<number, Cliente[]>>({});
  const [expandido, setExpandido] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // form
  const [form, setForm] = useState({ ...FORM_INICIAL });
  const [showPwd, setShowPwd] = useState(false);
  const [vendedorEditando, setVendedorEditando] = useState<VendedorOut | null>(null);

  useEffect(() => {
    api.vendedores.list()
      .then(setVendedores)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function toggleCartera(id: number) {
    if (expandido === id) { setExpandido(null); return; }
    setExpandido(id);
    try {
      const clientes = await api.vendedores.cartera(id);
      setCarteras((prev) => ({ ...prev, [id]: clientes }));
    } catch {}
  }

  function showSuccessMsg(msg: string) {
    setSuccess(msg);
    setTimeout(() => setSuccess(""), 3500);
  }

  function abrirAgregar() {
    setForm({ ...FORM_INICIAL });
    setError("");
    setVendedorEditando(null);
    setView("agregar");
  }

  function abrirEditar(v: VendedorOut) {
    setVendedorEditando(v);
    setForm({ nombre: v.nombre, email: v.email, password: "", telefono: "", sede: "", notas: "" });
    setError("");
    setView("editar");
  }

  function volver() {
    setView("list");
    setVendedorEditando(null);
    setError("");
  }

  async function handleCrear(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const nuevo = await api.vendedores.create({
        nombre: form.nombre,
        email: form.email,
        password: form.password,
        rol: "vendedor",
      });
      setVendedores((prev) => [...prev, nuevo]);
      showSuccessMsg(`Vendedor "${nuevo.nombre}" registrado correctamente.`);
      volver();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear vendedor");
    } finally {
      setSaving(false);
    }
  }

  async function handleEditar(e: React.FormEvent) {
    e.preventDefault();
    if (!vendedorEditando) return;
    setError("");
    setSaving(true);
    try {
      const actualizado = await api.vendedores.update(vendedorEditando.id, {
        nombre: form.nombre,
        email: form.email,
      });
      setVendedores((prev) =>
        prev.map((v) => (v.id === vendedorEditando.id ? { ...v, ...actualizado } : v))
      );
      showSuccessMsg(`Vendedor "${actualizado.nombre}" actualizado correctamente.`);
      volver();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar vendedor");
    } finally {
      setSaving(false);
    }
  }

  async function handleDesactivar() {
    if (!vendedorEditando) return;
    if (!confirm(`¿Desactivar al vendedor "${vendedorEditando.nombre}"?`)) return;
    setSaving(true);
    try {
      await api.vendedores.update(vendedorEditando.id, { activo: false });
      setVendedores((prev) =>
        prev.map((v) => (v.id === vendedorEditando.id ? { ...v, activo: false } : v))
      );
      showSuccessMsg("Vendedor desactivado.");
      volver();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al desactivar");
    } finally {
      setSaving(false);
    }
  }

  const soloVendedores = vendedores.filter((v) => v.rol === "vendedor");

  // ── VISTA: FORMULARIO ────────────────────────────────────────────────────────
  if (view === "agregar" || view === "editar") {
    const esEditar = view === "editar";

    return (
      <div className="p-6 max-w-5xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button onClick={volver} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
            <ArrowLeft size={16} />
            Volver
          </button>
          <span className="text-gray-300">|</span>
          <h1 className="text-xl font-bold text-gray-900">
            {esEditar ? "Editar Vendedor" : "Registrar Nuevo Vendedor"}
          </h1>
        </div>

        <div className="max-w-2xl">
          {/* Formulario principal */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-bold text-gray-900 text-lg mb-1">
              {esEditar ? "Editar Vendedor" : "Registrar Nuevo Vendedor"}
            </h2>
            <p className="text-sm text-gray-400 mb-5">
              {esEditar
                ? "Modifica los datos del vendedor registrado"
                : "Completa todos los campos para crear la cuenta del vendedor"}
            </p>

            <form onSubmit={esEditar ? handleEditar : handleCrear} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre Completo <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  placeholder="Ej: Juan Ramírez"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Correo Electrónico <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="vendedor@ico.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Teléfono <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.telefono}
                  onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                  placeholder="555-1234"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Zona / Sede <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.sede}
                  onChange={(e) => setForm({ ...form, sede: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  <option value="">Seleccionar zona...</option>
                  {SEDES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </div>

              {!esEditar && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contraseña Inicial <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPwd ? "text" : "password"}
                      required
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="Mínimo 8 caracteres"
                      className="w-full px-3 py-2 pr-9 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd(!showPwd)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400"
                    >
                      {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notas adicionales <span className="text-xs text-gray-400">(opcional)</span>
                </label>
                <textarea
                  rows={3}
                  value={form.notas}
                  onChange={(e) => setForm({ ...form, notas: e.target.value })}
                  placeholder="Observaciones, zona de cobertura..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className={`flex gap-3 pt-2 ${esEditar ? "justify-between" : "justify-end"}`}>
                {esEditar && (
                  <button
                    type="button"
                    onClick={handleDesactivar}
                    disabled={saving}
                    className="px-4 py-2 text-sm font-medium border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                  >
                    Desactivar
                  </button>
                )}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={volver}
                    className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-5 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-50"
                    style={{ backgroundColor: "#3B5BDB" }}
                  >
                    {saving ? "Guardando..." : esEditar ? "Guardar Cambios" : "Guardar Vendedor"}
                  </button>
                </div>
              </div>
            </form>
          </div>

        </div>
      </div>
    );
  }

  // ── VISTA: LISTA ──────────────────────────────────────────────────────────────
  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Vendedores</h1>
          <p className="text-gray-500 mt-1 text-sm">{soloVendedores.length} vendedores activos</p>
        </div>
        <button
          onClick={abrirAgregar}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-semibold"
          style={{ backgroundColor: "#3B5BDB" }}
        >
          + Nuevo Vendedor
        </button>
      </div>

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando...</div>
      ) : soloVendedores.length === 0 ? (
        <div className="py-16 text-center text-gray-400 text-sm">No hay vendedores registrados.</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {soloVendedores.map((v) => (
            <div key={v.id}>
              <div className="px-5 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0"
                    style={{ backgroundColor: "#3B5BDB" }}
                  >
                    {v.nombre.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">{v.nombre}</p>
                    <p className="text-xs text-gray-400">{v.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
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
                    onClick={() => abrirEditar(v)}
                    className="text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => toggleCartera(v.id)}
                    className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    <Users size={13} />
                    Clientes
                    <ChevronDown size={13} className={`transition-transform ${expandido === v.id ? "rotate-180" : ""}`} />
                  </button>
                </div>
              </div>

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
                          <div
                            key={c.cliente_id}
                            className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-gray-100"
                          >
                            <div
                              className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                              style={{ backgroundColor: "#4c6ef5" }}
                            >
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
