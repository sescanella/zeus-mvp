/**
 * Tests for parseEstadoDetalle — TypeScript mirror of backend estado_detalle_parser.py
 *
 * Covers all 11 known Estado_Detalle formats produced by EstadoDetalleBuilder.
 * Must produce identical output to the Python parse_estado_detalle() function.
 *
 * Reference: backend/services/estado_detalle_parser.py
 */
import { parseEstadoDetalle, ParsedEstadoDetalle } from '../../lib/parse-estado-detalle';

describe('parseEstadoDetalle', () => {
  // ============================================================
  // NULL / EMPTY / WHITESPACE inputs -> LIBRE defaults
  // ============================================================
  describe('null and empty inputs', () => {
    it('returns LIBRE defaults for null', () => {
      const result = parseEstadoDetalle(null);
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'LIBRE',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('returns LIBRE defaults for undefined', () => {
      const result = parseEstadoDetalle(undefined);
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'LIBRE',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('returns LIBRE defaults for empty string', () => {
      const result = parseEstadoDetalle('');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'LIBRE',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('returns LIBRE defaults for whitespace-only string', () => {
      const result = parseEstadoDetalle('   ');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'LIBRE',
        ciclo_rep: null,
        worker: null,
      });
    });
  });

  // ============================================================
  // Pattern 1: Occupied ARM — "MR(93) trabajando ARM (...)"
  // ============================================================
  describe('Pattern 1: Occupied working ARM', () => {
    it('parses ARM in progress', () => {
      const result = parseEstadoDetalle('MR(93) trabajando ARM (ARM en progreso, SOLD pendiente)');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: 'ARM',
        estado_trabajo: 'EN_PROGRESO',
        ciclo_rep: null,
        worker: 'MR(93)',
      });
    });

    it('extracts worker correctly with different worker formats', () => {
      const result = parseEstadoDetalle('JP(12) trabajando ARM (ARM en progreso, SOLD pendiente)');
      expect(result.worker).toBe('JP(12)');
      expect(result.operacion_actual).toBe('ARM');
      expect(result.estado_trabajo).toBe('EN_PROGRESO');
    });
  });

  // ============================================================
  // Pattern 1: Occupied SOLD — "MR(93) trabajando SOLD (...)"
  // ============================================================
  describe('Pattern 1: Occupied working SOLD', () => {
    it('parses SOLD in progress', () => {
      const result = parseEstadoDetalle('MR(93) trabajando SOLD (ARM completado, SOLD en progreso)');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: 'SOLD',
        estado_trabajo: 'EN_PROGRESO',
        ciclo_rep: null,
        worker: 'MR(93)',
      });
    });
  });

  // ============================================================
  // Pattern 2: REPARACION in progress — "EN_REPARACION (Ciclo N/3) - Ocupado: MR(93)"
  // ============================================================
  describe('Pattern 2: REPARACION in progress', () => {
    it('parses reparacion ciclo 1', () => {
      const result = parseEstadoDetalle('EN_REPARACION (Ciclo 1/3) - Ocupado: MR(93)');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: 'REPARACION',
        estado_trabajo: 'EN_PROGRESO',
        ciclo_rep: 1,
        worker: null,
      });
    });

    it('parses reparacion ciclo 2', () => {
      const result = parseEstadoDetalle('EN_REPARACION (Ciclo 2/3) - Ocupado: MR(93)');
      expect(result.ciclo_rep).toBe(2);
      expect(result.operacion_actual).toBe('REPARACION');
      expect(result.estado_trabajo).toBe('EN_PROGRESO');
    });

    it('parses reparacion ciclo 3', () => {
      const result = parseEstadoDetalle('EN_REPARACION (Ciclo 3/3) - Ocupado: JP(12)');
      expect(result.ciclo_rep).toBe(3);
    });
  });

  // ============================================================
  // Pattern 3: BLOQUEADO — "BLOQUEADO - Contactar supervisor"
  // ============================================================
  describe('Pattern 3: BLOQUEADO', () => {
    it('parses BLOQUEADO string', () => {
      const result = parseEstadoDetalle('BLOQUEADO - Contactar supervisor');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'BLOQUEADO',
        ciclo_rep: null,
        worker: null,
      });
    });
  });

  // ============================================================
  // Pattern 4: RECHAZADO with cycle — "... RECHAZADO (Ciclo N/3) - Pendiente reparacion"
  // ============================================================
  describe('Pattern 4: RECHAZADO with cycle', () => {
    it('parses RECHAZADO ciclo 2', () => {
      const result = parseEstadoDetalle(
        'Disponible - ARM completado, SOLD completado, RECHAZADO (Ciclo 2/3) - Pendiente reparacion'
      );
      expect(result.estado_trabajo).toBe('RECHAZADO');
      expect(result.ciclo_rep).toBe(2);
      expect(result.operacion_actual).toBeNull();
    });

    it('parses RECHAZADO ciclo 1', () => {
      const result = parseEstadoDetalle('RECHAZADO (Ciclo 1/3) - Pendiente reparacion');
      expect(result.estado_trabajo).toBe('RECHAZADO');
      expect(result.ciclo_rep).toBe(1);
    });
  });

  // ============================================================
  // Pattern 5: RECHAZADO bare — "RECHAZADO"
  // ============================================================
  describe('Pattern 5: RECHAZADO bare', () => {
    it('parses bare RECHAZADO', () => {
      const result = parseEstadoDetalle('RECHAZADO');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'RECHAZADO',
        ciclo_rep: null,
        worker: null,
      });
    });
  });

  // ============================================================
  // Pattern 6: PENDIENTE_METROLOGIA — "REPARACION completado - PENDIENTE_METROLOGIA"
  // ============================================================
  describe('Pattern 6: PENDIENTE_METROLOGIA', () => {
    it('parses PENDIENTE_METROLOGIA format', () => {
      const result = parseEstadoDetalle('REPARACION completado - PENDIENTE_METROLOGIA');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'PENDIENTE_METROLOGIA',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('also matches via PENDIENTE_METROLOGIA keyword alone', () => {
      const result = parseEstadoDetalle('PENDIENTE_METROLOGIA');
      expect(result.estado_trabajo).toBe('PENDIENTE_METROLOGIA');
    });

    it('also matches via REPARACION completado keyword', () => {
      const result = parseEstadoDetalle('REPARACION completado - pending review');
      expect(result.estado_trabajo).toBe('PENDIENTE_METROLOGIA');
    });
  });

  // ============================================================
  // Pattern 7: METROLOGIA APROBADO — "... METROLOGIA APROBADO ✓"
  // ============================================================
  describe('Pattern 7: METROLOGIA APROBADO', () => {
    it('parses METROLOGIA APROBADO checkmark', () => {
      const result = parseEstadoDetalle(
        'Disponible - ARM completado, SOLD completado, METROLOGIA APROBADO \u2713'
      );
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'COMPLETADO',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('also matches METROLOGIA APROBADO without checkmark', () => {
      const result = parseEstadoDetalle('METROLOGIA APROBADO - done');
      expect(result.estado_trabajo).toBe('COMPLETADO');
    });
  });

  // ============================================================
  // Pattern 8: ARM + SOLD completado — "ARM completado, SOLD completado"
  // ============================================================
  describe('Pattern 8: ARM and SOLD completado', () => {
    it('parses both ARM and SOLD completado as COMPLETADO', () => {
      const result = parseEstadoDetalle('Disponible - ARM completado, SOLD completado');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'COMPLETADO',
        ciclo_rep: null,
        worker: null,
      });
    });
  });

  // ============================================================
  // Pattern 9: ARM done, SOLD pendiente/pausado
  // ============================================================
  describe('Pattern 9: ARM done, SOLD pending or paused', () => {
    it('parses ARM completado SOLD pendiente as PAUSADO', () => {
      const result = parseEstadoDetalle('Disponible - ARM completado, SOLD pendiente');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: 'ARM',
        estado_trabajo: 'PAUSADO',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('parses ARM completado SOLD pausado as PAUSADO', () => {
      const result = parseEstadoDetalle('Disponible - ARM completado, SOLD pausado');
      expect(result.estado_trabajo).toBe('PAUSADO');
      expect(result.operacion_actual).toBe('ARM');
    });
  });

  // ============================================================
  // Pattern 10: ARM pausado
  // ============================================================
  describe('Pattern 10: ARM pausado', () => {
    it('parses ARM pausado string', () => {
      const result = parseEstadoDetalle('ARM pausado');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: 'ARM',
        estado_trabajo: 'PAUSADO',
        ciclo_rep: null,
        worker: null,
      });
    });
  });

  // ============================================================
  // Pattern 11: Default fallback -> LIBRE
  // ============================================================
  describe('Pattern 11: Default fallback', () => {
    it('returns LIBRE for unrecognized string', () => {
      const result = parseEstadoDetalle('alguna cadena desconocida xyz');
      expect(result).toEqual<ParsedEstadoDetalle>({
        operacion_actual: null,
        estado_trabajo: 'LIBRE',
        ciclo_rep: null,
        worker: null,
      });
    });

    it('returns LIBRE for arbitrary text', () => {
      const result = parseEstadoDetalle('random text with no matching pattern');
      expect(result.estado_trabajo).toBe('LIBRE');
    });
  });

  // ============================================================
  // Match order verification: BLOQUEADO must come before RECHAZADO
  // (RECHAZADO is never actually tested with BLOQUEADO together but
  //  order matters when patterns could overlap)
  // ============================================================
  describe('Pattern order correctness', () => {
    it('RECHAZADO with cycle takes precedence over bare RECHAZADO', () => {
      const withCycle = parseEstadoDetalle('RECHAZADO (Ciclo 2/3) - Pendiente reparacion');
      expect(withCycle.ciclo_rep).toBe(2);

      const bare = parseEstadoDetalle('RECHAZADO');
      expect(bare.ciclo_rep).toBeNull();
    });

    it('ARM+SOLD completado matches before ARM completado SOLD pendiente when both present', () => {
      // Full completion string — should be COMPLETADO not PAUSADO
      const result = parseEstadoDetalle('Disponible - ARM completado, SOLD completado');
      expect(result.estado_trabajo).toBe('COMPLETADO');
    });
  });
});
