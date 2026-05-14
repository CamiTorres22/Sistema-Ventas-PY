"use client";

import { useEffect, useState, Suspense } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Package, CheckCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Pedido } from "@/lib/types";

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
}

function formatDateLong(s: string) {
  return new Date(s).toLocaleDateString("es-PE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatDateShort(s: string) {
  return new Date(s).toLocaleDateString("es-PE", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function addBusinessDays(date: Date, days: number): Date {
  const d = new Date(date);
  let added = 0;
  while (added < days) {
    d.setDate(d.getDate() + 1);
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) added++;
  }
  return d;
}

const ESTADO_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  pendiente:   { bg: "#FFF3BF", text: "#E67700", label: "Pendiente" },
  confirmado:  { bg: "#DBE4FF", text: "#3B5BDB", label: "En proceso" },
  en_proceso:  { bg: "#DBE4FF", text: "#3B5BDB", label: "En proceso" },
  entregado:   { bg: "#D3F9D8", text: "#2F9E44", label: "Completado" },
  completado:  { bg: "#D3F9D8", text: "#2F9E44", label: "Completado" },
  cancelado:   { bg: "#FFE3E3", text: "#C92A2A", label: "Cancelado" },
};

function DetallePedidoContent() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { nombre } = useAuth();
  const esNuevo = searchParams.get("nuevo") === "true";

  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.pedidos
      .get(Number(id))
      .then(setPedido)
      .catch(() => router.push("/historial"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6 text-gray-400">Cargando pedido...</div>;
  if (!pedido) return null;

  const estado = ESTADO_CONFIG[pedido.estado] ?? { bg: "#F1F3F5", text: "#495057", label: pedido.estado };
  const fechaEntrega = addBusinessDays(new Date(pedido.creado_en), 3);
  const subtotal = pedido.subtotal;
  const impuesto = pedido.impuesto;
  const descuento = pedido.descuento ?? 0;

  return (
    <div className="p-6 max-w-5xl">
      {/* Banner confirmación */}
      {esNuevo && (
        <div className="mb-5 bg-green-50 border border-green-200 rounded-xl px-5 py-4 flex items-center gap-3">
          <div className="w-9 h-9 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
            <CheckCircle size={18} className="text-white" />
          </div>
          <div>
            <p className="font-semibold text-green-800 text-sm">
              Pedido {pedido.numero} registrado exitosamente
            </p>
            <p className="text-green-600 text-xs mt-0.5">
              El pedido fue confirmado y notificado al equipo de despacho.
            </p>
          </div>
        </div>
      )}

      {/* Header azul */}
      <div
        className="rounded-xl px-6 py-5 mb-5 flex items-center justify-between"
        style={{ backgroundColor: "#3B5BDB" }}
      >
        <div>
          <h1 className="text-xl font-bold text-white">Pedido #{pedido.numero}</h1>
          <p className="text-sm mt-0.5" style={{ color: "#A5B4FC" }}>
            {pedido.cliente_id}
          </p>
        </div>
        <span
          className="text-xs px-4 py-1.5 rounded-full font-semibold"
          style={{ backgroundColor: estado.bg, color: estado.text }}
        >
          ✓ {estado.label}
        </span>
      </div>

      {/* Info row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-gray-200 rounded-xl overflow-hidden mb-5">
        {[
          { label: "N° de Pedido",    value: pedido.numero },
          { label: "Fecha del Pedido", value: formatDateLong(pedido.creado_en) },
          { label: "Fecha de Entrega", value: formatDateShort(fechaEntrega.toISOString()) },
          { label: "Forma de Pago",   value: pedido.forma_pago ?? "Contado" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white px-5 py-4">
            <p className="text-xs text-gray-400 mb-1">{label}</p>
            <p className="text-sm font-semibold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      {/* Cuerpo */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Productos */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Productos del Pedido</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-5 py-3 font-medium text-gray-400">Producto</th>
                <th className="text-center px-3 py-3 font-medium text-gray-400">Cant.</th>
                <th className="text-right px-3 py-3 font-medium text-gray-400">P. Unit.</th>
                <th className="text-right px-5 py-3 font-medium text-gray-400">Subtotal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {pedido.detalles.map((d) => (
                <tr key={d.producto_id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <Package size={15} className="text-gray-300 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-gray-900">{d.nombre}</p>
                        <p className="text-xs text-gray-400">{d.categoria_producto}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-center font-semibold" style={{ color: "#3B5BDB" }}>
                    x{d.cantidad}
                  </td>
                  <td className="px-3 py-3 text-right text-gray-500">
                    {formatCurrency(d.precio_unit)}
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">
                    {formatCurrency(d.subtotal)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Resumen */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-3">
          <h2 className="font-semibold text-gray-900">Resumen del Pedido</h2>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-500">
              <span>Subtotal ({pedido.detalles.length} productos)</span>
              <span>{formatCurrency(subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>Impuesto (12%)</span>
              <span>{formatCurrency(impuesto)}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>Descuento cliente</span>
              <span>-{formatCurrency(descuento)}</span>
            </div>
            <div className="border-t border-gray-100 pt-2 flex justify-between font-bold text-base">
              <span className="text-gray-900">TOTAL</span>
              <span style={{ color: "#3B5BDB" }}>{formatCurrency(pedido.total)}</span>
            </div>
          </div>

          <div className="border-t border-gray-100 pt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Forma de Pago</span>
              <span className="font-medium text-gray-900 text-right">{pedido.forma_pago ?? "Contado"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Fecha de Entrega</span>
              <span className="font-medium text-gray-900 text-right">
                {formatDateShort(fechaEntrega.toISOString())}
              </span>
            </div>
            {nombre && (
              <div className="flex justify-between">
                <span className="text-gray-400">Vendedor</span>
                <span className="font-medium text-gray-900 text-right">{nombre}</span>
              </div>
            )}
          </div>

          <div className="border-t border-gray-100 pt-3">
            <p className="text-sm font-semibold text-gray-900 mb-3">Estado del Pedido</p>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0" />
                <span className="text-gray-700 flex-1">Pedido registrado</span>
                <span className="text-xs text-gray-400">
                  {new Date(pedido.creado_en).toLocaleDateString("es-PE", { day: "2-digit", month: "2-digit" })}
                </span>
              </div>
              {(pedido.estado === "confirmado" || pedido.estado === "entregado") && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0" />
                  <span className="text-gray-700 flex-1">En preparación</span>
                </div>
              )}
              {pedido.estado === "entregado" && (
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full bg-green-500 flex-shrink-0" />
                  <span className="text-gray-700 flex-1">Entregado</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Acciones */}
      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          href="/historial"
          className="flex items-center gap-2 px-5 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50"
        >
          <ArrowLeft size={15} />
          Volver al Historial
        </Link>
        <Link
          href="/clientes"
          className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white"
          style={{ backgroundColor: "#3B5BDB" }}
        >
          Nuevo Pedido
        </Link>
      </div>
    </div>
  );
}

export default function DetallePedidoPage() {
  return (
    <Suspense fallback={<div className="p-6 text-gray-400">Cargando...</div>}>
      <DetallePedidoContent />
    </Suspense>
  );
}
