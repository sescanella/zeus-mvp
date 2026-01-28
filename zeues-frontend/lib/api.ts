// /Users/sescanella/Proyectos/ZEUES-by-KM/zeues-frontend/lib/api.ts

// ============= IMPORTS =============
import {
  Worker,
  Spool,
  ActionPayload,
  ActionResponse,
  BatchActionRequest,
  BatchActionResponse,
  TomarRequest,
  PausarRequest,
  CompletarRequest,
  BatchTomarRequest,
  OccupationResponse,
  BatchOccupationResponse
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
 * console.log(workers); // [{id: 93, nombre: "Juan", apellido: "Pérez", activo: true, nombre_completo: "JP(93)"}]
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
 * const spools = await getSpoolsParaCompletar('ARM', 'JP(93)');
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0.1, armador: "JP(93)", ...}]
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
 * @deprecated Use tomarOcupacion() instead (v3.0 endpoint with Redis locks, optimistic versioning, and Estado_Detalle tracking)
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
  console.warn('⚠️ iniciarAccion() is deprecated. Migrate to tomarOcupacion() for v3.0 features (Redis locks, optimistic versioning, Estado_Detalle tracking).');
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
 * @deprecated Use completarOcupacion() instead (v3.0 endpoint with Redis lock release and Estado_Detalle updates)
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
 *   console.error(error.message); // "Solo JP(93) puede completar esta acción..."
 * }
 */
export async function completarAccion(payload: ActionPayload): Promise<ActionResponse> {
  console.warn('⚠️ completarAccion() is deprecated. Migrate to completarOcupacion() for v3.0 features (Redis lock release, Estado_Detalle updates).');
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
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0.1, armador: "JP(93)", ...}]
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
 * @deprecated Use pausarOcupacion() instead (v3.0 endpoint - semantic difference: PAUSAR marks as "parcial (pausado)", CANCELAR reverts to PENDIENTE)
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
 *   console.error(error.message); // "Solo JP(93) puede cancelar esta acción."
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
  console.warn('⚠️ cancelarAccion() is deprecated. Migrate to pausarOcupacion() (v3.0 PAUSAR marks as "parcial (pausado)", CANCELAR reverts to PENDIENTE).');
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
// METROLOGIA OPERATIONS (Phase 5)
// ==========================================

/**
 * POST /api/metrologia/completar
 * Completes metrología inspection with binary resultado (APROBADO/RECHAZADO).
 *
 * Instant completion workflow - no occupation phase. Validates prerequisites:
 * - ARM and SOLD must be completed (fecha_armado != None AND fecha_soldadura != None)
 * - Spool must not be occupied (ocupado_por = None)
 * - Metrología must be PENDIENTE (not already completed)
 *
 * @param tagSpool - TAG_SPOOL identifier
 * @param workerId - ID numérico del trabajador
 * @param resultado - Binary resultado: 'APROBADO' or 'RECHAZADO'
 * @returns Promise<{message: string, tag_spool: string, resultado: string}>
 * @throws Error if:
 *   - 404: Spool or worker not found
 *   - 400: Invalid data or prerequisites not met
 *   - 409: Spool is occupied by another worker
 *   - 403: Worker not authorized (missing Metrologia role)
 *   - 422: Invalid resultado value
 *
 * @example
 * // Successful approval
 * const result = await completarMetrologia('MK-123', 95, 'APROBADO');
 * console.log(result.message); // "Metrología completada: APROBADO"
 *
 * @example
 * // Rejection
 * const result = await completarMetrologia('MK-456', 95, 'RECHAZADO');
 * console.log(result.message); // "Metrología completada: RECHAZADO - Pendiente reparación"
 *
 * @example
 * // Error 409 - occupied spool
 * try {
 *   await completarMetrologia('MK-789', 95, 'APROBADO');
 * } catch (error) {
 *   console.error(error.message); // "Spool ocupado por otro trabajador"
 * }
 */
