"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MetricasModelo } from "@/lib/types";
import {
  BarChart3,
  Users,
  Package,
  Activity,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";

interface ActividadItem {
  accion: string;
  usuario: string;
  fecha: string;
  detalle: string;
}

function pct(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmt(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toFixed(4);
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function PanelAdminPage() {
  const [metricas, setMetricas] = useState<MetricasModelo | null>(null);
  const [actividad, setActividad] = useState<ActividadItem[]>([]);
  const [health, setHealth] = useState<{
    status: string;
    modelo_cargado: boolean;
    batch_disponible: boolean;
    mensaje: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [m, a, h] = await Promise.all([
          api.admin.metricas(),
          api.admin.actividad(),
          api.admin.health(),
        ]);
        setMetricas(m);
        setActividad(a.actividad ?? []);
        setHealth(h);
      } catch {}
      finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-6 text-center text-gray-400 py-20">Cargando métricas...</div>
    );
  }

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Panel de Administración</h1>
        <p className="text-gray-500 mt-1">Métricas del modelo NeuMF y actividad del sistema</p>
      </div>

      {/* Health status */}
      {health && (
        <div className={`mb-6 rounded-xl border p-4 flex items-center gap-4 ${
          health.status === "ok" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
        }`}>
          {health.status === "ok"
            ? <CheckCircle size={20} className="text-green-600 flex-shrink-0" />
            : <XCircle size={20} className="text-red-600 flex-shrink-0" />
          }
          <div className="flex-1 min-w-0">
            <p className={`font-semibold text-sm ${health.status === "ok" ? "text-green-800" : "text-red-800"}`}>
              Sistema {health.status === "ok" ? "operativo" : "con problemas"}
            </p>
            <p className="text-xs text-gray-500 truncate">{health.mensaje}</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className={`flex items-center gap-1 ${health.modelo_cargado ? "text-green-600" : "text-red-500"}`}>
              {health.modelo_cargado ? "✓" : "✗"} Modelo
            </span>
            <span className={`flex items-center gap-1 ${health.batch_disponible ? "text-green-600" : "text-red-500"}`}>
              {health.batch_disponible ? "✓" : "✗"} Batch
            </span>
          </div>
        </div>
      )}

      {/* Métricas del modelo */}
      {metricas && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard
              icon={<BarChart3 size={20} className="text-blue-600" />}
              label="NDCG@10"
              value={fmt(metricas.ndcg_at_10)}
              bg="bg-blue-50"
              description="Calidad del ranking"
            />
            <MetricCard
              icon={<Activity size={20} className="text-purple-600" />}
              label="HitRate@10"
              value={pct(metricas.hitrate_at_10)}
              bg="bg-purple-50"
              description="Cobertura de hits"
            />
            <MetricCard
              icon={<BarChart3 size={20} className="text-orange-600" />}
              label="Precision@10"
              value={pct(metricas.precision_at_10)}
              bg="bg-orange-50"
              description="Precisión del top-10"
            />
            <MetricCard
              icon={<Activity size={20} className="text-green-600" />}
              label="Tasa conversión"
              value={pct(metricas.tasa_conversion)}
              bg="bg-green-50"
              description="Recom. → pedido"
            />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <MetricCard
              icon={<Users size={20} className="text-teal-600" />}
              label="Usuarios"
              value={String(metricas.n_usuarios)}
              bg="bg-teal-50"
              description="Clientes en el modelo"
            />
            <MetricCard
              icon={<Package size={20} className="text-indigo-600" />}
              label="Productos"
              value={String(metricas.n_productos)}
              bg="bg-indigo-50"
              description="Ítems en el catálogo"
            />
            <MetricCard
              icon={<Clock size={20} className="text-gray-600" />}
              label="Entrenamiento"
              value={metricas.fecha_entrenamiento
                ? new Date(metricas.fecha_entrenamiento).toLocaleDateString("es-PE")
                : "—"
              }
              bg="bg-gray-100"
              description="Último entreno"
            />
            <MetricCard
              icon={<Clock size={20} className="text-gray-600" />}
              label="Último batch"
              value={metricas.fecha_ultimo_batch
                ? new Date(metricas.fecha_ultimo_batch).toLocaleDateString("es-PE")
                : "—"
              }
              bg="bg-gray-100"
              description="Predicciones"
            />
          </div>
        </>
      )}

      {/* Actividad reciente */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Actividad reciente</h2>
        </div>
        {actividad.length === 0 ? (
          <div className="py-8 text-center text-gray-400 text-sm">Sin actividad registrada.</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {actividad.slice(0, 20).map((a, i) => (
              <div key={i} className="px-6 py-3 flex items-start gap-3">
                <div className="w-2 h-2 bg-blue-400 rounded-full mt-1.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">
                    <span className="font-medium">{a.usuario}</span> — {a.accion}
                  </p>
                  {a.detalle && (
                    <p className="text-xs text-gray-400 truncate">{a.detalle}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">{formatDate(a.fecha)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  bg,
  description,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  bg: string;
  description: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className={`w-10 h-10 ${bg} rounded-lg flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-900 leading-tight">{value}</p>
      <p className="text-sm font-medium text-gray-700 mt-0.5">{label}</p>
      <p className="text-xs text-gray-400 mt-0.5">{description}</p>
    </div>
  );
}
