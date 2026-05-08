"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Cliente, PedidoResumen } from "@/lib/types";

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function initials(nombre: string) {
  const parts = nombre.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

const AVATAR_COLORS = ["#3B5BDB", "#2F9E44", "#E67700", "#C92A2A", "#7048E8", "#0C8599"];
function avatarColor(id: string): string {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) % AVATAR_COLORS.length;
  return AVATAR_COLORS[h];
}

export default function ClientesPage() {
  const router = useRouter();
  const { vendedorId } = useAuth();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [pedidos, setPedidos] = useState<PedidoResumen[]>([]);
  const [loading, setLoading] = useState(true);
  const [buscar, setBuscar] = useState("");
  const [sedeFilter, setSedeFilter] = useState("");
  const [tipoFilter, setTipoFilter] = useState("");
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  useEffect(() => {
    if (!vendedorId) return;
    api.vendedores.cartera(vendedorId)
      .then(setClientes)
      .catch(() => {})
      .finally(() => setLoading(false));
    api.pedidos.list({ limit: 100 })
      .then(setPedidos)
      .catch(() => {});
  }, [vendedorId]);

  const sedes = useMemo(
    () => Array.from(new Set(clientes.map((c) => c.sede_cliente))).sort(),
    [clientes]
  );
  const tipos = useMemo(
    () => Array.from(new Set(clientes.map((c) => c.tipo ?? "").filter(Boolean))).sort(),
    [clientes]
  );

  // Último pedido por cliente
  const ultimoPedido = useMemo(() => {
    const map: Record<string, PedidoResumen> = {};
    for (const p of pedidos) {
      const prev = map[p.cliente_id];
      if (!prev || p.creado_en > prev.creado_en) map[p.cliente_id] = p;
    }
    return map;
  }, [pedidos]);

  const filtered = useMemo(() => {
    const q = buscar.toLowerCase();
    return clientes.filter((c) => {
      const matchQ = !q || c.nombre.toLowerCase().includes(q) || (c.ruc ?? "").includes(q);
      const matchSede = !sedeFilter || c.sede_cliente === sedeFilter;
      const matchTipo = !tipoFilter || (c.tipo ?? "") === tipoFilter;
      return matchQ && matchSede && matchTipo;
    });
  }, [clientes, buscar, sedeFilter, tipoFilter]);

  function irAProductos(clienteId: string) {
    sessionStorage.setItem("ico_cliente_id", clienteId);
    router.push("/productos");
  }

  return (
    <div className="p-6 max-w-6xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-5">Mis Clientes Asignados</h1>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-5 items-center">
        <div className="flex items-center gap-2 flex-1 min-w-[220px]">
          <span className="text-sm text-gray-500 flex-shrink-0">Nombre:</span>
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nombre del cliente..."
              value={buscar}
              onChange={(e) => setBuscar(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 flex-shrink-0">Sede:</span>
          <select
            value={sedeFilter}
            onChange={(e) => setSedeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">Todas las sedes</option>
            {sedes.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 flex-shrink-0">Tipo:</span>
          <select
            value={tipoFilter}
            onChange={(e) => setTipoFilter(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">Todos</option>
            {tipos.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => seleccionado && irAProductos(seleccionado)}
          disabled={!seleccionado}
          className="px-4 py-2 rounded-lg text-sm font-semibold text-white flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ backgroundColor: "#3B5BDB" }}
        >
          {seleccionado
            ? `+ Nuevo Pedido — ${clientes.find(c => c.cliente_id === seleccionado)?.nombre ?? ""}`
            : "+ Nuevo Pedido"}
        </button>
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando clientes...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-700">
              Cartera de Clientes Asignados ({filtered.length})
            </p>
          </div>
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-gray-400">No se encontraron clientes.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-5 py-3 font-medium text-gray-400">Nombre del Negocio</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-400">Sede</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-400">Teléfono</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-400">Último Pedido</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-400">Monto</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-400">Tipo</th>
                  <th className="text-center px-4 py-3 font-medium text-gray-400">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((c) => {
                  const ultimo = ultimoPedido[c.cliente_id];
                  const color = avatarColor(c.cliente_id);
                  const isSelected = seleccionado === c.cliente_id;
                  return (
                    <tr
                      key={c.cliente_id}
                      onClick={() => setSeleccionado(isSelected ? null : c.cliente_id)}
                      className="cursor-pointer border-l-2 transition-colors"
                      style={{
                        backgroundColor: isSelected ? "#EEF2FF" : undefined,
                        borderLeftColor: isSelected ? "#3B5BDB" : "transparent",
                      }}
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-9 h-9 rounded-full flex items-center justify-center font-semibold text-white text-xs flex-shrink-0"
                            style={{ backgroundColor: color }}
                          >
                            {initials(c.nombre)}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{c.nombre}</p>
                            <p className="text-xs text-gray-400">{c.rubro_cliente}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                          {c.sede_cliente}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{c.telefono ?? "—"}</td>
                      <td className="px-4 py-3 text-gray-500">
                        {ultimo ? formatDate(ultimo.creado_en) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900">
                        {ultimo ? formatCurrency(ultimo.total) : "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-500">{c.tipo ?? "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); irAProductos(c.cliente_id); }}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white"
                            style={{ backgroundColor: "#3B5BDB" }}
                          >
                            Pedido
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(
                                `/historial?cliente=${c.cliente_id}&nombre=${encodeURIComponent(c.nombre)}`
                              );
                            }}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 text-gray-600 hover:bg-gray-50"
                          >
                            Historial
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
