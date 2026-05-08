"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { AuthProvider, useAuth } from "@/lib/auth-context";

function LoginForm() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading, rol } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(rol === "admin" ? "/admin/panel" : "/inicio");
    }
  }, [isAuthenticated, isLoading, rol, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.auth.login(email, password);
      login(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Panel izquierdo */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-center px-16"
        style={{ backgroundColor: "#3B5BDB" }}
      >
        <div className="max-w-sm">
          <div className="mb-8">
            <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center mb-6">
              <span className="text-white text-2xl font-bold">ICO</span>
            </div>
            <h1 className="text-4xl font-bold text-white leading-tight mb-3">
              ICO Distribuidora
            </h1>
            <p className="text-blue-200 text-lg">
              Sistema de Gestión de Ventas
            </p>
          </div>
          <div className="space-y-4 mt-12">
            <div className="flex items-center gap-3 text-blue-100">
              <div className="w-2 h-2 bg-blue-300 rounded-full" />
              <span>Recomendaciones inteligentes de productos</span>
            </div>
            <div className="flex items-center gap-3 text-blue-100">
              <div className="w-2 h-2 bg-blue-300 rounded-full" />
              <span>Gestión de clientes y pedidos</span>
            </div>
            <div className="flex items-center gap-3 text-blue-100">
              <div className="w-2 h-2 bg-blue-300 rounded-full" />
              <span>Control de inventario en tiempo real</span>
            </div>
          </div>
        </div>
      </div>

      {/* Panel derecho */}
      <div className="flex-1 flex flex-col justify-center items-center px-8 bg-white">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <div className="lg:hidden mb-6">
              <span className="text-2xl font-bold" style={{ color: "#3B5BDB" }}>
                ICO Distribuidora
              </span>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Iniciar sesión</h2>
            <p className="text-gray-500 mt-1">Ingresa tus credenciales para continuar</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Correo electrónico
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                style={{ ["--tw-ring-color" as string]: "#3B5BDB" }}
                placeholder="correo@ejemplo.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:border-transparent transition"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-lg text-white font-semibold transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ backgroundColor: loading ? "#6b7280" : "#3B5BDB" }}
            >
              {loading ? "Ingresando..." : "Ingresar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  );
}
