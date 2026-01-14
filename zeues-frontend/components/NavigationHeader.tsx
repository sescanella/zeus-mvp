import { CircleChevronLeft, CircleX } from 'lucide-react';

interface NavigationHeaderProps {
  title: string;
  onBack?: () => void;
  showCancel?: boolean;
  onCancel?: () => void;
}

/**
 * Componente de navegación consistente para páginas P2-P6
 *
 * Features:
 * - Botón "Volver" (izquierda) con CircleChevronLeft icon
 * - Título centrado (operación o página actual)
 * - Botón "Cancelar" (derecha) opcional con CircleX icon
 * - Mobile-first design (800×1280px tablets)
 * - Touch targets grandes (64px altura)
 *
 * @param title - Título de la página actual
 * @param onBack - Callback para botón "Volver" (opcional)
 * @param showCancel - Mostrar botón "Cancelar" (default: false)
 * @param onCancel - Callback para botón "Cancelar" (opcional)
 *
 * @example
 * // Con solo "Volver"
 * <NavigationHeader
 *   title="Seleccionar Operación"
 *   onBack={() => router.back()}
 * />
 *
 * @example
 * // Con "Volver" y "Cancelar"
 * <NavigationHeader
 *   title="Seleccionar Spool"
 *   onBack={() => router.back()}
 *   showCancel={true}
 *   onCancel={() => router.push('/')}
 * />
 */
export function NavigationHeader({
  title,
  onBack,
  showCancel = false,
  onCancel,
}: NavigationHeaderProps) {
  return (
    <header className="bg-white border-b-2 border-km-gray-light px-6 py-4 sticky top-0 z-10 shadow-sm">
      <div className="max-w-2xl mx-auto flex items-center justify-between h-16">
        {/* Botón Volver (izquierda) */}
        {onBack ? (
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-zeues-blue hover:text-zeues-blue-600
                     active:scale-95 transition-all h-12 px-4 -ml-4 rounded-lg
                     hover:bg-km-gray-light/50"
            aria-label="Volver a la página anterior"
          >
            <CircleChevronLeft size={28} />
            <span className="font-semibold text-lg">Volver</span>
          </button>
        ) : (
          <div className="w-32" /> // Spacer para mantener título centrado
        )}

        {/* Título (centro) */}
        <h1 className="text-xl font-bold text-km-gray-text text-center flex-1 px-4">
          {title}
        </h1>

        {/* Botón Cancelar (derecha) */}
        {showCancel && onCancel ? (
          <button
            onClick={onCancel}
            className="flex items-center gap-2 text-red-600 hover:text-red-700
                     active:scale-95 transition-all h-12 px-4 -mr-4 rounded-lg
                     hover:bg-red-50"
            aria-label="Cancelar flujo y volver al inicio"
          >
            <span className="font-semibold text-lg">Cancelar</span>
            <CircleX size={28} />
          </button>
        ) : (
          <div className="w-32" /> // Spacer para mantener título centrado
        )}
      </div>
    </header>
  );
}
