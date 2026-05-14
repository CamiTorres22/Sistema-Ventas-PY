"use client";

import { useEffect, useState, useMemo } from "react";
import { Search, ArrowLeft, UserCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, VendedorOut } from "@/lib/types";

type View = "list" | "agregar" | "editar";

const SEDES = ["Lima", "Arequipa", "Piura", "Cusco"];
const TIPOS = ["Mayorista", "Minorista", "Corporativo"];
const RUBROS = [
  "Restaurante", "Hotel", "Bar", "Cafetería", "Bodega",
  "Supermercado", "Catering", "Panadería", "Otro",
];

function initials(nombre: string) {
  const parts = nombre.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

const AVATAR_COLORS = ["#3B5BDB", "#2F9E44", "#E67700", "#C92A2A", "#7048E8", "#0C8599"];
function avatarColor(id: string) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) % AVATAR_COLORS.length;
  return AVATAR_COLORS[h];
}

function siguienteClienteId(clientes: Cliente[]): string {
  let max = 0;
  for (const c of clientes) {
    const match = c.cliente_id.match(/\d+/);
    if (match) {
      const num = parseInt(match[0], 10);
      if (num > max) max = num;
    }
  }
  return `CLI_${max + 1}`;
}

const FORM_INICIAL = {
  cliente_id: "",
  nombre: "",
  ruc: "",
  telefono: "",
  rubro_cliente: "Restaurante",
  sede_cliente: "Lima",
  tipo: "Mayorista",
  activo: true,
};

