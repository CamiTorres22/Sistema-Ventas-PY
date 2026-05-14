"use client";

import { useEffect, useState, Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { PedidoResumen } from "@/lib/types";

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

const ESTADO_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  pendiente:   { bg: "#FFF3BF", text: "#E67700", label: "Pendiente" },
  confirmado:  { bg: "#DBE4FF", text: "#3B5BDB", label: "En proceso" },
  en_proceso:  { bg: "#DBE4FF", text: "#3B5BDB", label: "En proceso" },
  entregado:   { bg: "#D3F9D8", text: "#2F9E44", label: "Completado" },
  completado:  { bg: "#D3F9D8", text: "#2F9E44", label: "Completado" },
  cancelado:   { bg: "#FFE3E3", text: "#C92A2A", label: "Cancelado" },
};

const PERIODOS = [
  { label: "Último mes",       days: 30 },
  { label: "Últimos 3 meses",  days: 90 },
  { label: "Último año",       days: 365 },
  { label: "Todo el historial", days: 0 },
];

const POR_PAGINA = 7;

function exportCSV(pedidos: PedidoResumen[]) {
  const headers = ["N° Pedido", "Cliente", "Fecha", "Productos", "Total", "Estado"];
  const rows = pedidos.map((p) => [
    p.numero,
    `"${p.nombre_cliente}"`,
    formatDate(p.creado_en),
    `${p.n_productos} productos`,
    p.total.toFixed(2),
    ESTADO_CONFIG[p.estado]?.label ?? p.estado,
  ]);
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "historial_pedidos.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function buildPageNumbers(total: number, current: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i);
  const pages: (number | "...")[] = [0];
  if (current > 2) pages.push("...");
  for (let i = Math.max(1, current - 1); i <= Math.min(total - 2, current + 1); i++) pages.push(i);
  if (current < total - 3) pages.push("...");
  pages.push(total - 1);
  return pages;
}

