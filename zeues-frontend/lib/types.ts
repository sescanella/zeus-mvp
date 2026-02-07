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
  ocupado_por?: string | null;  // v3.0: Worker ocupando el spool (formato: "MR(93)"), v4.0: Usado para FINALIZAR
  fecha_ocupacion?: string | null;  // v3.0: Timestamp de ocupación (DD-MM-YYYY HH:MM:SS)
  total_uniones?: number;  // v4.0: Column 68 - Total union count
  version?: 'v3.0' | 'v4.0';  // v4.0: Derived from total_uniones (>0 = v4.0, 0 = v3.0)
}

// ==========================================
// BATCH OPERATIONS (v2.0 Multiselect) - DEPRECATED
// Legacy types removed in v3.0 refactor (Feb 2026)
// ==========================================

// ==========================================
// REPARACION OPERATIONS (Phase 6)
// ==========================================

/**
 * Response for reparación operations
 *
 * Used by completarReparacion, tomarReparacion, pausarReparacion, cancelarReparacion
 */
export interface ReparacionResponse {
  success: boolean;
  message: string;
  tag_spool: string;
  estado_detalle?: string;
}

// ==========================================
// REAL-TIME SSE (v3.0) - REMOVED
// Single-user mode doesn't need real-time updates
// ==========================================
// VERSION DETECTION (v4.0 Phase 9)
// ==========================================

/**
 * Version information for a spool (v3.0 vs v4.0)
 *
 * Detection logic: count > 0 = v4.0, count = 0 = v3.0
 */
export interface VersionInfo {
  version: 'v3.0' | 'v4.0';
  union_count: number;
  detection_logic: string;
  tag_spool: string;
}

/**
 * API response for version detection endpoint
 */
export interface VersionResponse {
  success: boolean;
  data: VersionInfo;
}

// ==========================================
// v4.0 UNION-LEVEL TYPES (Phase 12)
// ==========================================

/**
 * Union interface representing a single union in a spool (v4.0)
 *
 * Represents a row from the Uniones sheet (18 columns).
 * Used for union-level tracking and selection workflows.
 */
export interface Union {
  id: string; // Composite ID: TAG_SPOOL+N_UNION (e.g., 'OT-123+5')
  n_union: number;
  dn_union: number;
  tipo_union: string;
  arm_fecha_inicio?: string;
  arm_fecha_fin?: string;
  arm_worker?: string;
  sol_fecha_inicio?: string;
  sol_fecha_fin?: string;
  sol_worker?: string;
  ndt_fecha?: string;
  ndt_status?: string;
  is_completed?: boolean; // Computed field for UI (whether this union is already completed)
}

/**
 * Response for GET /api/v4/uniones/{tag}/disponibles endpoint
 *
 * Returns list of available unions for a given operation.
 */
export interface DisponiblesResponse {
  tag_spool: string;
  operacion: string;
  unions: Union[];  // English field name to match backend Pydantic model
  count: number;    // Backend returns 'count' not 'disponibles_count'
}

/**
 * Response for GET /api/v4/uniones/{tag}/metricas endpoint
 *
 * Returns pulgadas-diámetro performance metrics.
 */
export interface MetricasResponse {
  tag_spool: string;
  total_uniones: number;
  uniones_arm_completadas: number;
  uniones_sold_completadas: number;
  pulgadas_arm: number;
  pulgadas_sold: number;
}

/**
 * Request for POST /api/v4/occupation/iniciar endpoint
 *
 * Occupies spool without union selection (v4.0 INICIAR workflow).
 */
export interface IniciarRequest {
  tag_spool: string;
  worker_id: number;
  worker_nombre: string;
  operacion: 'ARM' | 'SOLD';
}

/**
 * Response for POST /api/v4/occupation/iniciar endpoint
 */
export interface IniciarResponse {
  success: boolean;
  message: string;
  tag_spool: string;
  ocupado_por: string;
}

/**
 * Request for POST /api/v4/occupation/finalizar endpoint
 *
 * Union selection + auto PAUSAR/COMPLETAR determination (v4.0 FINALIZAR workflow).
 */
export interface FinalizarRequest {
  tag_spool: string;
  worker_id: number;
  operacion: 'ARM' | 'SOLD';
  selected_unions: string[]; // Union IDs (format: "OT-123+5")
}

/**
 * Response for POST /api/v4/occupation/finalizar endpoint
 *
 * IMPORTANT: Field names must match backend FinalizarResponseV4 model exactly:
 * - action_taken (not "action")
 * - unions_processed (not "uniones_completadas")
 * - pulgadas (not "pulgadas_completadas")
 */
export interface FinalizarResponse {
  success: boolean;
  tag_spool: string;
  message: string;
  action_taken: 'PAUSAR' | 'COMPLETAR' | 'CANCELADO';  // Backend returns "CANCELADO" not "CANCELAR"
  unions_processed: number;  // Backend field name
  pulgadas: number | null;   // Backend field name (nullable)
  metrologia_triggered: boolean;
  new_state: string | null;  // Backend field name (nullable)
}
