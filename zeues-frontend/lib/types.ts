// TypeScript Types - Completar en DÍA 4

export interface Worker {
  id: number;
  nombre: string;
  apellido?: string;
  rol?: string;  // Legacy/deprecated - usar roles array
  roles?: string[];  // v2.0: Array de roles desde hoja Roles
  activo: boolean;
  nombre_completo: string;  // v2.1: Formato "INICIALES(ID)" ej: "MR(93)"
}

export interface Spool {
  tag_spool: string;
  nv?: string;  // v2.0: Número de Nota de Venta (filtro multidimensional)
  arm: number;
  sold: number;
  proyecto?: string;
  fecha_materiales?: string;
  fecha_armado?: string;
  armador?: string;  // v2.1: Formato "INICIALES(ID)" ej: "JP(93)"
  fecha_soldadura?: string;
  soldador?: string;  // v2.1: Formato "INICIALES(ID)" ej: "MG(94)"
  fecha_qc_metrologia?: string | null;  // v2.1: Fecha QC/Metrología completada
}

export interface ActionPayload {
  worker_id: number;  // v2.0: Breaking change from worker_nombre (string) to worker_id (number)
  operacion: 'ARM' | 'SOLD' | 'METROLOGIA';  // v2.0: +METROLOGIA
  tag_spool: string;
  timestamp?: string;
}

// Response de API para iniciar/completar acción
export interface ActionResponse {
  success: boolean;
  message: string;
  data: {
    tag_spool: string;
    operacion: string;
    trabajador: string;  // v2.1: Formato "INICIALES(ID)" ej: "MR(93)"
    fila_actualizada: number;
    columna_actualizada: string;
    valor_nuevo: number;
    metadata_actualizada: Record<string, unknown>;
  };
}

// ==========================================
// BATCH OPERATIONS (v2.0 Multiselect)
// ==========================================

/**
 * Request para operaciones batch (múltiples spools)
 *
 * Soporta hasta 50 spools simultáneos
 */
export interface BatchActionRequest {
  worker_id: number;
  operacion: 'ARM' | 'SOLD' | 'METROLOGIA';
  tag_spools: string[];  // Array de TAGs (máx 50)
  timestamp?: string;    // Solo para completar
}

/**
 * Resultado individual de un spool en batch operation
 */
export interface SpoolActionResult {
  tag_spool: string;
  success: boolean;
  message: string;
  evento_id: string | null;
  error_type: string | null;
}

/**
 * Response de batch operation (iniciar/completar/cancelar)
 *
 * Retorna stats agregadas + resultados individuales
 * success=true si AL MENOS 1 spool fue procesado exitosamente
 */
export interface BatchActionResponse {
  success: boolean;
  message: string;
  total: number;
  exitosos: number;
  fallidos: number;
  resultados: SpoolActionResult[];
}

// ==========================================
// OCCUPATION v3.0 TYPES (Redis locks + State Machine)
// ==========================================

/**
 * Request para TOMAR un spool (iniciar ocupación v3.0)
 *
 * Utilizado por endpoint POST /api/occupation/tomar
 * Adquiere lock Redis y actualiza Ocupado_Por/Fecha_Ocupacion
 */
export interface TomarRequest {
  tag_spool: string;
  worker_id: number;
  worker_nombre: string;  // Format: "INICIALES(ID)" e.g., "MR(93)"
  operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';
}

/**
 * Request para PAUSAR trabajo en un spool (v3.0)
 *
 * Utilizado por endpoint POST /api/occupation/pausar
 * Marca como "parcial (pausado)" y libera lock
 */
export interface PausarRequest {
  tag_spool: string;
  worker_id: number;
  worker_nombre: string;
  operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';
}

/**
 * Request para COMPLETAR trabajo en un spool (v3.0)
 *
 * Utilizado por endpoint POST /api/occupation/completar
 * Actualiza fecha_armado/soldadura y libera lock
 */
export interface CompletarRequest {
  tag_spool: string;
  worker_id: number;
  worker_nombre: string;
  fecha_operacion: string;  // REQUIRED - Format: "DD-MM-YYYY" (e.g., "28-01-2026")
}

/**
 * Request para TOMAR múltiples spools en batch (v3.0)
 *
 * Utilizado por endpoint POST /api/occupation/batch-tomar
 * Máximo 50 spools por operación
 */
export interface BatchTomarRequest {
  tag_spools: string[];  // Min 1, Max 50
  worker_id: number;
  worker_nombre: string;
  operacion: 'ARM' | 'SOLD' | 'METROLOGIA' | 'REPARACION';
}

/**
 * Response para operaciones individuales v3.0 (TOMAR/PAUSAR/COMPLETAR)
 *
 * CRÍTICO: Backend retorna SOLO 3 campos (NO incluye ocupado_por, fecha_ocupacion, version, estado_detalle)
 */
export interface OccupationResponse {
  success: boolean;
  tag_spool: string;
  message: string;
}

/**
 * Response para operaciones batch v3.0
 *
 * IMPORTANTE: Usa nombres en inglés (succeeded/failed) NO español (exitosos/fallidos)
 */
export interface BatchOccupationResponse {
  total: number;      // Total spools procesados
  succeeded: number;  // Cantidad exitosa (English!)
  failed: number;     // Cantidad fallida (English!)
  details: OccupationResponse[];  // Resultados individuales
}

// ==========================================
// REAL-TIME SSE (v3.0)
// ==========================================

/**
 * Evento SSE de actualización de spool
 */
export interface SSEEvent {
  type: 'TOMAR' | 'PAUSAR' | 'COMPLETAR' | 'STATE_CHANGE';
  tag_spool: string;
  worker: string | null;
  estado_detalle: string | null;
  timestamp: string;
}

/**
 * Opciones para useSSE hook
 */
export interface UseSSEOptions {
  onMessage: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
  onConnectionChange?: (connected: boolean) => void;
  openWhenHidden?: boolean;  // Default: false
}
