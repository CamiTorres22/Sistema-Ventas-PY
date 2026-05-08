"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import type { ItemCarrito, Producto } from "./types";

interface CartContextValue {
  items: ItemCarrito[];
  addItem: (producto: Producto, desdeRecomendacion?: boolean) => void;
  removeItem: (productoId: string) => void;
  updateCantidad: (productoId: string, cantidad: number) => void;
  clearCart: () => void;
  total: number;
  itemCount: number;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ItemCarrito[]>([]);

  const addItem = useCallback((producto: Producto, desdeRecomendacion = false) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.producto.producto_id === producto.producto_id);
      if (existing) {
        return prev.map((i) =>
          i.producto.producto_id === producto.producto_id
            ? { ...i, cantidad: i.cantidad + 1 }
            : i
        );
      }
      return [...prev, { producto, cantidad: 1, desde_recomendacion: desdeRecomendacion }];
    });
  }, []);

  const removeItem = useCallback((productoId: string) => {
    setItems((prev) => prev.filter((i) => i.producto.producto_id !== productoId));
  }, []);

  const updateCantidad = useCallback((productoId: string, cantidad: number) => {
    if (cantidad <= 0) {
      setItems((prev) => prev.filter((i) => i.producto.producto_id !== productoId));
      return;
    }
    setItems((prev) =>
      prev.map((i) =>
        i.producto.producto_id === productoId ? { ...i, cantidad } : i
      )
    );
  }, []);

  const clearCart = useCallback(() => setItems([]), []);

  const total = items.reduce(
    (acc, i) => acc + i.producto.precio_unitario * i.cantidad,
    0
  );
  const itemCount = items.reduce((acc, i) => acc + i.cantidad, 0);

  return (
    <CartContext.Provider
      value={{ items, addItem, removeItem, updateCantidad, clearCart, total, itemCount }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart debe usarse dentro de CartProvider");
  return ctx;
}
