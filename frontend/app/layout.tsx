import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ICO Distribuidora — Sistema de Gestión de Ventas",
  description: "Sistema de recomendaciones y gestión de ventas para ICO Distribuidora",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${geistSans.variable} h-full`}>
      <body className="h-full antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