export async function completarMetrologia(
  tagSpool: string,
  workerId: number,
  resultado: 'APROBADO' | 'RECHAZADO'
): Promise<{ message: string; tag_spool: string; resultado: string }> {
  try {
    const res = await fetch(`${API_URL}/api/metrologia/completar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tag_spool: tagSpool,
        worker_id: workerId,
        resultado: resultado
      })
    });

    // Handle specific error codes
    if (res.status === 409) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Spool ocupado por otro trabajador. Intenta más tarde.');
    }

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Spool o trabajador no encontrado.');
    }

    if (res.status === 403) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'No tienes autorización para realizar metrología.');
    }

    if (res.status === 400) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Error de validación. Verifica los datos.');
    }

    if (res.status === 422) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Resultado inválido. Debe ser APROBADO o RECHAZADO.');
    }

    return await handleResponse<{ message: string; tag_spool: string; resultado: string }>(res);
  } catch (error) {
    console.error('completarMetrologia error:', error);
    throw error;
  }
}

// ==========================================
// REPARACION OPERATIONS (Phase 6)
// ==========================================

/**
 * GET /api/spools/reparacion
 * Obtiene spools RECHAZADO disponibles para reparación.
 *
 * Returns spools where estado_detalle contains "RECHAZADO" or "BLOQUEADO".
 * Skips occupied spools (ocupado_por != None).
 * For each spool:
 * - Parses cycle count from Estado_Detalle
 * - Checks if blocked (cycle >= 3)
 * - Includes fecha_rechazo (from Fecha_QC_Metrologia)
 *
 * @returns Promise with:
 *   - spools: Array of RECHAZADO/BLOQUEADO spools
 *   - total: Total count
 *   - bloqueados: Count of BLOQUEADO spools
 *   - filtro_aplicado: Description
 * @throws Error si falla request
 *
 * @example
 * const result = await getSpoolsReparacion();
 * console.log(result);
 * // {
 * //   spools: [
 * //     { tag_spool: "MK-123", cycle: 2, bloqueado: false, ... },
 * //     { tag_spool: "MK-456", cycle: 3, bloqueado: true, ... }
 * //   ],
 * //   total: 2,
 * //   bloqueados: 1
 * // }
 */
export async function getSpoolsReparacion(): Promise<{
  spools: Array<{
    tag_spool: string;
    estado_detalle: string;
    fecha_rechazo: string;
    cycle: number;
    bloqueado: boolean;
  }>;
  total: number;
  bloqueados: number;
  filtro_aplicado: string;
}> {
  try {
    const url = `${API_URL}/api/spools/reparacion`;
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    return await handleResponse<{
      spools: Array<{
        tag_spool: string;
        estado_detalle: string;
        fecha_rechazo: string;
        cycle: number;
        bloqueado: boolean;
      }>;
      total: number;
      bloqueados: number;
      filtro_aplicado: string;
    }>(res);
  } catch (error) {
    console.error('getSpoolsReparacion error:', error);
    throw new Error('No se pudieron cargar spools para reparación.');
  }
}

/**
 * POST /api/completar-reparacion
 * Completes repair work and returns spool to metrología queue.
 *
 * Validates:
 * - Spool exists and is EN_REPARACION
 * - Worker owns the spool (ownership validation)
 *
 * Updates:
 * - Ocupado_Por = None
 * - Fecha_Ocupacion = None
 * - Estado_Detalle = "PENDIENTE_METROLOGIA"
 *
 * @param payload - Datos de la acción (worker_id, tag_spool)
 * @returns Promise with success message and estado_detalle
 * @throws Error if:
 *   - 404: Spool not found
 *   - 400: Spool not EN_REPARACION
 *   - 403: Worker doesn't own the spool or spool is BLOQUEADO
 *
 * @example
 * const result = await completarReparacion({
 *   worker_id: 93,
 *   operacion: 'REPARACION',
 *   tag_spool: 'MK-123'
 * });
 * console.log(result.message); // "Reparación completada para spool MK-123 - devuelto a metrología"
 */
export async function completarReparacion(payload: {
  tag_spool: string;
  worker_id: number;
  worker_nombre?: string;
}): Promise<unknown> {
  try {
    const res = await fetch(`${API_URL}/api/completar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.status === 403) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Spool bloqueado - contactar supervisor');
    }

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Spool no encontrado.');
    }

    if (res.status === 400) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Error de validación. Verifica los datos.');
    }

    return await handleResponse<unknown>(res);
  } catch (error) {
    console.error('completarReparacion error:', error);
    throw error;
  }
}

