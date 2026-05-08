"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { TokenResponse } from "./types";

interface AuthState {
  token: string | null;
  rol: "vendedor" | "admin" | null;
  nombre: string | null;
  vendedorId: number | null;
}

interface AuthContextValue extends AuthState {
  login: (data: TokenResponse) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({
    token: null,
    rol: null,
    nombre: null,
    vendedorId: null,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("ico_token");
    const raw = localStorage.getItem("ico_user");
    if (token && raw) {
      try {
        const user = JSON.parse(raw);
        setAuth({ token, rol: user.rol, nombre: user.nombre, vendedorId: user.vendedor_id });
      } catch {
        localStorage.removeItem("ico_token");
        localStorage.removeItem("ico_user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((data: TokenResponse) => {
    localStorage.setItem("ico_token", data.access_token);
    localStorage.setItem(
      "ico_user",
      JSON.stringify({ rol: data.rol, nombre: data.nombre, vendedor_id: data.vendedor_id })
    );
    setAuth({
      token: data.access_token,
      rol: data.rol,
      nombre: data.nombre,
      vendedorId: data.vendedor_id,
    });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("ico_token");
    localStorage.removeItem("ico_user");
    setAuth({ token: null, rol: null, nombre: null, vendedorId: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...auth, login, logout, isAuthenticated: !!auth.token, isLoading }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
