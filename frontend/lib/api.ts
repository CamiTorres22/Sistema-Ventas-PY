/**
 * api.ts — Cliente HTTP para el backend FastAPI
 * Todas las llamadas incluyen el JWT del localStorage automáticamente.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ico_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("ico_token");
    localStorage.removeItem("ico_user");
    window.location.href = "/login";
    throw new Error("No autorizado");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Error del servidor");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<import("./types").TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<import("./types").AuthUser>("/auth/me"),
  },

  // ── Clientes ────────────────────────────────────────────────────────────────
  clientes: {
    list: (params?: { buscar?: string; sede?: string; tipo?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.buscar) q.set("buscar", params.buscar);
      if (params?.sede)   q.set("sede", params.sede);
      if (params?.tipo)   q.set("tipo", params.tipo);
      if (params?.limit)  q.set("limit", String(params.limit));
      return request<import("./types").Cliente[]>(`/clientes?${q}`);
    },
    get: (id: string) => request<import("./types").Cliente>(`/clientes/${id}`),
    create: (data: Partial<import("./types").Cliente>) =>
      request<import("./types").Cliente>("/clientes", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<import("./types").Cliente>) =>
      request<import("./types").Cliente>(`/clientes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    asignar: (clienteId: string, vendedorId: number) =>
      request<{ detail: string }>(`/clientes/${clienteId}/asignar?vendedor_id=${vendedorId}`, { method: "POST" }),
  },

  // ── Productos ────────────────────────────────────────────────────────────────
  productos: {
    list: (params?: { categoria?: string; buscar?: string; limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.categoria) q.set("categoria", params.categoria);
      if (params?.buscar)    q.set("buscar", params.buscar);
      if (params?.limit)     q.set("limit", String(params.limit));
      if (params?.skip)      q.set("skip", String(params.skip));
      return request<import("./types").Producto[]>(`/productos?${q}`);
    },
    get: (id: string) => request<import("./types").Producto>(`/productos/${id}`),
    create: (data: Partial<import("./types").Producto>) =>
      request<import("./types").Producto>("/productos", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<import("./types").Producto>) =>
      request<import("./types").Producto>(`/productos/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    addStock: (id: string, incremento: number) =>
      request<import("./types").Producto>(`/productos/${id}/stock`, {
        method: "PATCH",
        body: JSON.stringify({ incremento }),
      }),
  },

  // ── Recomendaciones ──────────────────────────────────────────────────────────
  recomendar: {
    dashboard: (clienteId: string, topK = 10) =>
      request<import("./types").DashboardResponse>(
        `/recomendar/dashboard/${clienteId}?top_k=${topK}`
      ),
    general: (clienteId: string, topK = 10) =>
      request<import("./types").DashboardResponse>(
        `/recomendar/${clienteId}?top_k=${topK}`
      ),
  },

  // ── Pedidos ──────────────────────────────────────────────────────────────────
  pedidos: {
    create: (data: {
      cliente_id: string;
      items: { producto_id: string; cantidad: number; desde_recomendacion: boolean }[];
      forma_pago?: string;
      notas?: string;
    }) => request<import("./types").Pedido>("/pedidos", { method: "POST", body: JSON.stringify(data) }),

    list: (params?: { estado?: string; limit?: number; cliente_id?: string }) => {
      const q = new URLSearchParams();
      if (params?.estado)     q.set("estado",     params.estado);
      if (params?.limit)      q.set("limit",      String(params.limit));
      if (params?.cliente_id) q.set("cliente_id", params.cliente_id);
      return request<import("./types").PedidoResumen[]>(`/pedidos?${q}`);
    },
    get: (id: number) => request<import("./types").Pedido>(`/pedidos/${id}`),
  },

  // ── Vendedores ───────────────────────────────────────────────────────────────
  vendedores: {
    list: () => request<import("./types").VendedorOut[]>("/vendedores"),
    create: (data: { nombre: string; email: string; password: string; rol: string }) =>
      request<import("./types").VendedorOut>("/vendedores", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: { nombre?: string; email?: string; activo?: boolean }) =>
      request<import("./types").VendedorOut>(`/vendedores/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    cartera: (id: number) =>
      request<import("./types").Cliente[]>(`/vendedores/${id}/cartera`),
  },

  // ── Admin ────────────────────────────────────────────────────────────────────
  admin: {
    metricas: () => request<import("./types").MetricasModelo>("/admin/metricas"),
    actividad: () => request<{ actividad: { accion: string; usuario: string; fecha: string; detalle: string }[] }>("/admin/actividad"),
    health: () => request<{ status: string; modelo_cargado: boolean; batch_disponible: boolean; mensaje: string }>("/admin/health"),
    logs: (soloFallidos = false) => request<{ id: number; email: string; nombre: string | null; rol: string | null; exitoso: boolean; motivo_fallo: string | null; ip_address: string | null; user_agent: string | null; creado_en: string }[]>(`/admin/logs?limit=100${soloFallidos ? "&solo_fallidos=true" : ""}`),
  },
};
