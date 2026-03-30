import type { Metadata, Viewport } from 'next';
import { JetBrains_Mono } from 'next/font/google';
import './globals.css';

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'ZEUS by KM',
  description: 'Sistema de trazabilidad para manufactura de cañerías',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // WCAG 2.1 AA Compliance: Allow zoom for visually impaired users
  // maximumScale: 1,  // REMOVED: Do not restrict zoom
  // userScalable: false,  // REMOVED: Allow pinch-to-zoom on mobile
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={jetbrainsMono.variable}>
      <body>
        {children}
      </body>
    </html>
  );
}
