// /Users/sescanella/Proyectos/ZEUES-by-KM/zeues-frontend/lib/api.ts

// ============= IMPORTS =============
import {
  Worker,
  Spool,
  ActionPayload,
  ActionResponse,
  BatchActionRequest,
  BatchActionResponse
} from './types';

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
 * @param payload - Datos de la acción (worker_id, operacion, tag_spool)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la operación
 * @throws Error si trabajador/spool no encontrado, ya iniciada, o dependencias no satisfechas
 *
 * @example
 * const result = await iniciarAccion({
 *   worker_id: 93,
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
 * @param payload - Datos de la acción (worker_id, operacion, tag_spool, timestamp?)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la operación
 * @throws Error si no autorizado (403), no iniciada, trabajador/spool no encontrado
 *
 * @example
 * // Caso exitoso (mismo trabajador que inició)
 * const result = await completarAccion({
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   tag_spool: 'MK-1335-CW-25238-011'
 * });
 * console.log(result.message); // "Acción ARM completada exitosamente..."
 *
 * @example
 * // Caso error 403 (trabajador diferente)
 * try {
 *   await completarAccion({
 *     worker_id: 94, // Diferente al que inició (93)
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

/**
 * GET /api/workers/{workerId}/roles
 * Obtiene los roles operativos asignados a un trabajador.
 *
 * @param workerId - ID numérico del trabajador
 * @returns Promise<string[]> - Array de roles ("Armador", "Soldador", "Metrologia", etc.)
 * @throws Error si trabajador no encontrado o falla request
 *
 * @example
 * const roles = await getWorkerRoles(93);
 * console.log(roles); // ["Armador", "Soldador"]
 */
export async function getWorkerRoles(workerId: number): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/workers/${workerId}/roles`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ roles: string[] }>(res);
    return data.roles;
  } catch (error) {
    console.error('getWorkerRoles error:', error);
    throw new Error('No se pudieron cargar los roles del trabajador.');
  }
}

/**
 * GET /api/spools/cancelar?operacion={ARM|SOLD}&worker_id={id}
 * Obtiene spools EN_PROGRESO (estado=0.1) del trabajador para CANCELAR.
 *
 * Similar a getSpoolsParaCompletar pero semánticamente diferente:
 * - COMPLETAR: Finalizar acción (0.1 → 1.0)
 * - CANCELAR: Revertir acción (0.1 → 0)
 *
 * @param operacion - Tipo de operación ("ARM" o "SOLD")
 * @param workerId - ID numérico del trabajador
 * @returns Promise<Spool[]> - Array de spools propios EN_PROGRESO
 * @throws Error si operación inválida, worker no encontrado, o falla request
 *
 * @example
 * const spools = await getSpoolsParaCancelar('ARM', 93);
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0.1, armador: "Juan Pérez", ...}]
 */
export async function getSpoolsParaCancelar(
  operacion: 'ARM' | 'SOLD',
  workerId: number
): Promise<Spool[]> {
  try {
    const url = `${API_URL}/api/spools/cancelar?operacion=${operacion}&worker_id=${workerId}`;

    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ spools: Spool[], total: number, filtro_aplicado: string }>(res);
    return data.spools;
  } catch (error) {
    console.error('getSpoolsParaCancelar error:', error);
    throw new Error(`No se pudieron cargar spools cancelables de ${operacion}.`);
  }
}

/**
 * POST /api/cancelar-accion
 * Cancela una acción EN_PROGRESO (revierte estado 0.1 → 0, limpia worker asignado).
 *
 * CRÍTICO: Solo quien inició (BC/BE) puede cancelar. Si otro trabajador intenta,
 * backend retorna 403 FORBIDDEN. Solo spools con estado 0.1 pueden ser cancelados.
 *
 * Validaciones Backend:
 * - Spool existe
 * - Estado = 0.1 (EN_PROGRESO) - NO se puede cancelar estado 0 (PENDIENTE) o 1.0 (COMPLETADO)
 * - Worker es quien inició (ownership validation)
 *
 * Workflow:
 * 1. Validar puede cancelar
 * 2. UPDATE estado: 0.1 → 0 (volver a PENDIENTE)
 * 3. Limpiar worker asignado (BC/BE = null)
 * 4. Registrar evento CANCELAR en Metadata (CANCELAR_ARM, CANCELAR_SOLD)
 *
 * @param payload - Datos de la acción (worker_id, operacion, tag_spool)
 * @returns Promise<ActionResponse> - Respuesta con detalles de la cancelación
 * @throws Error si no autorizado (403), estado inválido (400), trabajador/spool no encontrado (404)
 *
 * @example
 * // Caso exitoso (mismo trabajador que inició)
 * const result = await cancelarAccion({
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   tag_spool: 'MK-1335-CW-25238-011'
 * });
 * console.log(result.message); // "Acción ARM cancelada. Spool vuelve a PENDIENTE."
 *
 * @example
 * // Caso error 403 (trabajador diferente)
 * try {
 *   await cancelarAccion({
 *     worker_id: 94, // Diferente al que inició
 *     operacion: 'ARM',
 *     tag_spool: 'MK-1335-CW-25238-011'
 *   });
 * } catch (error) {
 *   console.error(error.message); // "Solo Juan Pérez puede cancelar esta acción."
 * }
 *
 * @example
 * // Caso error 400 (estado inválido)
 * try {
 *   await cancelarAccion({
 *     worker_id: 93,
 *     operacion: 'ARM',
 *     tag_spool: 'MK-COMPLETADO' // Spool con estado 1.0
 *   });
 * } catch (error) {
 *   console.error(error.message); // "No se puede cancelar una acción completada."
 * }
 */
export async function cancelarAccion(payload: ActionPayload): Promise<ActionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/cancelar-accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    // Manejo especial para 403 FORBIDDEN (ownership validation)
    if (res.status === 403) {
      const errorData = await res.json();
      const message = errorData.message || 'No estás autorizado para cancelar esta acción. Solo quien la inició puede cancelarla.';
      throw new Error(message);
    }

    // Manejo especial para 400 BAD REQUEST (estado inválido)
    if (res.status === 400) {
      const errorData = await res.json();
      const message = errorData.message || 'No se puede cancelar esta acción. Verifica el estado del spool.';
      throw new Error(message);
    }

    return await handleResponse<ActionResponse>(res);
  } catch (error) {
    console.error('cancelarAccion error:', error);
    // Re-throw para que el componente maneje el error
    throw error;
  }
}

// ==========================================
// BATCH OPERATIONS (v2.0 Multiselect)
// ==========================================

/**
 * POST /api/iniciar-accion-batch
 * Inicia múltiples acciones simultáneamente (hasta 50 spools).
 *
 * Procesa cada spool individualmente. Si algunos spools fallan, continúa
 * procesando los restantes (manejo de errores parciales).
 *
 * Validaciones por spool:
 * - Trabajador existe y está activo
 * - Spool existe
 * - Operación está PENDIENTE (estado=0)
 * - Trabajador tiene rol necesario (v2.0)
 *
 * @param request - BatchActionRequest (worker_id, operacion, tag_spools[])
 * @returns Promise<BatchActionResponse> - Stats + resultados individuales
 * @throws Error si batch > 50, batch vacío, o error de red
 *
 * @example
 * const result = await iniciarAccionBatch({
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   tag_spools: ['MK-001', 'MK-002', 'MK-003']
 * });
 * console.log(result);
 * // { success: true, total: 3, exitosos: 3, fallidos: 0, resultados: [...] }
 */
export async function iniciarAccionBatch(
  request: BatchActionRequest
): Promise<BatchActionResponse> {
  try {
    // Validación frontend
    if (request.tag_spools.length === 0) {
      throw new Error('Debes seleccionar al menos 1 spool.');
    }
    if (request.tag_spools.length > 50) {
      throw new Error('Máximo 50 spools por operación batch.');
    }

    const res = await fetch(`${API_URL}/api/iniciar-accion-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    return await handleResponse<BatchActionResponse>(res);
  } catch (error) {
    console.error('iniciarAccionBatch error:', error);
    throw error;
  }
}

/**
 * POST /api/completar-accion-batch
 * Completa múltiples acciones EN_PROGRESO (hasta 50 spools).
 *
 * CRÍTICO: Valida ownership individualmente. Solo quien inició puede completar.
 * Si algunos spools fallan ownership validation, continúa con los restantes.
 *
 * Validaciones por spool:
 * - Trabajador existe y está activo
 * - Spool existe
 * - Operación EN_PROGRESO (estado=0.1)
 * - OWNERSHIP: worker_id debe coincidir con quien inició (403 si no)
 * - Trabajador tiene rol necesario (v2.0)
 *
 * @param request - BatchActionRequest (worker_id, operacion, tag_spools[], timestamp)
 * @returns Promise<BatchActionResponse> - Stats + resultados individuales (incluye ownership errors)
 * @throws Error si batch > 50, batch vacío, o error de red
 *
 * @example
 * const result = await completarAccionBatch({
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   tag_spools: ['MK-001', 'MK-002'],
 *   timestamp: new Date().toISOString()
 * });
 * // Posible partial success: exitosos=1, fallidos=1 (ownership error en MK-002)
 */
export async function completarAccionBatch(
  request: BatchActionRequest
): Promise<BatchActionResponse> {
  try {
    // Validación frontend
    if (request.tag_spools.length === 0) {
      throw new Error('Debes seleccionar al menos 1 spool.');
    }
    if (request.tag_spools.length > 50) {
      throw new Error('Máximo 50 spools por operación batch.');
    }

    const res = await fetch(`${API_URL}/api/completar-accion-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    return await handleResponse<BatchActionResponse>(res);
  } catch (error) {
    console.error('completarAccionBatch error:', error);
    throw error;
  }
}

/**
 * POST /api/cancelar-accion-batch
 * Cancela múltiples acciones EN_PROGRESO (hasta 50 spools).
 *
 * CRÍTICO: Valida ownership individualmente. Solo quien inició puede cancelar.
 * Revierte estado 0.1 → 0 (PENDIENTE) y limpia worker asignado.
 *
 * Validaciones por spool:
 * - Trabajador existe y está activo
 * - Spool existe
 * - Operación EN_PROGRESO (estado=0.1)
 * - OWNERSHIP: worker_id debe coincidir con quien inició (403 si no)
 * - Trabajador tiene rol necesario (v2.0)
 *
 * @param request - BatchActionRequest (worker_id, operacion, tag_spools[])
 * @returns Promise<BatchActionResponse> - Stats + resultados individuales (incluye ownership errors)
 * @throws Error si batch > 50, batch vacío, o error de red
 *
 * @example
 * const result = await cancelarAccionBatch({
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   tag_spools: ['MK-001', 'MK-002', 'MK-003']
 * });
 * console.log(result);
 * // { success: true, total: 3, exitosos: 3, fallidos: 0, resultados: [...] }
 */
export async function cancelarAccionBatch(
  request: BatchActionRequest
): Promise<BatchActionResponse> {
  try {
    // Validación frontend
    if (request.tag_spools.length === 0) {
      throw new Error('Debes seleccionar al menos 1 spool.');
    }
    if (request.tag_spools.length > 50) {
      throw new Error('Máximo 50 spools por operación batch.');
    }

    const res = await fetch(`${API_URL}/api/cancelar-accion-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    return await handleResponse<BatchActionResponse>(res);
  } catch (error) {
    console.error('cancelarAccionBatch error:', error);
    throw error;
  }
}
