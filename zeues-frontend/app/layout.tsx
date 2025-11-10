import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ZEUES - Trazabilidad',
  description: 'Sistema de trazabilidad para manufactura de cañerías',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        {/* TODO DÍA 3: Agregar AppProvider wrapping children */}
        {children}
      </body>
    </html>
  );
}
