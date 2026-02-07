// /Users/sescanella/Proyectos/ZEUES-by-KM/zeues-frontend/lib/api.ts

// ============= IMPORTS =============
import {
  Worker,
  Spool,
  ReparacionResponse,
  DisponiblesResponse,
  MetricasResponse,
  IniciarRequest,
  IniciarResponse,
  FinalizarRequest,
  FinalizarResponse
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
 * GET /api/spools/disponible?operacion={ARM|SOLD|REPARACION} (v3.0)
 * Obtiene spools DISPONIBLES para TOMAR (no ocupados, prerequisitos cumplidos).
 *
 * Usado por P4 cuando tipo=tomar. Muestra spools que el trabajador puede tomar.
 *
 * @param operacion - Tipo de operación ("ARM", "SOLD", or "REPARACION")
 * @returns Promise<Spool[]> - Array de spools disponibles para tomar
 * @throws Error si operación inválida o falla request
 *
 * @example
 * const spools = await getSpoolsDisponible('ARM');
 * console.log(spools); // [{tag_spool: "MK-123", arm: 0, armador: null, ...}]
 */
export async function getSpoolsDisponible(
  operacion: 'ARM' | 'SOLD' | 'REPARACION'
): Promise<Spool[]> {
  try {
    // For ARM/SOLD, use existing /iniciar endpoint (same logic as disponible)
    // For REPARACION, use dedicated endpoint
    if (operacion === 'REPARACION') {
      const reparacionResponse = await getSpoolsReparacion();
      return reparacionResponse.spools as unknown as Spool[];
    }

    // ARM/SOLD use /iniciar endpoint (shows spools available to start)
    return await getSpoolsParaIniciar(operacion);
  } catch (error) {
    console.error('getSpoolsDisponible error:', error);
    throw new Error(`No se pudieron cargar spools disponibles de ${operacion}.`);
  }
}

/**
 * GET /api/spools/ocupados?operacion={ARM|SOLD|REPARACION}&worker_id={id}
 * Obtiene spools ocupados por el trabajador (v3.0/v4.0 unified).
 *
 * REGLA UNIFICADA:
 * - Filtra por Ocupado_Por contiene "(worker_id)"
 * - Funciona para v3.0 (TOMAR/PAUSAR/COMPLETAR) y v4.0 (INICIAR/FINALIZAR)
 * - Independiente de versión del spool
 *
 * Usado por P4 cuando tipo=pausar/completar/cancelar (v3.0) o accion=FINALIZAR (v4.0).
 * Muestra spools que el trabajador actualmente tiene ocupados.
 *
 * @param workerId - ID numérico del trabajador
 * @param operacion - Tipo de operación ("ARM", "SOLD", o "REPARACION")
 * @returns Promise<Spool[]> - Array de spools ocupados por el trabajador
 * @throws Error si operación inválida o falla request
 *
 * @example
 * const spools = await getSpoolsOcupados(93, 'ARM');
 * console.log(spools); // [{tag_spool: "TEST-02", ocupado_por: "MR(93)", ...}]
 */
export async function getSpoolsOcupados(
  workerId: number,
  operacion: 'ARM' | 'SOLD' | 'REPARACION'
): Promise<Spool[]> {
  try {
    const url = `${API_URL}/api/spools/ocupados?operacion=${operacion}&worker_id=${workerId}`;

    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{ spools: Spool[], total: number, filtro_aplicado: string }>(res);
    return data.spools;
  } catch (error) {
    console.error('getSpoolsOcupados error:', error);
    throw new Error(`No se pudieron cargar tus spools de ${operacion}.`);
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
    // Use /api/spools/iniciar?operacion=REPARACION endpoint (uses FilterRegistry)
    const url = `${API_URL}/api/spools/iniciar?operacion=REPARACION`;
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await handleResponse<{
      spools: Array<{
        tag_spool: string;
        estado_detalle?: string;
        fecha_qc_metrologia?: string;
      }>;
      total: number;
      filtro_aplicado: string;
    }>(res);

    // Transform response to match expected format
    return {
      spools: data.spools.map((spool) => ({
        tag_spool: spool.tag_spool,
        estado_detalle: spool.estado_detalle || '',
        fecha_rechazo: spool.fecha_qc_metrologia || '',
        cycle: 0, // TODO: Extract cycle from estado_detalle if needed
        bloqueado: false // TODO: Determine from estado_detalle if needed
      })),
      total: data.total,
      bloqueados: 0, // TODO: Calculate if needed
      filtro_aplicado: data.filtro_aplicado
    };
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
}): Promise<ReparacionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/completar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...payload,
        operacion: 'REPARACION'  // Required by ActionRequest model
      })
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

    return await handleResponse<ReparacionResponse>(res);
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
}): Promise<ReparacionResponse> {
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

    return await handleResponse<ReparacionResponse>(res);
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
}): Promise<ReparacionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/pausar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return await handleResponse<ReparacionResponse>(res);
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
}): Promise<ReparacionResponse> {
  try {
    const res = await fetch(`${API_URL}/api/cancelar-reparacion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    return await handleResponse<ReparacionResponse>(res);
  } catch (error) {
    console.error('cancelarReparacion error:', error);
    throw error;
  }
}

// ==========================================
// v4.0 UNION-LEVEL API FUNCTIONS (Phase 12)
// ==========================================

/**
 * GET /api/v4/uniones/{tag}/metricas (v4.0)
 * Obtiene métricas de pulgadas-diámetro para un spool.
 *
 * Returns performance metrics including total unions, completed unions,
 * and pulgadas-diámetro sums for ARM and SOLD operations.
 *
 * Used for version detection on P3 (tipo-interaccion page).
 * If union count > 0, spool is v4.0; otherwise v3.0.
 *
 * @param tag - TAG_SPOOL identifier
 * @returns Promise<MetricasResponse> with 6 metric fields
 * @throws Error if:
 *   - 404: Spool not found
 *   - Network error or backend unavailable
 *
 * @example
 * const metricas = await getUnionMetricas('TEST-02');
 * console.log(metricas);
 * // {
 * //   tag_spool: "TEST-02",
 * //   total_uniones: 8,
 * //   uniones_arm_completadas: 3,
 * //   uniones_sold_completadas: 2,
 * //   pulgadas_arm: 12.5,
 * //   pulgadas_sold: 8.2
 * // }
 */
export async function getUnionMetricas(tag: string): Promise<MetricasResponse> {
  try {
    const url = `${API_URL}/api/v4/uniones/${tag}/metricas`;
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Spool no encontrado.');
    }

    return await handleResponse<MetricasResponse>(res);
  } catch (error) {
    console.error('getUnionMetricas error:', error);
    throw error;
  }
}

/**
 * GET /api/v4/uniones/{tag}/disponibles?operacion={ARM|SOLD} (v4.0)
 * Obtiene uniones disponibles para selección en un spool.
 *
 * Returns list of unions that haven't been completed yet for the given operation.
 * Used on P5 (union selection page) after INICIAR is clicked.
 *
 * Filtering logic:
 * - ARM: Returns unions where arm_fecha_fin is None
 * - SOLD: Returns unions where sol_fecha_fin is None AND arm_fecha_fin is not None
 *
 * @param tag - TAG_SPOOL identifier
 * @param operacion - Operation type ('ARM' or 'SOLD')
 * @returns Promise<DisponiblesResponse> with available unions list
 * @throws Error if:
 *   - 404: Spool not found
 *   - 400: Invalid operacion parameter
 *   - Network error or backend unavailable
 *
 * @example
 * const disponibles = await getDisponiblesUnions('TEST-02', 'ARM');
 * console.log(disponibles);
 * // {
 * //   tag_spool: "TEST-02",
 * //   operacion: "ARM",
 * //   uniones: [
 * //     { n_union: 1, dn_union: 2.5, tipo_union: "BW", ... },
 * //     { n_union: 2, dn_union: 3.0, tipo_union: "SO", ... }
 * //   ],
 * //   total_uniones: 8,
 * //   disponibles_count: 2
 * // }
 */
export async function getDisponiblesUnions(
  tag: string,
  operacion: 'ARM' | 'SOLD'
): Promise<DisponiblesResponse> {
  try {
    const url = `${API_URL}/api/v4/uniones/${tag}/disponibles?operacion=${operacion}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (res.status === 404) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Spool no encontrado.');
    }

    if (res.status === 400) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Operación inválida.');
    }

    return await handleResponse<DisponiblesResponse>(res);
  } catch (error) {
    console.error('getDisponiblesUnions error:', error);
    throw error;
  }
}

