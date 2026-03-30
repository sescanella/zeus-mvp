import { WifiOff, Search, CircleAlert, CircleX, type LucideIcon } from 'lucide-react';

type ErrorType = 'network' | 'not-found' | 'validation' | 'forbidden' | 'server' | 'generic';

interface ErrorMessageProps {
  message: string;
  type?: ErrorType;
  onRetry?: () => void;
}

interface ErrorConfig {
  icon: LucideIcon;
  title: string;
  bgColor: string;
  borderColor: string;
  textColor: string;
  showRetry: boolean;
}

/**
 * Componente de mensaje de error con iconos Lucide y estilos según tipo
 *
 * @param message - Mensaje de error a mostrar
 * @param type - Tipo de error (network, not-found, validation, forbidden, server, generic)
 * @param onRetry - Callback opcional para botón de reintentar (solo para errores recuperables)
 */
export function ErrorMessage({ message, type = 'generic', onRetry }: ErrorMessageProps) {
  // Configuración de iconos Lucide y colores según tipo de error
  const config: Record<ErrorType, ErrorConfig> = {
    network: {
      icon: WifiOff,
      title: 'Error de Conexión',
      bgColor: 'bg-orange-900/20',
      borderColor: 'border-orange-500/40',
      textColor: 'text-orange-400',
      showRetry: true,
    },
    'not-found': {
      icon: Search,
      title: 'No Encontrado',
      bgColor: 'bg-blue-900/20',
      borderColor: 'border-blue-500/40',
      textColor: 'text-blue-400',
      showRetry: false,
    },
    validation: {
      icon: CircleAlert,
      title: 'Error de Validación',
      bgColor: 'bg-yellow-900/20',
      borderColor: 'border-yellow-500/40',
      textColor: 'text-yellow-400',
      showRetry: false,
    },
    forbidden: {
      icon: CircleX,
      title: 'No Autorizado',
      bgColor: 'bg-red-900/20',
      borderColor: 'border-red-500/40',
      textColor: 'text-red-400',
      showRetry: false,
    },
    server: {
      icon: CircleX,
      title: 'Error del Servidor',
      bgColor: 'bg-red-900/20',
      borderColor: 'border-red-500/40',
      textColor: 'text-red-400',
      showRetry: true,
    },
    generic: {
      icon: CircleX,
      title: 'Error',
      bgColor: 'bg-red-900/20',
      borderColor: 'border-red-500/40',
      textColor: 'text-red-400',
      showRetry: false,
    },
  };

  const errorConfig = config[type];
  const shouldShowRetry = onRetry && errorConfig.showRetry;
  const IconComponent = errorConfig.icon;

  return (
    <div role="alert" className={`${errorConfig.bgColor} border ${errorConfig.borderColor} p-4`}>
      <div className="flex items-start gap-3">
        <IconComponent
          size={28}
          className={`${errorConfig.textColor} flex-shrink-0`}
          aria-label={errorConfig.title}
        />
        <div className="flex-1">
          <h3 className={`${errorConfig.textColor} font-mono font-black text-base tracking-widest uppercase mb-1`}>
            {errorConfig.title}
          </h3>
          <p className={`${errorConfig.textColor} font-mono text-sm`}>
            {message}
          </p>
          {shouldShowRetry && (
            <button
              onClick={onRetry}
              className="mt-3 px-4 py-2 border-2 border-white text-white font-mono font-black text-sm cursor-pointer active:bg-white active:text-zeues-navy transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset min-h-[44px]"
            >
              Reintentar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
