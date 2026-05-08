"use client";

import { useEffect, useState } from "react";
import { Search, UserPlus, RefreshCw, Users } from "lucide-react";
import { api } from "@/lib/api";
import type { Cliente, VendedorOut } from "@/lib/types";

export default function AdminClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [vendedores, setVendedores] = useState<VendedorOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [buscar, setBuscar] = useState("");
  const [asignando, setAsignando] = useState<string | null>(null);
  const [success, setSuccess] = useState("");
  // mapa clienteId → vendedor_id seleccionado actualmente
  const [seleccion, setSeleccion] = useState<Record<string, string>>({});
  const [pagina, setPagina] = useState(0);
  const POR_PAGINA = 50;

  useEffect(() => {
    async function load() {
      const [cli, vend] = await Promise.all([
        api.clientes.list({ limit: 5000 }),
        api.vendedores.list(),
      ]);
      setClientes(cli);
      setVendedores(vend.filter((v) => v.rol === "vendedor"));
      // inicializar selección con vendedores ya asignados
      const inicial: Record<string, string> = {};
      for (const c of cli) {
        inicial[c.cliente_id] = c.vendedor_id != null ? String(c.vendedor_id) : "";
      }
      setSeleccion(inicial);
      setLoading(false);
    }
    load().catch(() => setLoading(false));
  }, []);

  const filtered = clientes.filter((c) => {
    const q = buscar.toLowerCase();
    return (
      !q ||
      c.nombre.toLowerCase().includes(q) ||
      (c.ruc ?? "").includes(q) ||
      c.sede_cliente.toLowerCase().includes(q)
    );
  });

  const totalPaginas = Math.ceil(filtered.length / POR_PAGINA);
  const paginaActual = Math.min(pagina, Math.max(0, totalPaginas - 1));
  const paginados = filtered.slice(paginaActual * POR_PAGINA, (paginaActual + 1) * POR_PAGINA);

  async function asignar(clienteId: string, vendedorId: string) {
    if (!vendedorId) return;
    const anterior = seleccion[clienteId] ?? "";
    setSeleccion((prev) => ({ ...prev, [clienteId]: vendedorId })); // optimista
    setAsignando(clienteId);
    try {
      await api.clientes.asignar(clienteId, Number(vendedorId));
      setSuccess("Cliente asignado correctamente.");
      setTimeout(() => setSuccess(""), 3000);
    } catch {
      setSeleccion((prev) => ({ ...prev, [clienteId]: anterior })); // revertir si falla
    } finally {
      setAsignando(null);
    }
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Clientes</h1>
          <p className="text-gray-500 mt-1">{clientes.length} clientes registrados</p>
        </div>
      </div>

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      <div className="relative mb-5">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por nombre, RUC o sede..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(0); }}
          className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        />
      </div>

      {loading ? (
        <div className="py-16 text-center text-gray-400">Cargando...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-5 py-3 font-medium text-gray-500">Cliente</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Sede</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Rubro</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Estado</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">Asignar vendedor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {paginados.map((c) => (
                <tr key={c.cliente_id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{c.nombre}</p>
                    {c.ruc && <p className="text-xs text-gray-400">RUC: {c.ruc}</p>}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.sede_cliente}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{c.rubro_cliente}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${c.activo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {c.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <select
                        className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                        value={seleccion[c.cliente_id] ?? ""}
                        onChange={(e) => asignar(c.cliente_id, e.target.value)}
                      >
                        <option value="">— Sin asignar —</option>
                        {vendedores.map((v) => (
                          <option key={v.id} value={v.id}>
                            {v.nombre}
                          </option>
                        ))}
                      </select>
                      {asignando === c.cliente_id && (
                        <RefreshCw size={13} className="text-blue-500 animate-spin" />
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {totalPaginas > 1 && (
            <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>
                Mostrando {paginaActual * POR_PAGINA + 1}–{Math.min((paginaActual + 1) * POR_PAGINA, filtered.length)} de {filtered.length}
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
