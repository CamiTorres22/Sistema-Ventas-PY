"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Package,
  ShoppingCart,
  LogOut,
} from "lucide-react";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { CartProvider, useCart } from "@/lib/cart-context";

const navItems = [
  { href: "/inicio", label: "Inicio", icon: LayoutDashboard },
  { href: "/clientes", label: "Mis Clientes", icon: Users },
  { href: "/productos", label: "Productos", icon: Package },
  { href: "/carrito", label: "Carrito", icon: ShoppingCart, badge: true },
];

function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { nombre, logout, isAuthenticated, isLoading, rol } = useAuth();
  const { itemCount } = useCart();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
    } else if (rol === "admin") {
      router.replace("/admin/panel");
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
      style={{ backgroundColor: "#3B5BDB" }}
    >
      {/* Logo */}
      <div className="px-6 py-6 border-b border-blue-500/30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">ICO</span>
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-tight">ICO Distribuidora</p>
            <p className="text-blue-200 text-xs">Gestión de Ventas</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                active
                  ? "bg-white/20 text-white"
                  : "text-blue-100 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon size={18} />
              <span className="flex-1">{label}</span>
              {badge && itemCount > 0 && (
                <span className="bg-orange-500 text-white text-xs font-bold rounded-full min-w-[20px] h-5 flex items-center justify-center px-1">
                  {itemCount}
                </span>
              )}
            </Link>
          );
        })}

        {/* Separador */}
        <div className="border-t border-blue-500/30 my-2" />

        {/* Cerrar sesión como pestaña */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-blue-100 hover:bg-white/10 hover:text-white transition-all"
        >
          <LogOut size={18} />
          <span className="flex-1 text-left">Cerrar sesión</span>
        </button>
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-blue-500/30">
        <div className="px-3 py-2">
          <p className="text-white text-sm font-medium truncate">{nombre ?? "—"}</p>
          <p className="text-blue-200 text-xs">Vendedor</p>
        </div>
      </div>
    </aside>
  );
}

function VendedorLayoutInner({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-60 min-h-screen bg-gray-50">
        {children}
      </main>
    </div>
  );
}

export default function VendedorLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <CartProvider>
        <VendedorLayoutInner>{children}</VendedorLayoutInner>
      </CartProvider>
    </AuthProvider>
  );
}