function HistorialContent() {
  const searchParams = useSearchParams();
  const clienteIdParam    = searchParams.get("cliente");
  const clienteNombreParam = searchParams.get("nombre");

  const [pedidos, setPedidos]       = useState<PedidoResumen[]>([]);
  const [loading, setLoading]       = useState(true);
  const [buscar, setBuscar]         = useState(clienteNombreParam ?? "");
  const [estadoFilter, setEstado]   = useState("todos");
  const [periodoIdx, setPeriodo]    = useState(0);
  const [pagina, setPagina]         = useState(0);

  useEffect(() => {
    api.pedidos
      .list({ limit: 500, cliente_id: clienteIdParam ?? undefined })
      .then(setPedidos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [clienteIdParam]);

  const filtered = useMemo(() => {
    const q = buscar.toLowerCase();
    const dias = PERIODOS[periodoIdx].days;
    const desde = dias > 0 ? Date.now() - dias * 86400000 : 0;
    return pedidos.filter((p) => {
      const matchQ      = !q || p.nombre_cliente.toLowerCase().includes(q) || p.numero.toLowerCase().includes(q);
      const matchEstado = estadoFilter === "todos" || p.estado === estadoFilter;
      const matchPeriodo = dias === 0 || new Date(p.creado_en).getTime() >= desde;
      return matchQ && matchEstado && matchPeriodo;
    });
  }, [pedidos, buscar, estadoFilter, periodoIdx]);

  const totalPaginas  = Math.max(1, Math.ceil(filtered.length / POR_PAGINA));
  const paginaActual  = Math.min(pagina, totalPaginas - 1);
  const paginados     = filtered.slice(paginaActual * POR_PAGINA, (paginaActual + 1) * POR_PAGINA);
  const pageNumbers   = buildPageNumbers(totalPaginas, paginaActual);

  function changePage(n: number) {
    setPagina(Math.max(0, Math.min(totalPaginas - 1, n)));
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Historial de Pedidos</h1>
        <p className="text-sm text-gray-500 mt-1">
          Consulta el seguimiento de todos tus pedidos realizados
        </p>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-5 items-center">
        <input
          type="text"
          placeholder="Buscar por cliente..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(0); }}
          className="flex-1 min-w-[180px] px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        />
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-gray-500">Estado:</span>
          <select
            value={estadoFilter}
            onChange={(e) => { setEstado(e.target.value); setPagina(0); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="todos">Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="confirmado">En proceso</option>
            <option value="entregado">Completado</option>
            <option value="cancelado">Cancelado</option>
          </select>
        </div>
        <select
          value={periodoIdx}
          onChange={(e) => { setPeriodo(Number(e.target.value)); setPagina(0); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          {PERIODOS.map((p, i) => (
            <option key={p.label} value={i}>{p.label}</option>
          ))}
        </select>
        <button
          onClick={() => exportCSV(filtered)}
          className="ml-auto flex items-center gap-1.5 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50"
        >
          ↓ Exportar CSV
        </button>
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando historial...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-5 py-3 font-semibold text-gray-500">N° Pedido</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-500">Cliente</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-500">Fecha</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-500">Productos</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-500">Total</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-500">Estado</th>
                <th className="text-center px-4 py-3 font-semibold text-gray-500">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {paginados.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-gray-400">
                    No hay pedidos que coincidan con los filtros.
                  </td>
                </tr>
              ) : (
                paginados.map((p) => {
                  const e = ESTADO_CONFIG[p.estado] ?? { bg: "#F1F3F5", text: "#495057", label: p.estado };
                  return (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-5 py-3">
                        <Link
                          href={`/historial/${p.id}`}
                          className="font-medium"
                          style={{ color: "#3B5BDB" }}
                        >
                          {p.numero}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-gray-700">{p.nombre_cliente}</td>
                      <td className="px-4 py-3 text-gray-500">{formatDate(p.creado_en)}</td>
                      <td className="px-4 py-3 text-gray-500">{p.n_productos} productos</td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900">
                        {formatCurrency(p.total)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className="text-xs px-3 py-1 rounded-full font-medium"
                          style={{ backgroundColor: e.bg, color: e.text }}
                        >
                          {e.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Link
                          href={`/historial/${p.id}`}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white"
                          style={{ backgroundColor: "#3B5BDB" }}
                        >
                          Ver detalle
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>

          {/* Paginación */}
          <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500">
            <span>
              Mostrando {filtered.length === 0 ? 0 : paginaActual * POR_PAGINA + 1}
              –{Math.min((paginaActual + 1) * POR_PAGINA, filtered.length)} de {filtered.length} pedidos
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => changePage(paginaActual - 1)}
                disabled={paginaActual === 0}
                className="px-2 py-1 rounded text-xs hover:bg-gray-100 disabled:opacity-40"
              >
                &lt; Anterior
              </button>
              {pageNumbers.map((n, i) =>
                n === "..." ? (
                  <span key={`dots-${i}`} className="px-1 text-xs">...</span>
                ) : (
                  <button
                    key={n}
                    onClick={() => changePage(n as number)}
                    className={`w-7 h-7 rounded text-xs font-medium transition-colors ${
                      paginaActual === n ? "text-white" : "hover:bg-gray-100 text-gray-600"
                    }`}
                    style={paginaActual === n ? { backgroundColor: "#3B5BDB" } : {}}
                  >
                    {(n as number) + 1}
                  </button>
                )
              )}
              <button
                onClick={() => changePage(paginaActual + 1)}
                disabled={paginaActual === totalPaginas - 1}
                className="px-2 py-1 rounded text-xs hover:bg-gray-100 disabled:opacity-40"
              >
                Siguiente &gt;
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HistorialPage() {
  return (
    <Suspense fallback={<div className="p-6 text-gray-400">Cargando...</div>}>
      <HistorialContent />
    </Suspense>
  );
}
