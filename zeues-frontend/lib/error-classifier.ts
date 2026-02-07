/**
 * Error Classification Utility for ZEUES Manufacturing App
 *
 * Centralizes error handling logic and provides tablet-friendly error messages.
 * Used by P4 (seleccionar-spool) and P5 (confirmar) to classify API errors.
 */

export type ErrorType = 'network' | 'validation' | 'forbidden' | 'server' | 'conflict' | 'generic';

export interface ClassifiedError {
  type: ErrorType;
  userMessage: string;
  technicalMessage?: string;
  shouldRetry: boolean;
  retryDelay?: number;  // ms to wait before retry
}

/**
 * Classify API errors into user-friendly categories.
 *
 * Prioritizes clear, actionable messages for tablet operators.
 *
 * @param error - Error from API call (unknown type for flexibility)
 * @returns ClassifiedError with type, message, and retry guidance
 *
 * @example
 * const classified = classifyApiError(apiError);
 * if (classified.shouldRetry) {
 *   setTimeout(() => retryAction(), classified.retryDelay || 0);
 * }
 */
export function classifyApiError(error: unknown): ClassifiedError {
  // Network errors (fetch failed, no response)
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      type: 'network',
      userMessage: 'Sin conexión al servidor. Verifica WiFi o reinicia la tablet.',
      technicalMessage: error.message,
      shouldRetry: true,
      retryDelay: 2000,
    };
  }

  // API response errors (structured error objects)
  if (typeof error === 'object' && error !== null && 'status' in error) {
    const apiError = error as { status: number; message?: string; detail?: string };

    switch (apiError.status) {
      case 400:
        // Validation errors (invalid data)
        return {
          type: 'validation',
          userMessage: apiError.detail || apiError.message || 'Datos inválidos. Verifica la selección.',
          shouldRetry: false,
        };

      case 403:
        // Forbidden (ownership, permissions)
        return {
          type: 'forbidden',
          userMessage: apiError.detail || 'No tienes permiso para esta acción.',
          shouldRetry: false,
        };

      case 404:
        // Not found (spool doesn't exist)
        return {
          type: 'validation',
          userMessage: 'Spool no encontrado. Verifica el TAG.',
          shouldRetry: false,
        };

      case 409:
        // Conflict (concurrency, version mismatch)
        return {
          type: 'conflict',
          userMessage: 'Otro usuario modificó este spool. Recarga la página.',
          technicalMessage: apiError.detail || apiError.message,
          shouldRetry: true,
          retryDelay: 1000,
        };

      case 500:
      case 502:
      case 503:
      case 504:
        // Server errors (Google Sheets timeout, backend crash)
        return {
          type: 'server',
          userMessage: 'Error del servidor. Espera unos segundos e intenta de nuevo.',
          technicalMessage: apiError.detail || apiError.message,
          shouldRetry: true,
          retryDelay: 3000,
        };

      default:
        // Unknown HTTP error
        return {
          type: 'generic',
          userMessage: `Error ${apiError.status}. Contacta al supervisor.`,
          technicalMessage: apiError.detail || apiError.message,
          shouldRetry: false,
        };
    }
  }

  // Unstructured errors (strings, unknown objects)
  const errorMessage = error instanceof Error ? error.message : String(error);
  return {
    type: 'generic',
    userMessage: 'Error inesperado. Contacta al supervisor.',
    technicalMessage: errorMessage,
    shouldRetry: false,
  };
}

