// TypeScript Types - Completar en DÍA 4

export interface Worker {
  id: number;
  nombre: string;
  apellido?: string;
  rol?: string;  // Legacy/deprecated - usar roles array
  roles?: string[];  // v2.0: Array de roles desde hoja Roles
  activo: boolean;
  nombre_completo: string;
}

export interface Spool {
  tag_spool: string;
  nv?: string;  // v2.0: Número de Nota de Venta (filtro multidimensional)
  arm: number;
  sold: number;
  proyecto?: string;
  fecha_materiales?: string;
  fecha_armado?: string;
  armador?: string;
  fecha_soldadura?: string;
  soldador?: string;
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
    trabajador: string;
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