/**
 * POST /api/v4/occupation/iniciar (v4.0)
 * Inicia ocupación de spool sin selección de uniones.
 *
 * First step of v4.0 two-button workflow (INICIAR → FINALIZAR).
 * Updates Ocupado_Por/Fecha_Ocupacion (occupation).
 * No union-level work is recorded yet - that happens in FINALIZAR.
 *
 * Validations:
 * - Spool must be v4.0 (total_uniones > 0)
 * - For SOLD: ARM prerequisite must be satisfied (100% ARM complete)
 * - Spool must not be occupied
 *
 * @param payload - IniciarRequest with tag_spool, worker_id, worker_nombre, operacion
 * @returns Promise<IniciarResponse> with success status
 * @throws Error if:
 *   - 400: Not a v4.0 spool or validation failed
 *   - 403: ARM prerequisite not met for SOLD
 *   - 404: Spool not found
 *   - 409: Spool already occupied
 *
 * @example
 * const result = await iniciarSpool({
 *   tag_spool: 'TEST-02',
 *   worker_id: 93,
 *   worker_nombre: 'MR(93)',
 *   operacion: 'ARM'
 * });
 * console.log(result);
 * // {
 * //   success: true,
 * //   message: "Spool tomado por MR(93) - selecciona uniones para completar",
 * //   tag_spool: "TEST-02",
 * //   ocupado_por: "MR(93)"
 * // }
 */
