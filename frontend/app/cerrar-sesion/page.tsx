"use client";

import Link from "next/link";
import { LogOut } from "lucide-react";

export default function CerrarSesionPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-10 flex flex-col items-center text-center max-w-sm w-full">
        {/* Ícono */}
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mb-5"
          style={{ backgroundColor: "#EEF2FF" }}
        >
          <LogOut size={28} style={{ color: "#3B5BDB" }} />
        </div>

        {/* Logo */}
        <p className="text-xs font-semibold tracking-widest uppercase mb-6" style={{ color: "#3B5BDB" }}>
          ICO Distribuidora
        </p>

        {/* Mensaje */}
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Cerraste sesión
        </h1>
        <p className="text-sm text-gray-500 mb-8">
          Tu sesión fue cerrada correctamente. Puedes volver a ingresar cuando quieras.
        </p>

        {/* Botón */}
        <Link
          href="/login"
          className="w-full py-3 rounded-xl text-sm font-semibold text-white text-center transition-opacity hover:opacity-90"
          style={{ backgroundColor: "#3B5BDB" }}
        >
          Volver a iniciar sesión
        </Link>
      </div>
    </div>
  );
}
