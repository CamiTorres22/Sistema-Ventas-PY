// ── Auth ──────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  rol: "vendedor" | "admin";
  nombre: string;
  vendedor_id: number;
}

export interface AuthUser {
  token: string;
  rol: "vendedor" | "admin";
  nombre: string;
  vendedor_id: number;
}

// UsuarioOut: lo que devuelve GET /vendedores (backend schema)
export interface VendedorOut {
  id: number;
  nombre: string;
  email: string;
  rol: "vendedor" | "admin";
  activo: boolean;
}

// ── Clientes ──────────────────────────────────────────────────────────────────

export interface Cliente {
  cliente_id: string;
  nombre: string;
  ruc: string | null;
  telefono: string | null;
  rubro_cliente: string;
  subrubro_1: string | null;
  subrubro_2: string | null;
  sede_cliente: string;
  tipo: string | null;
  activo: boolean;
  vendedor_id?: number | null;
}

// ── Productos ─────────────────────────────────────────────────────────────────

export interface Producto {
  producto_id: string;
  nombre: string;
  categoria_producto: string;
  descripcion: string | null;
  precio_unitario: number;
  costo_unitario: number;
  stock: number;
  sede: string;
  fecha_ingreso_catalogo: string | null;
  fecha_min_caducidad: string | null;
  rotacion_diaria: number;
  baja_rotacion: number;
  activo: boolean;
}

// ── Recomendaciones ───────────────────────────────────────────────────────────

export interface ProductoRecomendado {
  producto_id: string;
  nombre: string;
  categoria_producto: string;
  precio_unitario: number;
  stock: number;
  score_final: number;
  ncf_score: number;
  s_urgency: number;
  s_rotation: number;
  s_novelty: number;
  es_urgente: boolean;
  es_nuevo: boolean;
  es_baja_rotacion: boolean;
  dias_para_vencer: number | null;
  dias_en_catalogo: number | null;
  rotacion_diaria: number | null;
}

export interface DashboardResponse {
  cliente_id: string;
  urgentes: ProductoRecomendado[];
  baja_rotacion: ProductoRecomendado[];
  nuevos: ProductoRecomendado[];
  total: number;
  fecha_calculo: string | null;
}

// ── Carrito ───────────────────────────────────────────────────────────────────

export interface ItemCarrito {
  producto: Producto;
  cantidad: number;
  desde_recomendacion: boolean;
}

// ── Pedidos ───────────────────────────────────────────────────────────────────

export interface DetallePedido {
  producto_id: string;
  nombre: string;
  categoria_producto: string;
  cantidad: number;
  precio_unit: number;
  subtotal: number;
  desde_recomendacion: boolean;
}

export interface Pedido {
  id: number;
  numero: string;
  cliente_id: string;
  vendedor_id: number;
  estado: string;
  subtotal: number;
  impuesto: number;
  descuento: number;
  total: number;
  forma_pago: string | null;
  notas: string | null;
  creado_en: string;
  detalles: DetallePedido[];
}

export interface PedidoResumen {
  id: number;
  numero: string;
  cliente_id: string;
  nombre_cliente: string;
  estado: string;
  total: number;
  n_productos: number;
  creado_en: string;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface MetricasModelo {
  ndcg_at_10: number | null;
  hitrate_at_10: number | null;
  precision_at_10: number | null;
  tasa_conversion: number | null;
  rotation_coverage: number | null;
  n_usuarios: number;
  n_productos: number;
  fecha_entrenamiento: string | null;
  fecha_ultimo_batch: string | null;
}