export default function AdminClientesPage() {
  const [view, setView] = useState<View>("list");
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [vendedores, setVendedores] = useState<VendedorOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // list filters
  const [buscar, setBuscar] = useState("");
  const [sedeFilter, setSedeFilter] = useState("Todas");
  const [pagina, setPagina] = useState(0);
  const POR_PAGINA = 50;

  // vendedor seleccionado en el panel de edición
  const [vendedorEditId, setVendedorEditId] = useState<string>("");
  const [asignando, setAsignando] = useState(false);
  const [successAsignar, setSuccessAsignar] = useState("");

  // form
  const [form, setForm] = useState({ ...FORM_INICIAL });
  const [clienteEditando, setClienteEditando] = useState<Cliente | null>(null);

  useEffect(() => {
    async function load() {
      const [cli, vend] = await Promise.all([
        api.clientes.list({ limit: 5000 }),
        api.vendedores.list(),
      ]);
      setClientes(cli);
      setVendedores(vend.filter((v) => v.rol === "vendedor"));
      setLoading(false);
    }
    load().catch(() => setLoading(false));
  }, []);

  const vendedorMap = useMemo(() => {
    const m: Record<number, string> = {};
    for (const v of vendedores) m[v.id] = v.nombre;
    return m;
  }, [vendedores]);

  const filtered = useMemo(() => {
    const q = buscar.toLowerCase();
    return clientes.filter((c) => {
      const matchQ = !q || c.nombre.toLowerCase().includes(q) || (c.ruc ?? "").includes(q);
      const matchSede = sedeFilter === "Todas" || c.sede_cliente === sedeFilter;
      return matchQ && matchSede;
    });
  }, [clientes, buscar, sedeFilter]);

  const totalPaginas = Math.ceil(filtered.length / POR_PAGINA);
  const paginaActual = Math.min(pagina, Math.max(0, totalPaginas - 1));
  const paginados = filtered.slice(paginaActual * POR_PAGINA, (paginaActual + 1) * POR_PAGINA);

  async function handleAsignar() {
    if (!clienteEditando || !vendedorEditId) return;
    setAsignando(true);
    try {
      await api.clientes.asignar(clienteEditando.cliente_id, Number(vendedorEditId));
      const vid = Number(vendedorEditId);
      setClientes((prev) =>
        prev.map((c) =>
          c.cliente_id === clienteEditando.cliente_id ? { ...c, vendedor_id: vid } : c
        )
      );
      setClienteEditando((prev) => prev ? { ...prev, vendedor_id: vid } : prev);
      setSuccessAsignar("Vendedor asignado correctamente.");
      setTimeout(() => setSuccessAsignar(""), 3000);
    } catch {
      setSuccessAsignar("");
    } finally {
      setAsignando(false);
    }
  }

  function showSuccess(msg: string) {
    setSuccess(msg);
    setTimeout(() => setSuccess(""), 3000);
  }

  function abrirAgregar() {
    setForm({ ...FORM_INICIAL, cliente_id: siguienteClienteId(clientes) });
    setError("");
    setView("agregar");
  }

  function abrirEditar(c: Cliente) {
    setClienteEditando(c);
    setVendedorEditId(c.vendedor_id != null ? String(c.vendedor_id) : "");
    setSuccessAsignar("");
    setForm({
      cliente_id: c.cliente_id,
      nombre: c.nombre,
      ruc: c.ruc ?? "",
      telefono: c.telefono ?? "",
      rubro_cliente: c.rubro_cliente,
      sede_cliente: c.sede_cliente,
      tipo: c.tipo ?? "Mayorista",
      activo: c.activo,
    });
    setError("");
    setView("editar");
  }

  function volver() {
    setView("list");
    setClienteEditando(null);
    setError("");
  }

  async function handleAgregar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const nuevo = await api.clientes.create({
        cliente_id: form.cliente_id,
        nombre: form.nombre,
        ruc: form.ruc || undefined,
        telefono: form.telefono || undefined,
        rubro_cliente: form.rubro_cliente,
        sede_cliente: form.sede_cliente,
        tipo: form.tipo || undefined,
      });
      setClientes((prev) => [nuevo, ...prev]);
      showSuccess(`Cliente "${nuevo.nombre}" creado correctamente.`);
      volver();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear cliente");
    } finally {
      setSaving(false);
    }
  }

  async function handleEditar(e: React.FormEvent) {
    e.preventDefault();
    if (!clienteEditando) return;
    setError("");
    setSaving(true);
    try {
      const actualizado = await api.clientes.update(clienteEditando.cliente_id, {
        nombre: form.nombre,
        ruc: form.ruc || undefined,
        telefono: form.telefono || undefined,
        rubro_cliente: form.rubro_cliente,
        sede_cliente: form.sede_cliente,
        tipo: form.tipo || undefined,
        activo: form.activo,
      });
      setClientes((prev) =>
        prev.map((c) => (c.cliente_id === clienteEditando.cliente_id ? { ...c, ...actualizado } : c))
      );
      showSuccess(`Cliente "${actualizado.nombre}" actualizado correctamente.`);
      volver();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al actualizar cliente");
    } finally {
      setSaving(false);
    }
  }

  async function handleEliminar() {
    if (!clienteEditando) return;
    if (!confirm(`¿Eliminar al cliente "${clienteEditando.nombre}"? Esta acción lo marcará como inactivo.`)) return;
    setSaving(true);
    try {
      await api.clientes.update(clienteEditando.cliente_id, { activo: false });
      setClientes((prev) =>
        prev.map((c) =>
          c.cliente_id === clienteEditando.cliente_id ? { ...c, activo: false } : c
        )
      );
      showSuccess("Cliente eliminado correctamente.");
      volver();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al eliminar cliente");
    } finally {
      setSaving(false);
    }
  }

  // ── VISTA: FORMULARIO AGREGAR / EDITAR ─────────────────────────────────────
  if (view === "agregar" || view === "editar") {
    const esEditar = view === "editar";
    const vendedorAsignado = clienteEditando?.vendedor_id
      ? vendedorMap[clienteEditando.vendedor_id]
      : null;

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
            {esEditar ? "Editar Cliente" : "Agregar Cliente"}
          </h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Formulario principal */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-bold text-gray-900 text-lg mb-1">
              {esEditar ? "Editar Información del Cliente" : "Agregar Nuevo Cliente"}
            </h2>
            <p className="text-sm text-gray-400 mb-5">
              {esEditar
                ? "Modifica los datos del cliente registrado en el sistema"
                : "Complete los datos del nuevo cliente para registrarlo en el sistema."}
            </p>

            <form onSubmit={esEditar ? handleEditar : handleAgregar} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Negocio <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ej: Supermercado El Sol"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  RUC / NIT
                </label>
                <input
                  type="text"
                  value={form.ruc}
                  onChange={(e) => setForm({ ...form, ruc: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="1234567890"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Teléfono
                </label>
                <input
                  type="text"
                  value={form.telefono}
                  onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="555-1234"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sede <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    value={form.sede_cliente}
                    onChange={(e) => setForm({ ...form, sede_cliente: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    {SEDES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Cliente <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    value={form.tipo}
                    onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    {TIPOS.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rubro <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  value={form.rubro_cliente}
                  onChange={(e) => setForm({ ...form, rubro_cliente: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  {RUBROS.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>

              {esEditar && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Estado</label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setForm({ ...form, activo: true })}
                      className="px-5 py-2 rounded-full text-sm font-medium transition-colors"
                      style={form.activo
                        ? { backgroundColor: "#2F9E44", color: "white" }
                        : { backgroundColor: "#F1F3F5", color: "#495057" }}
                    >
                      Activo
                    </button>
                    <button
                      type="button"
                      onClick={() => setForm({ ...form, activo: false })}
                      className="px-5 py-2 rounded-full text-sm font-medium transition-colors"
                      style={!form.activo
                        ? { backgroundColor: "#868E96", color: "white" }
                        : { backgroundColor: "#F1F3F5", color: "#495057" }}
                    >
                      Inactivo
                    </button>
                  </div>
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className={`flex gap-3 pt-2 ${esEditar ? "justify-between" : "justify-end"}`}>
                {esEditar && (
                  <button
                    type="button"
                    onClick={handleEliminar}
                    disabled={saving}
                    className="px-4 py-2 text-sm font-medium border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                  >
                    Eliminar Cliente
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
                    {saving ? "Guardando..." : esEditar ? "Guardar Cambios" : "Agregar Cliente"}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Panel lateral */}
          <div className="space-y-4">
            {/* Resumen del cliente (solo editar) */}
            {esEditar && clienteEditando && (
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-800 mb-4">Resumen del Cliente</h3>
                <div className="flex flex-col items-center text-center mb-4">
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-lg mb-2"
                    style={{ backgroundColor: avatarColor(clienteEditando.cliente_id) }}
                  >
                    {initials(clienteEditando.nombre)}
                  </div>
                  <p className="font-semibold text-gray-900">{clienteEditando.nombre}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {clienteEditando.tipo} | {clienteEditando.sede_cliente}
                  </p>
                </div>
              </div>
            )}

            {/* Vendedor asignado (solo editar) */}
            {esEditar && (
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-800 mb-3">Vendedor Asignado</h3>

                {/* Vendedor actual */}
                {vendedorAsignado ? (
                  <div className="flex items-center gap-3 mb-4">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0"
                      style={{ backgroundColor: "#3B5BDB" }}
                    >
                      {vendedorAsignado.charAt(0)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{vendedorAsignado}</p>
                      <p className="text-xs text-gray-400">Asignado actualmente</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-orange-500 font-medium mb-4">Sin asignar</p>
                )}

                {/* Select para cambiar */}
                <select
                  value={vendedorEditId}
                  onChange={(e) => setVendedorEditId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white mb-3"
                >
                  <option value="">— Sin asignar —</option>
                  {vendedores.map((v) => (
                    <option key={v.id} value={v.id}>{v.nombre}</option>
                  ))}
                </select>

                {successAsignar && (
                  <p className="text-xs text-green-600 mb-2">{successAsignar}</p>
                )}

                <button
                  type="button"
                  onClick={handleAsignar}
                  disabled={asignando || !vendedorEditId}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-white rounded-lg disabled:opacity-40"
                  style={{ backgroundColor: "#3B5BDB" }}
                >
                  <UserCheck size={15} />
                  {asignando ? "Asignando..." : "Confirmar Asignación"}
                </button>
              </div>
            )}

          </div>
        </div>
      </div>
    );
  }

  // ── VISTA: LISTA ──────────────────────────────────────────────────────────────
  return (
    <div className="p-6 max-w-6xl">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Clientes</h1>
          <p className="text-gray-500 text-sm mt-1">
            Clientes Registrados ({clientes.length})
          </p>
        </div>
        <button
          onClick={abrirAgregar}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-semibold"
          style={{ backgroundColor: "#3B5BDB" }}
        >
          + Agregar Cliente
        </button>
      </div>

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {/* Búsqueda */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por nombre..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(0); }}
          className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        />
      </div>

      {/* Filtros por sede */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <span className="text-sm text-gray-500 font-medium">Sede:</span>
        {["Todas", ...SEDES].map((s) => (
          <button
            key={s}
            onClick={() => { setSedeFilter(s); setPagina(0); }}
            className="px-4 py-1.5 rounded-full text-sm font-medium border transition-colors"
            style={sedeFilter === s
              ? { backgroundColor: "#3B5BDB", color: "white", borderColor: "#3B5BDB" }
              : { backgroundColor: "white", color: "#495057", borderColor: "#dee2e6" }}
          >
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-5 py-3 font-medium text-gray-500">Nombre del Negocio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">RUC/NIT</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Sede</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Vendedor Asignado</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Tipo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Estado</th>
                <th className="text-center px-4 py-3 font-medium text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {paginados.map((c) => {
                const nombreVendedor = c.vendedor_id ? vendedorMap[c.vendedor_id] : null;

                return (
                  <tr key={c.cliente_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0"
                          style={{ backgroundColor: avatarColor(c.cliente_id) }}
                        >
                          {initials(c.nombre)}
                        </div>
                        <p className="font-medium text-gray-900">{c.nombre}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{c.ruc ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{c.sede_cliente}</td>
                    <td className="px-4 py-3">
                      {nombreVendedor ? (
                        <span className="text-gray-700">{nombreVendedor}</span>
                      ) : (
                        <span className="text-orange-500 text-xs font-medium">Sin asignar</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{c.tipo ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                        c.activo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                      }`}>
                        {c.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => abrirEditar(c)}
                        className="px-4 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {totalPaginas > 1 && (
            <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>
                Mostrando {paginaActual * POR_PAGINA + 1}–
                {Math.min((paginaActual + 1) * POR_PAGINA, filtered.length)} de {filtered.length}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPagina((p) => Math.max(0, p - 1))}
                  disabled={paginaActual === 0}
                  className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
                >
                  Anterior
                </button>
                <span>{paginaActual + 1} / {totalPaginas}</span>
                <button
                  onClick={() => setPagina((p) => Math.min(totalPaginas - 1, p + 1))}
                  disabled={paginaActual === totalPaginas - 1}
                  className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
