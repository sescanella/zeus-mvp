// TypeScript Types - Completar en DÍA 4

export interface Worker {
  nombre: string;
  apellido?: string;
  activo: boolean;
  nombre_completo: string;
}

export interface Spool {
  tag_spool: string;
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
  worker_nombre: string;
  operacion: 'ARM' | 'SOLD';
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