/**
 * POST /api/tomar-reparacion
 * Worker takes RECHAZADO spool for repair.
 *
 * @param payload - Datos de la acción (worker_id, tag_spool)
 * @returns Promise with success message
 * @throws Error if spool BLOQUEADO (HTTP 403) or not available
 */
export async function tomarReparacion(payload: {
  tag_spool: string;
  worker_id: number;
}): Promise<unknown> {
  try {
    const res = await fetch(`${API_URL}/api/tomar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.status === 403) {
      const errorData = await res.json();
      throw new Error(errorData.message || 'Spool bloqueado - contactar supervisor');
    }

    return await handleResponse<unknown>(res);
  } catch (error) {
    console.error('tomarReparacion error:', error);
    throw error;
  }
}

/**
 * POST /api/pausar-reparacion
 * Worker pauses repair work and releases occupation.
 */
export async function pausarReparacion(payload: {
  tag_spool: string;
  worker_id: number;
}): Promise<unknown> {
  try {
    const res = await fetch(`${API_URL}/api/pausar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return await handleResponse<unknown>(res);
  } catch (error) {
    console.error('pausarReparacion error:', error);
    throw error;
  }
}

/**
 * POST /api/cancelar-reparacion
 * Worker cancels repair work and returns spool to RECHAZADO.
 */
export async function cancelarReparacion(payload: {
  tag_spool: string;
  worker_id: number;
}): Promise<unknown> {
  try {
    const res = await fetch(`${API_URL}/api/cancelar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return await handleResponse<unknown>(res);
  } catch (error) {
    console.error('cancelarReparacion error:', error);
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
 * @deprecated Use tomarOcupacionBatch() instead (v3.0 endpoint with Redis locks per spool and English response field names)
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
  console.warn('⚠️ iniciarAccionBatch() is deprecated. Migrate to tomarOcupacionBatch() for v3.0 features (Redis locks per spool, English response field names).');
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
 * @deprecated Use individual completarOcupacion() calls with Promise.allSettled() instead (v3.0 requires fecha_operacion per spool)
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
  console.warn('⚠️ completarAccionBatch() is deprecated. Migrate to individual completarOcupacion() calls with Promise.allSettled() (v3.0 requires fecha_operacion per spool).');
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
 * @deprecated Use individual pausarOcupacion() calls with Promise.allSettled() instead (v3.0 PAUSAR semantic: marks as "parcial (pausado)", not reverted to PENDIENTE)
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
  console.warn('⚠️ cancelarAccionBatch() is deprecated. Migrate to individual pausarOcupacion() calls with Promise.allSettled() (v3.0 PAUSAR marks as "parcial (pausado)", CANCELAR reverts to PENDIENTE).');
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

// ==========================================
// OCCUPATION v3.0 OPERATIONS (Redis locks + State Machine)
// ==========================================

/**
 * POST /api/occupation/tomar (v3.0)
 * Toma un spool con lock Redis y actualiza columnas de ocupación.
 *
 * Atomically acquires Redis lock and updates Ocupado_Por/Fecha_Ocupacion/Version/Estado_Detalle
 * in Operaciones sheet. Prevents concurrent TOMAR on same spool.
 *
 * NEW v3.0 features vs v2.1 iniciarAccion:
 * - Redis lock with ownership token (prevents race conditions)
 * - Optimistic locking with Version column
 * - Estado_Detalle tracking ("ARM en progreso", etc.)
 * - Requires worker_nombre in all requests (format: "INICIALES(ID)")
 *
 * @param request - TomarRequest with tag_spool, worker_id, worker_nombre, operacion
 * @returns Promise<OccupationResponse> with success status (ONLY 3 fields)
 * @throws Error if:
 *   - 409 CONFLICT: Spool already occupied by another worker (LOC-04 requirement)
 *   - 404 NOT FOUND: Spool not found
 *   - 400 BAD REQUEST: Prerequisites not met (e.g., missing Fecha_Materiales)
 *   - 503 SERVICE UNAVAILABLE: Sheets update failed
 *
 * @example
 * const result = await tomarOcupacion({
 *   tag_spool: 'MK-1335-CW-25238-011',
 *   worker_id: 93,
 *   worker_nombre: 'MR(93)',
 *   operacion: 'ARM'
 * });
 * console.log(result);
 * // { success: true, tag_spool: "MK-1335-CW-25238-011", message: "Spool tomado por MR(93)" }
 *
 * @example
 * // Error 409 CONFLICT (race condition)
 * try {
 *   await tomarOcupacion({
 *     tag_spool: 'MK-123',
 *     worker_id: 93,
 *     worker_nombre: 'MR(93)',
 *     operacion: 'ARM'
 *   });
 * } catch (error) {
 *   console.error(error.message); // "Spool ocupado por otro trabajador: JP(94)"
 * }
 */
export async function tomarOcupacion(request: TomarRequest): Promise<OccupationResponse> {
  try {
    const res = await fetch(`${API_URL}/api/occupation/tomar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    // v3.0 specific error handling BEFORE generic handleResponse
    if (res.status === 409) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Spool ocupado por otro trabajador. Intenta más tarde.');
    }

    if (res.status === 400) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Requisitos no cumplidos. Verifica el spool.');
    }

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Spool o trabajador no encontrado.');
    }

    if (res.status === 503) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Error al actualizar Google Sheets. Intenta nuevamente.');
    }

    return await handleResponse<OccupationResponse>(res);
  } catch (error) {
    console.error('tomarOcupacion error:', error);
    throw error;
  }
}