export async function iniciarSpool(payload: IniciarRequest): Promise<IniciarResponse> {
  try {
    const res = await fetch(`${API_URL}/api/v4/occupation/iniciar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    // v4.0 specific error handling
    if (res.status === 400) {
      const errorData = await res.json();
      // Handle both string and object detail (WRONG_VERSION returns nested object)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Error de validación. Verifica los datos.';
      throw new Error(errorMessage);
    }

    if (res.status === 403) {
      const errorData = await res.json();
      // Handle both string and object detail (ARM_PREREQUISITE, NO_AUTORIZADO return nested objects)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Requisitos no cumplidos para SOLD. Completa ARM primero.';
      throw new Error(errorMessage);
    }

    if (res.status === 404) {
      const errorData = await res.json();
      // Handle both string and object detail (for consistency)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Spool no encontrado.';
      throw new Error(errorMessage);
    }

    if (res.status === 409) {
      const errorData = await res.json();
      // Handle both string and object detail (SPOOL_OCCUPIED returns nested object)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Spool ocupado por otro trabajador. Intenta más tarde.';
      throw new Error(errorMessage);
    }

    return await handleResponse<IniciarResponse>(res);
  } catch (error) {
    console.error('iniciarSpool error:', error);
    throw error;
  }
}

/**
 * POST /api/v4/occupation/finalizar (v4.0)
 * Completa trabajo con selección de uniones y auto-determinación de PAUSAR/COMPLETAR.
 *
 * Second step of v4.0 two-button workflow (INICIAR → FINALIZAR).
 * Records union-level work, calculates pulgadas-diámetro, and auto-determines:
 * - COMPLETAR: All available unions selected (100% for operation)
 * - PAUSAR: Partial selection (work can be resumed later)
 * - CANCELAR: No unions selected (releases occupation)
 *
 * Updates:
 * - Uniones sheet: arm_fecha_fin/sol_fecha_fin for selected unions
 * - Operaciones sheet: Uniones_ARM_Completadas, Pulgadas_ARM, etc.
 * - Clears occupation on COMPLETAR or CANCELAR (keeps on PAUSAR)
 * - May trigger automatic metrología transition if SOLD 100% complete
 *
 * @param payload - FinalizarRequest with tag_spool, worker_id, operacion, selected_unions[], fecha_operacion
 * @returns Promise<FinalizarResponse> with action result and metrics
 * @throws Error if:
 *   - 400: Validation failed (invalid unions selected)
 *   - 403: Worker doesn't own the spool
 *   - 404: Spool not found
 *   - 409: Race condition (selected unions > available unions)
 *
 * @example
 * // Partial completion (PAUSAR)
 * const result = await finalizarSpool({
 *   tag_spool: 'TEST-02',
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   selected_unions: ['OT-123+1', 'OT-123+2', 'OT-123+3']
 * });
 * console.log(result);
 * // {
 * //   success: true,
 * //   tag_spool: "TEST-02",
 * //   message: "Trabajo pausado - 3 uniones procesadas",
 * //   action_taken: "PAUSAR",
 * //   unions_processed: 3,
 * //   pulgadas: 7.5,
 * //   metrologia_triggered: false,
 * //   new_state: null
 * // }
 *
 * @example
 * // Full completion (COMPLETAR)
 * const result = await finalizarSpool({
 *   tag_spool: 'TEST-02',
 *   worker_id: 93,
 *   operacion: 'ARM',
 *   selected_unions: ['OT-123+1', 'OT-123+2', 'OT-123+3', 'OT-123+4', 'OT-123+5', 'OT-123+6', 'OT-123+7', 'OT-123+8']
 * });
 * console.log(result);
 * // {
 * //   success: true,
 * //   tag_spool: "TEST-02",
 * //   message: "Operación completada - 8 uniones procesadas",
 * //   action_taken: "COMPLETAR",
 * //   unions_processed: 8,
 * //   pulgadas: 20.0,
 * //   metrologia_triggered: false,
 * //   new_state: null
 * // }
 */
export async function finalizarSpool(payload: FinalizarRequest): Promise<FinalizarResponse> {
  try {
    const res = await fetch(`${API_URL}/api/v4/occupation/finalizar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    // v4.0 specific error handling
    if (res.status === 400) {
      const errorData = await res.json();
      // Handle both string and object detail (for consistency)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Error de validación. Verifica las uniones seleccionadas.';
      throw new Error(errorMessage);
    }

    if (res.status === 403) {
      const errorData = await res.json();
      // Handle both string and object detail (for consistency)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'No estás autorizado. Solo quien inició puede finalizar.';
      throw new Error(errorMessage);
    }

    if (res.status === 404) {
      const errorData = await res.json();
      // Handle both string and object detail (for consistency)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Spool no encontrado.';
      throw new Error(errorMessage);
    }

    if (res.status === 409) {
      const errorData = await res.json();
      // Handle both string and object detail (consistent with iniciarSpool)
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : errorData.detail?.message || 'Conflicto: algunas uniones ya fueron completadas por otro trabajador.';
      throw new Error(errorMessage);
    }

    return await handleResponse<FinalizarResponse>(res);
  } catch (error) {
    console.error('finalizarSpool error:', error);
    throw error;
  }
}
