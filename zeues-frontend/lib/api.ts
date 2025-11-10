// /Users/sescanella/Proyectos/ZEUES-by-KM/zeues-frontend/lib/api.ts

// ============= IMPORTS =============
import { Worker, Spool, ActionPayload, ActionResponse } from './types';

// ============= CONSTANTS =============
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============= HELPER FUNCTIONS =============

/**
 * Helper para manejar respuestas HTTP de forma consistente.
 * Lanza error si response.ok === false.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.message || `Error ${response.status}: ${response.statusText}`;
    throw new Error(message);
  }
  return response.json();
}

// ============= API FUNCTIONS =============

/**
 * GET /api/workers
 * Obtiene lista de trabajadores activos.
 *
 * @returns Promise<Worker[]> - Array de trabajadores activos
 * @throws Error si falla la request o backend no disponible
 *
 * @example
 * const workers = await getWorkers();
 * console.log(workers); // [{nombre: "Juan", apellido: "Pérez", activo: true, nombre_completo: "Juan Pérez"}]
 */
export async function getWorkers(): Promise<Worker[]> {
  try {
    const res = await fetch(`${API_URL}/api/workers`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ workers: Worker[], total: number }>(res);
    return data.workers;
  } catch (error) {
    console.error('getWorkers error:', error);
    throw new Error('No se pudieron cargar los trabajadores. Verifica tu conexión.');
  }
}

/**
 * GET /api/spools/iniciar?operacion={ARM|SOLD}
 * Obtiene spools disponibles para INICIAR (V/W=0, dependencias OK).
 *
 * @param operacion - Tipo de operación ("ARM" o "SOLD")
 * @returns Promise<Spool[]> - Array de spools elegibles para iniciar
 * @throws Error si operación inválida o falla request
 *
 * @example
 * const spools = await getSpoolsParaIniciar('ARM');
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0, sold: 0, ...}]
 */
export async function getSpoolsParaIniciar(operacion: 'ARM' | 'SOLD'): Promise<Spool[]> {
  try {
    const url = `${API_URL}/api/spools/iniciar?operacion=${operacion}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ spools: Spool[], total: number, filtro_aplicado: string }>(res);
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaIniciar error:', error);
    throw new Error(`No se pudieron cargar spools para iniciar ${operacion}.`);
  }
}

/**
 * GET /api/spools/completar?operacion={ARM|SOLD}&worker_nombre={nombre}
 * Obtiene spools del trabajador para COMPLETAR (V/W=0.1, filtro ownership).
 *
 * @param operacion - Tipo de operación ("ARM" o "SOLD")
 * @param workerNombre - Nombre completo del trabajador (será URL encoded)
 * @returns Promise<Spool[]> - Array de spools propios del trabajador
 * @throws Error si operación inválida o falla request
 *
 * @example
 * const spools = await getSpoolsParaCompletar('ARM', 'Juan Pérez');
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0.1, armador: "Juan Pérez", ...}]
 */
export async function getSpoolsParaCompletar(
  operacion: 'ARM' | 'SOLD',
  workerNombre: string
): Promise<Spool[]> {
  try {
    // URL encode del nombre para manejar espacios y tildes
    const encodedWorker = encodeURIComponent(workerNombre);
    const url = `${API_URL}/api/spools/completar?operacion=${operacion}&worker_nombre=${encodedWorker}`;

    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ spools: Spool[], total: number, filtro_aplicado: string }>(res);
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaCompletar error:', error);
    throw new Error(`No se pudieron cargar tus spools de ${operacion}.`);
  }
}

/**
 * POST /api/iniciar-accion
 * Inicia una acción (marca V/W→0.1, guarda trabajador en BC/BE).
 *
 * @param payload - Datos de la acción (worker_nombre, operacion, tag_spool)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la operación
 * @throws Error si trabajador/spool no encontrado, ya iniciada, o dependencias no satisfechas
 *
 * @example
 * const result = await iniciarAccion({
 *   worker_nombre: 'Juan Pérez',
 *   operacion: 'ARM',
 *   tag_spool: 'MK-1335-CW-25238-011'
 * });
 * console.log(result.message); // "Acción ARM iniciada exitosamente..."
 */
export async function iniciarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/iniciar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return await handleResponse<ActionResponse>(res);
  } catch (error) {
    console.error('iniciarAccion error:', error);
    // Re-throw para que el componente maneje el error
    throw error;
  }
}

/**
 * POST /api/completar-accion
 * Completa una acción (marca V/W→1.0, guarda fecha en BB/BD).
 *
 * CRÍTICO: Solo quien inició (BC/BE) puede completar. Si otro trabajador intenta,
 * backend retorna 403 FORBIDDEN y esta función lanza error con mensaje específico.
 *
 * @param payload - Datos de la acción (worker_nombre, operacion, tag_spool, timestamp?)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la operación
 * @throws Error si no autorizado (403), no iniciada, trabajador/spool no encontrado
 *
 * @example
 * // Caso exitoso (mismo trabajador que inició)
 * const result = await completarAccion({
 *   worker_nombre: 'Juan Pérez',
 *   operacion: 'ARM',
 *   tag_spool: 'MK-1335-CW-25238-011'
 * });
 * console.log(result.message); // "Acción ARM completada exitosamente..."
 *
 * @example
 * // Caso error 403 (trabajador diferente)
 * try {
 *   await completarAccion({
 *     worker_nombre: 'María López', // Diferente al que inició
 *     operacion: 'ARM',
 *     tag_spool: 'MK-1335-CW-25238-011'
 *   });
 * } catch (error) {
 *   console.error(error.message); // "Solo Juan Pérez puede completar esta acción..."
 * }
 */
export async function completarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/completar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    // Manejo especial para 403 FORBIDDEN (ownership validation)
    if (res.status === 403) {
      const errorData = await res.json();
      const message = errorData.message || 'No estás autorizado para completar esta acción. Solo quien la inició puede completarla.';
      throw new Error(message);
    }

    return await handleResponse<ActionResponse>(res);
  } catch (error) {
    console.error('completarAccion error:', error);
    // Re-throw para que el componente maneje el error
    throw error;
  }
}

/**
 * GET /api/health
 * Health check del backend y conectividad Google Sheets.
 *
 * @returns Promise<{status: string, sheets_connection: string}> - Estado del sistema
 * @throws Error si backend no disponible
 *
 * @example
 * const health = await checkHealth();
 * console.log(health); // {status: "healthy", sheets_connection: "ok", ...}
 */
export async function checkHealth(): Promise<{ status: string, sheets_connection: string }> {
  try {
    const res = await fetch(`${API_URL}/api/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    return await handleResponse<{ status: string, sheets_connection: string }>(res);
  } catch (error) {
    console.error('checkHealth error:', error);
    throw new Error('No se pudo verificar el estado del sistema.');
  }
}