/**
 * POST /api/occupation/pausar (v3.0)
 * Pausa trabajo en un spool y libera el lock Redis.
 *
 * Verifies worker owns the lock, marks spool as "ARM parcial (pausado)"
 * or "SOLD parcial (pausado)", clears occupation, and releases Redis lock.
 *
 * SEMANTIC DIFFERENCE vs v2.1 cancelarAccion:
 * - PAUSAR (v3.0): Marks as "parcial (pausado)" - work can be resumed
 * - CANCELAR (v2.1): Reverts to PENDIENTE - work is completely undone
 *
 * @param request - PausarRequest with tag_spool, worker_id, worker_nombre
 * @returns Promise<OccupationResponse> with success status
 * @throws Error if:
 *   - 403 FORBIDDEN: Worker doesn't own the lock
 *   - 404 NOT FOUND: Spool not found
 *   - 410 GONE: Lock expired (worker took too long)
 *   - 503 SERVICE UNAVAILABLE: Sheets update failed
 *
 * @example
 * const result = await pausarOcupacion({
 *   tag_spool: 'MK-1335-CW-25238-011',
 *   worker_id: 93,
 *   worker_nombre: 'MR(93)'
 * });
 * console.log(result.message); // "Spool pausado exitosamente"
 */
export async function pausarOcupacion(request: PausarRequest): Promise<OccupationResponse> {
  try {
    const res = await fetch(`${API_URL}/api/occupation/pausar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    // v3.0 specific error handling
    if (res.status === 403) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'No estás autorizado para pausar este spool. Solo quien lo tomó puede pausarlo.');
    }

    if (res.status === 410) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'La operación expiró. Por favor toma el spool nuevamente.');
    }

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Spool no encontrado.');
    }

    if (res.status === 503) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Error al actualizar Google Sheets. Intenta nuevamente.');
    }

    return await handleResponse<OccupationResponse>(res);
  } catch (error) {
    console.error('pausarOcupacion error:', error);
    throw error;
  }
}

/**
 * POST /api/occupation/completar (v3.0)
 * Completa trabajo en un spool y libera el lock Redis.
 *
 * Verifies worker owns the lock, updates fecha_armado or fecha_soldadura,
 * clears occupation, and releases Redis lock.
 *
 * NEW v3.0 requirements vs v2.1 completarAccion:
 * - fecha_operacion is REQUIRED (YYYY-MM-DD format)
 * - v2.1 used timestamp (ISO 8601) - v3.0 uses date only
 *
 * @param request - CompletarRequest with tag_spool, worker_id, worker_nombre, fecha_operacion
 * @returns Promise<OccupationResponse> with success status
 * @throws Error if:
 *   - 403 FORBIDDEN: Worker doesn't own the lock
 *   - 404 NOT FOUND: Spool not found
 *   - 410 GONE: Lock expired
 *   - 503 SERVICE UNAVAILABLE: Sheets update failed
 *
 * @example
 * const result = await completarOcupacion({
 *   tag_spool: 'MK-1335-CW-25238-011',
 *   worker_id: 93,
 *   worker_nombre: 'MR(93)',
 *   fecha_operacion: '2026-01-28'  // YYYY-MM-DD format
 * });
 * console.log(result.message); // "Operación completada exitosamente"
 */
export async function completarOcupacion(request: CompletarRequest): Promise<OccupationResponse> {
  try {
    const res = await fetch(`${API_URL}/api/occupation/completar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    // v3.0 specific error handling
    if (res.status === 403) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'No estás autorizado para completar este spool. Solo quien lo tomó puede completarlo.');
    }

    if (res.status === 410) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'La operación expiró. Por favor toma el spool nuevamente.');
    }

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Spool no encontrado.');
    }

    if (res.status === 503) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Error al actualizar Google Sheets. Intenta nuevamente.');
    }

    return await handleResponse<OccupationResponse>(res);
  } catch (error) {
    console.error('completarOcupacion error:', error);
    throw error;
  }
}

