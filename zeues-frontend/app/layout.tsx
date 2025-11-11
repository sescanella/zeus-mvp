import type { Metadata } from 'next';
import './globals.css';
import { AppProvider } from '@/lib/context';

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
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
