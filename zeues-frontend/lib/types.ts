// TypeScript Types - Completar en DÍA 4

// ==========================================
// v5.0 SPOOL CARD TYPES
// ==========================================

/**
 * Union type of all possible spool work states.
 * Mirrors backend EstadoTrabajo enum exactly.
 */
export type EstadoTrabajo =
  | 'LIBRE'
  | 'EN_PROGRESO'
  | 'PAUSADO'
  | 'COMPLETADO'
  | 'RECHAZADO'
  | 'PENDIENTE_METROLOGIA';

/**
 * Union type of all possible active operations.
 * Mirrors backend OperacionActual field exactly.
 */
export type OperacionActual = 'ARM' | 'SOLD' | 'REPARACION' | null;

/**
 * Spool status data for v5.0 single-page card view.
 * Mirrors backend SpoolStatus Pydantic model exactly (snake_case field names).
 * Used by SpoolCard component and batch polling refresh.
 */
export interface CompletionEntry {
  operation: string;
  worker: string;
  date: string;
  /** T-021: 'partial' renders yellow, 'complete' renders green. Defaults to 'complete' if absent. */
  kind?: 'complete' | 'partial';
}

export interface SpoolCardData {
  tag_spool: string;
  nv: string | null;
  ocupado_por: string | null;
  ocupado_por_display: string | null;
  fecha_ocupacion: string | null;
  estado_detalle: string | null;
  total_uniones: number | null;
  uniones_arm_completadas: number | null;
  uniones_sold_completadas: number | null;
  pulgadas_arm: number | null;
  pulgadas_sold: number | null;
  completion_history: CompletionEntry[];
  fecha_armado: string | null;
  armador_display: string | null;
  fecha_soldadura: string | null;
  soldador_display: string | null;
  operacion_actual: OperacionActual;
  estado_trabajo: EstadoTrabajo | null;
}

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

/** Spool with reparación-specific fields returned by /api/spools/iniciar?operacion=REPARACION */
export interface ReparacionSpool {
  tag_spool: string;
  estado_detalle: string;
  fecha_rechazo: string;
}

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
  worker_nombre?: string;  // Optional — backend derives via WorkerService when not provided (Plan 00-03)
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
  selected_unions?: string[];  // Optional — not needed when action_override is set (Plan 00-03)
  action_override?: 'PAUSAR' | 'COMPLETAR';  // Bypass union selection (Plan 00-03)
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

// ==========================================
// UNIONES CRUD TYPES (UnionesModal)
// ==========================================

export interface UnionEditable {
  id?: string;                    // Composite ID: OT+N_UNION (e.g., "001+5")
  n_union: number;
  dn_union: number | null;
  tipo_union: string | null;
  has_work: boolean;
  arm_worker?: string | null;     // Worker who did ARM (e.g., "MR(93)")
  sol_worker?: string | null;     // Worker who did SOLD (e.g., "JP(45)")
}

export interface GetAllUnionsResponse {
  tag_spool: string;
  unions: UnionEditable[];
  total: number;
}

export interface SaveUnionsRequest {
  tag_spool: string;
  unions: { n_union: number; dn_union: number | null; tipo_union: string | null }[];
}

export interface SaveUnionsResponse {
  success: boolean;
  tag_spool: string;
  total_uniones: number;
  created: number;
  updated: number;
  deleted: number;
  created_ids: Array<{ n_union: number; id: string }>;
  message: string;
}

// ==========================================
// MI REGISTRO TYPES (Pieza 2)
// ==========================================

export interface WorkerUnionRecord {
  n_union: number;
  dn_union: number | null;
  tipo_union: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
}

export interface SpoolGroup {
  tag_spool: string;
  operacion: string;
  uniones: WorkerUnionRecord[];
  pd_total: number;
  otro_trabajador: string | null;
}

export interface RegistroResumen {
  fecha: string;
  pd_total: number;
  total_uniones: number;
  total_spools: number;
}

export interface RegistroResponse {
  worker_id: number;
  worker_nombre: string;
  fecha: string;
  resumen: RegistroResumen;
  spools: SpoolGroup[];
}

// ==========================================
// SUPERVISOR FEATURE TYPES
// (server-side tracking list + audit log)
// Mirrors backend/models/supervisor.py exactly.
// ==========================================

/**
 * Tipos de eventos del audit log del supervisor.
 * Debe coincidir 1:1 con backend/models/supervisor.py:EventType.
 *
 * Notas:
 * - El frontend NO emite LIST_ADD/LIST_REMOVE: el backend los genera
 *   server-side cuando llega la mutación correspondiente.
 * - LIST_MIGRATE / LIST_MIGRATE_PARTIAL los emite el frontend al final del
 *   flujo de migración Capa 1 (éxito o parcial).
 */
export type SupervisorEventType =
  | 'SESSION_START'
  | 'SESSION_END'
  | 'LIST_ADD'
  | 'LIST_REMOVE'
  | 'LIST_MIGRATE'
  | 'LIST_MIGRATE_PARTIAL'
  | 'MODAL_OPEN'
  | 'MODAL_CLOSE'
  | 'NAVIGATE';

/**
 * Una fila en la tab Lista del audit Sheet.
 * Mirrors backend TrackedSpool.
 *
 * - added_at / updated_at: ISO 8601 strings (el backend serializa Pydantic
 *   datetime a ISO al enviar JSON; al guardar en Sheets convierte a
 *   DD-MM-YYYY HH:MM:SS, pero eso no nos toca al frontend).
 * - notes: null si no hay nota.
 */
export interface TrackedSpool {
  tag_spool: string;
  added_at: string;
  updated_at: string;
  notes: string | null;
}

/**
 * Un evento del audit log.
 * Mirrors backend AuditEvent.
 *
 * - id: UUID generado por el cliente para idempotencia en retries.
 * - timestamp: ISO 8601 con timezone (use new Date().toISOString()).
 * - session_id: UUID por pestaña/sesión, generado por audit-buffer.ts.
 * - payload_json: string JSON serializado, NO objeto (el backend lo guarda
 *   verbatim sin parsear). Use JSON.stringify(...) si quieres adjuntar datos.
 */
export interface SupervisorAuditEvent {
  id: string;
  timestamp: string;
  session_id: string;
  event_type: SupervisorEventType;
  tag_spool?: string | null;
  modal?: string | null;
  route?: string | null;
  payload_json?: string | null;
}

/**
 * Capa 0 de migración: dump verbatim de localStorage al audit Sheet
 * antes de tocar nada. Mirrors backend LegacySnapshot.
 */
export interface SupervisorLegacySnapshot {
  snapshot_id: string;
  captured_at?: string;          // default backend = now()
  raw: string;                   // localStorage[zeues_v5_spool_tags] sin parsear
  user_agent?: string | null;
}

