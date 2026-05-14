"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Package,
  UserCheck,
  LogOut,
  ShieldCheck,
  ScrollText,
} from "lucide-react";
import { AuthProvider, useAuth } from "@/lib/auth-context";

const navItems = [
  { href: "/admin/panel",      label: "Panel Admin",    icon: LayoutDashboard },
  { href: "/admin/clientes",   label: "Clientes",       icon: Users },
  { href: "/admin/productos",  label: "Productos",      icon: Package },
  { href: "/admin/vendedores", label: "Vendedores",     icon: UserCheck },
  { href: "/admin/logs",       label: "Logs de sesión", icon: ScrollText },
];

function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { nombre, logout, isAuthenticated, isLoading, rol } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
    } else if (rol === "vendedor") {
      router.replace("/inicio");
    }
  }, [isAuthenticated, isLoading, rol, router]);

  if (isLoading) return null;

  function handleLogout() {
    logout();
    router.replace("/cerrar-sesion");
  }

  return (
    <aside
      className="fixed top-0 left-0 h-full w-60 flex flex-col z-30"
      style={{ backgroundColor: "#1a1a2e" }}
    >
      {/* Logo */}
      <div className="px-6 py-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/10 rounded-lg flex items-center justify-center">
            <ShieldCheck size={18} className="text-blue-300" />
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-tight">Panel Admin</p>
            <p className="text-gray-400 text-xs">ICO Distribuidora</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                active
                  ? "bg-white/10 text-white"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}

        {/* Separador */}
        <div className="border-t border-white/10 my-2" />

        {/* Cerrar sesión como pestaña */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-white/5 hover:text-white transition-all"
        >
          <LogOut size={18} />
          <span className="flex-1 text-left">Cerrar sesión</span>
        </button>
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="px-3 py-2">
          <p className="text-white text-sm font-medium truncate">{nombre ?? "—"}</p>
          <p className="text-gray-400 text-xs">Administrador</p>
        </div>
      </div>
    </aside>
  );
}

function AdminLayoutInner({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-screen">
      <AdminSidebar />
      <main className="flex-1 ml-60 min-h-screen bg-gray-50">
        {children}
      </main>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AdminLayoutInner>{children}</AdminLayoutInner>
    </AuthProvider>
  );
}