/**
 * POST /api/occupation/batch-tomar (v3.0)
 * Toma múltiples spools en batch (hasta 50).
 *
 * Processes each spool independently. Returns detailed results showing
 * which spools succeeded and which failed.
 *
 * Partial success is allowed: If 7 of 10 spools succeed, the operation
 * returns 200 OK with details about successes and failures.
 *
 * NEW v3.0 features:
 * - Response uses English field names (succeeded/failed) NOT Spanish (exitosos/fallidos)
 * - Each spool gets individual Redis lock + ownership token
 * - Atomic operations with optimistic locking per spool
 *
 * @param request - BatchTomarRequest with tag_spools list (max 50)
 * @returns Promise<BatchOccupationResponse> with total, succeeded, failed counts and details
 * @throws Error if batch > 50, batch empty, or network error
 *
 * @example
 * const result = await tomarOcupacionBatch({
 *   tag_spools: ['MK-001', 'MK-002', 'MK-003'],
 *   worker_id: 93,
 *   worker_nombre: 'MR(93)',
 *   operacion: 'ARM'
 * });
 * console.log(result);
 * // {
 * //   total: 3,
 * //   succeeded: 2,  // English!
 * //   failed: 1,     // English!
 * //   details: [
 * //     { success: true, tag_spool: "MK-001", message: "Spool tomado exitosamente" },
 * //     { success: true, tag_spool: "MK-002", message: "Spool tomado exitosamente" },
 * //     { success: false, tag_spool: "MK-003", message: "Spool ocupado por JP(94)" }
 * //   ]
 * // }
 */
export async function tomarOcupacionBatch(request: BatchTomarRequest): Promise<BatchOccupationResponse> {
  try {
    // Validación frontend
    if (request.tag_spools.length === 0) {
      throw new Error('Debes seleccionar al menos 1 spool.');
    }
    if (request.tag_spools.length > 50) {
      throw new Error('Máximo 50 spools por operación batch.');
    }

    const res = await fetch(`${API_URL}/api/occupation/batch-tomar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });

    return await handleResponse<BatchOccupationResponse>(res);
  } catch (error) {
    console.error('tomarOcupacionBatch error:', error);
    throw error;
  }
}
