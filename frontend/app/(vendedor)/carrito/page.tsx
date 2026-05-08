"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Minus, Package } from "lucide-react";
import { api } from "@/lib/api";
import { useCart } from "@/lib/cart-context";
import { useAuth } from "@/lib/auth-context";
import type { Cliente, DashboardResponse, ProductoRecomendado } from "@/lib/types";

const TAX_RATE = 0.12;

function formatCurrency(n: number) {
  return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);
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

function formatEntrega(date: Date) {
  return date.toLocaleDateString("es-PE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

type TabRec = "baja_rotacion" | "urgentes" | "nuevos";

const TAB_CONFIG: {
  key: TabRec;
  label: string;
  color: string;
  border: string;
  activeStyle: { backgroundColor: string; borderColor: string; color: string };
  headerBg: string;
  cardBg: string;
  badgeText: string;
}[] = [
  {
    key: "baja_rotacion",
    label: "Baja Rotación",
    color: "text-orange-700",
    border: "border-orange-300",
    activeStyle: { backgroundColor: "#FFF3BF", borderColor: "#F59F00", color: "#E67700" },
    headerBg: "#F59F00",
    cardBg: "#FFF3BF",
    badgeText: "BAJA ROTACION",
  },
  {
    key: "urgentes",
    label: "Próximos a Vencer",
    color: "text-red-600",
    border: "border-red-300",
    activeStyle: { backgroundColor: "#FFE3E3", borderColor: "#FA5252", color: "#C92A2A" },
    headerBg: "#FA5252",
    cardBg: "#FFF0F0",
    badgeText: "PRÓX. A VENCER",
  },
  {
    key: "nuevos",
    label: "Nuevos Productos",
    color: "text-green-700",
    border: "border-green-300",
    activeStyle: { backgroundColor: "#D3F9D8", borderColor: "#2F9E44", color: "#2F9E44" },
    headerBg: "#2F9E44",
    cardBg: "#F0FFF4",
    badgeText: "NUEVO",
  },
];

const FORMAS_PAGO = [
  { value: "contado",      label: "Contado" },
  { value: "credito_7",    label: "Crédito 7 días" },
  { value: "credito_15",   label: "Crédito 15 días" },
  { value: "credito_30",   label: "Crédito 30 días" },
];

export default function CarritoPage() {
  const router = useRouter();
  const { vendedorId } = useAuth();
  const { items, addItem, removeItem, updateCantidad, clearCart, total, itemCount } = useCart();

  const [clienteId, setClienteId]         = useState<string>("");
  const [clientes, setClientes]           = useState<Cliente[]>([]);
  const [clienteSelec, setClienteSelec]   = useState<Cliente | null>(null);
  const [recomendaciones, setRecs]        = useState<DashboardResponse | null>(null);
  const [loadingRec, setLoadingRec]       = useState(false);
  const [activeTab, setActiveTab]         = useState<TabRec>("baja_rotacion");
  const [submitting, setSubmitting]       = useState(false);
  const [error, setError]                 = useState("");
  const [formaPago, setFormaPago]         = useState("credito_30");
  const [notas, setNotas]                 = useState("");
  const [showFormaPago, setShowFormaPago] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem("ico_cliente_id");
    if (stored) setClienteId(stored);
  }, []);

  useEffect(() => {
    if (!vendedorId) return;
    api.vendedores.cartera(vendedorId).then(setClientes).catch(() => {});
  }, [vendedorId]);

  useEffect(() => {
    if (!clienteId) {
      setClienteSelec(null);
      setRecs(null);
      return;
    }
    const c = clientes.find((x) => x.cliente_id === clienteId) ?? null;
    setClienteSelec(c);
    sessionStorage.setItem("ico_cliente_id", clienteId);

    setLoadingRec(true);
    api.recomendar
      .dashboard(clienteId)
      .then(setRecs)
      .catch(() => setRecs(null))
      .finally(() => setLoadingRec(false));
  }, [clienteId, clientes]);

  const subtotal   = total;
  const impuesto   = subtotal * TAX_RATE;
  const descuento  = 0;
  const totalFinal = subtotal + impuesto - descuento;
  const entrega    = addBusinessDays(new Date(), 3);

  const formaLabel = FORMAS_PAGO.find((f) => f.value === formaPago)?.label ?? formaPago;

  const recList = recomendaciones
    ? activeTab === "urgentes"
      ? recomendaciones.urgentes
      : activeTab === "baja_rotacion"
      ? recomendaciones.baja_rotacion
      : recomendaciones.nuevos
    : [];

  const tabCfg = TAB_CONFIG.find((t) => t.key === activeTab)!;

  async function handleConfirmar() {
    if (!clienteId || items.length === 0) return;
    setError("");
    setSubmitting(true);
    try {
      const pedido = await api.pedidos.create({
        cliente_id: clienteId,
        items: items.map((i) => ({
          producto_id: i.producto.producto_id,
          cantidad: i.cantidad,
          desde_recomendacion: i.desde_recomendacion,
        })),
        forma_pago: formaPago,
        notas: notas || undefined,
      });
      clearCart();
      router.push(`/historial/${pedido.id}?nuevo=true`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear pedido");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-5">Carrito de Compras</h1>

      {/* Banner cliente */}
      {clienteSelec ? (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-3 mb-5 flex items-center gap-4">
          <p className="text-sm text-gray-700 flex-1">
            <span className="text-gray-500">Cliente seleccionado: </span>
            <span className="font-semibold" style={{ color: "#3B5BDB" }}>{clienteSelec.nombre}</span>
            {clienteSelec.tipo && (
              <span className="text-gray-500 ml-3">{clienteSelec.tipo}</span>
            )}
            {clienteSelec.ruc && (
              <span className="text-gray-500 ml-3">| RUC: {clienteSelec.ruc}</span>
            )}
          </p>
          <button
            onClick={() => { setClienteId(""); sessionStorage.removeItem("ico_cliente_id"); }}
            className="text-sm font-medium flex-shrink-0"
            style={{ color: "#3B5BDB" }}
          >
            Cambiar cliente &gt;
          </button>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-5">
          <p className="text-sm font-medium text-gray-700 mb-2">Seleccionar cliente</p>
          <select
            value={clienteId}
            onChange={(e) => setClienteId(e.target.value)}
            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">— Seleccionar cliente —</option>
            {clientes.map((c) => (
              <option key={c.cliente_id} value={c.cliente_id}>
                {c.nombre} ({c.sede_cliente})
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex flex-col xl:flex-row gap-6">
        {/* ── Columna izquierda ── */}
        <div className="flex-1">
          {/* Tabla de productos */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Productos en el Carrito</h2>
            </div>
            {items.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-gray-400 text-sm">El carrito está vacío.</p>
                <p className="text-gray-400 text-xs mt-1">
                  Agrega productos del catálogo o de las recomendaciones.
                </p>
              </div>
            ) : (
              <>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      <th className="text-left px-5 py-3 font-medium text-gray-400">Producto</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-400">P. Unit.</th>
                      <th className="text-center px-4 py-3 font-medium text-gray-400">Cantidad</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-400">Subtotal</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {items.map(({ producto, cantidad, desde_recomendacion }) => (
                      <tr key={producto.producto_id} className="hover:bg-gray-50">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-2">
                            <Package size={15} className="text-gray-300 flex-shrink-0" />
                            <div>
                              <p className="font-medium text-gray-900">{producto.nombre}</p>
                              <div className="flex items-center gap-2">
                                <p className="text-xs text-gray-400">{producto.categoria_producto}</p>
                                {desde_recomendacion && (
                                  <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded font-medium">
                                    Recom.
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500">
                          {formatCurrency(producto.precio_unitario)}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => updateCantidad(producto.producto_id, cantidad - 1)}
                              className="w-7 h-7 rounded border border-gray-200 flex items-center justify-center hover:bg-gray-50"
                            >
                              <Minus size={12} />
                            </button>
                            <span className="w-9 text-center font-semibold text-gray-900">{cantidad}</span>
                            <button
                              onClick={() => updateCantidad(producto.producto_id, cantidad + 1)}
                              disabled={cantidad >= producto.stock}
                              className="w-7 h-7 rounded flex items-center justify-center text-white disabled:opacity-40"
                              style={{ backgroundColor: "#3B5BDB" }}
                            >
                              <Plus size={12} />
                            </button>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900">
                          {formatCurrency(producto.precio_unitario * cantidad)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => removeItem(producto.producto_id)}
                            className="text-xs text-red-400 hover:text-red-600 font-medium"
                          >
                            Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-sm text-gray-500">{itemCount} productos agregados</span>
                  <span className="text-sm font-semibold" style={{ color: "#3B5BDB" }}>
                    Subtotal: {formatCurrency(subtotal)}
                  </span>
                </div>
              </>
            )}
          </div>

        </div>

        {/* ── Columna derecha: Resumen ── */}
        <div className="xl:w-72 flex-shrink-0">
          <div className="bg-white rounded-xl border border-gray-200 p-5 sticky top-6">
            <h2 className="font-semibold text-gray-900 mb-4">Resumen del Pedido</h2>

            {/* Info cliente */}
            {clienteSelec && (
              <div className="flex justify-between text-sm mb-3">
                <span className="text-gray-400">Cliente:</span>
                <span className="font-medium text-gray-900 text-right max-w-[150px] truncate">
                  {clienteSelec.nombre}
                </span>
              </div>
            )}

            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-500">
                <span>Subtotal ({itemCount} productos)</span>
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
            </div>

            <div className="border-t border-gray-100 my-3" />

            <div className="flex justify-between font-bold text-base mb-4">
              <span className="text-gray-900">TOTAL</span>
              <span style={{ color: "#3B5BDB" }}>{formatCurrency(totalFinal)}</span>
            </div>

            {/* Notas */}
            <p className="text-xs font-medium text-gray-600 mb-1">Notas (opcional):</p>
            <textarea
              rows={2}
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Instrucciones de entrega..."
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none mb-4"
            />

            {error && (
              <p className="text-xs text-red-500 mb-3">{error}</p>
            )}

            <button
              onClick={handleConfirmar}
              disabled={!clienteId || items.length === 0 || submitting}
              className="w-full py-3 rounded-lg text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed mb-2"
              style={{ backgroundColor: "#3B5BDB" }}
            >
              {submitting ? "Procesando..." : "Confirmar Pedido"}
            </button>

            <button
              onClick={() => router.push("/productos")}
              className="w-full py-2.5 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              Seguir Agregando Productos
            </button>

            <div className="border-t border-gray-100 mt-4 pt-4 space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Forma de pago:</span>
                {showFormaPago ? (
                  <select
                    value={formaPago}
                    onChange={(e) => { setFormaPago(e.target.value); setShowFormaPago(false); }}
                    autoFocus
                    onBlur={() => setShowFormaPago(false)}
                    className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none"
                  >
                    {FORMAS_PAGO.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                ) : (
                  <span className="text-gray-900 font-medium">
                    {formaLabel}{" "}
                    <button
                      onClick={() => setShowFormaPago(true)}
                      className="text-xs ml-1"
                      style={{ color: "#3B5BDB" }}
                    >
                      Cambiar &gt;
                    </button>
                  </span>
                )}
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Entrega estimada:</span>
                <span className="text-gray-900 font-medium text-right text-xs">
                  {formatEntrega(entrega)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Recomendaciones (ancho completo, debajo del layout) ── */}
      {clienteId && (
        <div className="mt-6">
          <h2 className="font-semibold text-gray-900 mb-1">Recomendaciones para este cliente</h2>
          <p className="text-sm text-gray-400 mb-3">
            Productos sugeridos según historial, vencimientos y novedades del catálogo
          </p>

          {/* Tabs */}
          <div className="flex gap-2 mb-4">
            {TAB_CONFIG.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className="px-4 py-1.5 rounded-full text-sm font-medium border transition-all"
                style={
                  activeTab === tab.key
                    ? tab.activeStyle
                    : { backgroundColor: "white", borderColor: tab.headerBg, color: tab.headerBg }
                }
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Panel recomendaciones */}
          {loadingRec ? (
            <div className="py-8 text-center text-gray-400 text-sm">Cargando recomendaciones...</div>
          ) : recList.length === 0 ? (
            <div className="py-8 text-center text-gray-400 text-sm">
              No hay recomendaciones en esta categoría.
            </div>
          ) : (
            <div className="rounded-xl overflow-hidden border border-gray-200">
              {/* Header del panel */}
              <div
                className="px-5 py-3 flex items-center justify-between"
                style={{ backgroundColor: tabCfg.headerBg }}
              >
                <p className="font-semibold text-white text-sm">
                  Productos con {tabCfg.label}
                </p>
                {activeTab === "urgentes" && (
                  <span className="text-xs bg-white/20 text-white px-2 py-0.5 rounded font-medium">
                    ⚠ VENCEN EN &lt; 30 DIAS
                  </span>
                )}
              </div>
              {/* Cards */}
              <div
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4"
                style={{ backgroundColor: tabCfg.cardBg }}
              >
                {recList.slice(0, 6).map((rec) => (
                  <RecCard
                    key={rec.producto_id}
                    rec={rec}
                    tabCfg={tabCfg}
                    inCart={items.some((i) => i.producto.producto_id === rec.producto_id)}
                    onAdd={() => {
                      addItem(
                        {
                          producto_id: rec.producto_id,
                          nombre: rec.nombre,
                          categoria_producto: rec.categoria_producto,
                          precio_unitario: rec.precio_unitario,
                          stock: rec.stock,
                          descripcion: null,
                          costo_unitario: 0,
                          sede: "",
                          fecha_ingreso_catalogo: null,
                          fecha_min_caducidad: null,
                          rotacion_diaria: rec.rotacion_diaria ?? 0,
                          baja_rotacion: rec.es_baja_rotacion ? 1 : 0,
                          activo: true,
                        },
                        true
                      );
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RecCard({
  rec,
  tabCfg,
  inCart,
  onAdd,
}: {
  rec: ProductoRecomendado;
  tabCfg: (typeof TAB_CONFIG)[0];
  inCart: boolean;
  onAdd: () => void;
}) {
  const [cantidad, setCantidad] = useState(1);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div
        className="px-3 py-1.5 text-xs font-bold"
        style={{ backgroundColor: tabCfg.headerBg, color: "white" }}
      >
        {tabCfg.badgeText}
      </div>
      <div className="p-3">
        <p className="text-sm font-semibold text-gray-900 line-clamp-2 leading-snug mb-1">
          {rec.nombre}
        </p>
        <p className="text-base font-bold mb-0.5" style={{ color: tabCfg.headerBg }}>
          {formatCurrency(rec.precio_unitario)}
        </p>
        <p className="text-xs text-gray-400 mb-3">
          {tabCfg.key === "baja_rotacion"
            ? rec.rotacion_diaria && rec.rotacion_diaria > 0
              ? `${Math.round(1 / rec.rotacion_diaria)} días sin venta`
              : "Sin ventas recientes"
            : tabCfg.key === "urgentes" && rec.dias_para_vencer !== null
            ? `${rec.dias_para_vencer} días para vencer`
            : `En catálogo hace ${rec.dias_en_catalogo ?? "—"} días`}
        </p>
        <div className="flex items-center gap-2">
          <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setCantidad((q) => Math.max(1, q - 1))}
              className="px-2 py-1 text-gray-500 hover:bg-gray-50 text-sm"
            >
              <Minus size={11} />
            </button>
            <span className="px-2 text-sm font-semibold text-gray-900">{cantidad}</span>
            <button
              onClick={() => setCantidad((q) => Math.min(rec.stock, q + 1))}
              className="px-2 py-1 text-white text-sm"
              style={{ backgroundColor: tabCfg.headerBg }}
            >
              <Plus size={11} />
            </button>
          </div>
          <button
            onClick={() => { for (let i = 0; i < cantidad; i++) onAdd(); }}
            disabled={rec.stock <= 0}
            className="flex-1 py-1.5 rounded-lg text-xs font-semibold text-white disabled:opacity-40"
            style={{ backgroundColor: tabCfg.headerBg }}
          >
            {inCart ? "✓ Agregado" : "+ Agregar"}
          </button>
        </div>
      </div>
    </div>
  );
}
