"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { PedidoResumen, Cliente } from "@/lib/types";

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

const estadoConfig: Record<string, { bg: string; text: string; label: string }> = {
  pendiente:  { bg: "#FFF3BF", text: "#E67700", label: "Pendiente" },
  confirmado: { bg: "#DBE4FF", text: "#3B5BDB", label: "En proceso" },
  entregado:  { bg: "#D3F9D8", text: "#2F9E44", label: "Completado" },
  cancelado:  { bg: "#FFE3E3", text: "#C92A2A", label: "Cancelado" },
};

export default function InicioPage() {
  const { nombre, vendedorId } = useAuth();
  const [pedidos, setPedidos] = useState<PedidoResumen[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [ped, cli] = await Promise.all([
          api.pedidos.list({ limit: 50 }),
          vendedorId ? api.vendedores.cartera(vendedorId) : Promise.resolve<Cliente[]>([]),
        ]);
        setPedidos(ped);
        setClientes(cli);
      } catch {}
      finally {
        setLoading(false);
      }
    }
    load();
  }, [vendedorId]);

  const now = new Date();
  const pedidosMes = pedidos.filter((p) => {
    const d = new Date(p.creado_en);
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  });
  const ventasMes = pedidosMes.reduce((acc, p) => acc + p.total, 0);
  const recientes = pedidos.slice(0, 7);

  return (
    <div className="p-6 max-w-5xl">
      {/* Banner de bienvenida */}
      <div
        className="rounded-2xl px-7 py-6 mb-6 flex items-center justify-between gap-4"
        style={{ backgroundColor: "#3B5BDB" }}
      >
        <div>
          <h1 className="text-2xl font-bold text-white">Hola, {nombre ?? "vendedor"}!</h1>
          <p className="text-sm mt-1" style={{ color: "#A5B4FC" }}>
            Selecciona un cliente para iniciar un nuevo pedido
          </p>
        </div>
        <Link
          href="/clientes"
          className="flex-shrink-0 bg-white rounded-xl px-5 py-2.5 text-sm font-semibold hover:opacity-90 transition-opacity"
          style={{ color: "#3B5BDB" }}
        >
          + Iniciar Nuevo Pedido
        </Link>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard label="Clientes Asignados" value={String(clientes.length)} borderColor="#3B5BDB" />
        <StatCard label="Pedidos Este Mes" value={String(pedidosMes.length)} borderColor="#2F9E44" />
        <StatCard label="Ventas del Mes" value={formatCurrency(ventasMes)} borderColor="#F59F00" />
      </div>

      {/* Pedidos recientes */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Pedidos Recientes</h2>
          <Link href="/historial" className="text-sm font-medium" style={{ color: "#3B5BDB" }}>
            Ver historial &gt;
          </Link>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-400">Cargando...</div>
        ) : recientes.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No hay pedidos aún.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-6 py-3 font-medium text-gray-400">Cliente</th>
                <th className="text-left px-4 py-3 font-medium text-gray-400">Fecha</th>
                <th className="text-right px-4 py-3 font-medium text-gray-400">Monto</th>
                <th className="text-right px-6 py-3 font-medium text-gray-400">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {recientes.map((p) => {
                const e = estadoConfig[p.estado] ?? { bg: "#F1F3F5", text: "#495057", label: p.estado };
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium text-gray-900">{p.nombre_cliente}</td>
                    <td className="px-4 py-4 text-gray-500">{formatDate(p.creado_en)}</td>
                    <td className="px-4 py-4 text-right font-semibold text-gray-900">{formatCurrency(p.total)}</td>
                    <td className="px-6 py-4 text-right">
                      <span
                        className="text-xs px-3 py-1 rounded-full font-medium"
                        style={{ backgroundColor: e.bg, color: e.text }}
                      >
                        {e.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  borderColor,
}: {
  label: string;
  value: string;
  borderColor: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="h-1" style={{ backgroundColor: borderColor }} />
      <div className="p-5">
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 mt-1">{label}</p>
      </div>
    </div>
  );
}
