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
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      textColor: 'text-orange-700',
      showRetry: true,
    },
    'not-found': {
      icon: Search,
      title: 'No Encontrado',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-700',
      showRetry: false,
    },
    validation: {
      icon: CircleAlert,
      title: 'Error de Validación',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-700',
      showRetry: false,
    },
    forbidden: {
      icon: CircleX,
      title: 'No Autorizado',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-700',
      showRetry: false,
    },
    server: {
      icon: CircleX,
      title: 'Error del Servidor',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-700',
      showRetry: true,
    },
    generic: {
      icon: CircleX,
      title: 'Error',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-700',
      showRetry: false,
    },
  };

  const errorConfig = config[type];
  const shouldShowRetry = onRetry && errorConfig.showRetry;
  const IconComponent = errorConfig.icon;

  return (
    <div className={`${errorConfig.bgColor} border ${errorConfig.borderColor} rounded-lg p-4`}>
      <div className="flex items-start gap-3">
        <IconComponent
          size={28}
          className={`${errorConfig.textColor} flex-shrink-0`}
          aria-label={errorConfig.title}
        />
        <div className="flex-1">
          <h3 className={`${errorConfig.textColor} font-bold text-lg mb-1`}>
            {errorConfig.title}
          </h3>
          <p className={`${errorConfig.textColor} font-medium`}>
            {message}
          </p>
          {shouldShowRetry && (
            <button
              onClick={onRetry}
              className={`mt-3 ${errorConfig.textColor} underline text-sm font-semibold hover:no-underline`}
            >
              Reintentar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
