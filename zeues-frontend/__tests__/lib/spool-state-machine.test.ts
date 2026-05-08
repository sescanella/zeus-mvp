/**
 * Tests for spool-state-machine — getValidActions
 *
 * Pure functions that determine what actions are available
 * for a given spool based on its current state.
 *
 * Reference: 01-02-PLAN.md Feature 2
 */
import {
  getValidActions,
  ALL_OPERATIONS,
  Action,
  deriveOperation,
  isMetReady,
} from '../../lib/spool-state-machine';
import type { SpoolCardData } from '../../lib/spool-state-machine';

// ─── Helper: build a minimal SpoolCardData for tests ──────────────────────────
function makeSpool(overrides: Partial<SpoolCardData> = {}): SpoolCardData {
  return {
    tag_spool: 'OT-TEST-001',
    nv: null,
    ocupado_por: null,
    ocupado_por_display: null,
    fecha_ocupacion: null,
    estado_detalle: null,
    total_uniones: null,
    uniones_arm_completadas: null,
    uniones_sold_completadas: null,
    pulgadas_arm: null,
    pulgadas_sold: null,
    fecha_armado: null,
    armador_display: null,
    fecha_soldadura: null,
    soldador_display: null,
    operacion_actual: null,
    estado_trabajo: null,
    ciclo_rep: null,
    ...overrides,
  };
}

// ─── ALL_OPERATIONS ─────────────────────────────────────────────────────────────

describe('ALL_OPERATIONS', () => {
  it('always contains all 4 operations', () => {
    expect(ALL_OPERATIONS).toEqual(['ARM', 'SOLD', 'MET', 'REP']);
  });
});

// ─── getValidActions ───────────────────────────────────────────────────────────

describe('getValidActions', () => {
  describe('libre spool (ocupado_por null or empty)', () => {
    it('returns [INICIAR] when ocupado_por is null', () => {
      const spool = makeSpool({ ocupado_por: null });
      expect(getValidActions(spool)).toEqual<Action[]>(['INICIAR']);
    });

    it('returns [INICIAR] when ocupado_por is empty string', () => {
      const spool = makeSpool({ ocupado_por: '' });
      expect(getValidActions(spool)).toEqual<Action[]>(['INICIAR']);
    });
  });

  describe('occupied spool (ocupado_por is non-null and non-empty)', () => {
    it('returns [FINALIZAR, PAUSAR] when ocupado_por is set', () => {
      const spool = makeSpool({ ocupado_por: 'MR(93)' });
      expect(getValidActions(spool)).toEqual<Action[]>(['FINALIZAR', 'PAUSAR']);
    });

    it('returns [FINALIZAR, PAUSAR] for different worker format', () => {
      const spool = makeSpool({ ocupado_por: 'JP(12)' });
      expect(getValidActions(spool)).toEqual<Action[]>(['FINALIZAR', 'PAUSAR']);
    });
  });

  describe('actions independent of estado_trabajo', () => {
    it('COMPLETADO with no worker -> INICIAR', () => {
      const spool = makeSpool({ estado_trabajo: 'COMPLETADO', ocupado_por: null });
      expect(getValidActions(spool)).toEqual<Action[]>(['INICIAR']);
    });

    it('LIBRE with worker set -> FINALIZAR+PAUSAR', () => {
      // Edge case: estado says LIBRE but ocupado_por is set — actions follow ocupado_por
      const spool = makeSpool({ estado_trabajo: 'LIBRE', ocupado_por: 'MR(93)' });
      expect(getValidActions(spool)).toEqual<Action[]>(['FINALIZAR', 'PAUSAR']);
    });
  });
});

// ─── deriveOperation ───────────────────────────────────────────────────────────

describe('deriveOperation', () => {
  it('returns ARM when operacion_actual is ARM', () => {
    const spool = makeSpool({ operacion_actual: 'ARM', ocupado_por: 'MR(93)' });
    expect(deriveOperation(spool)).toBe('ARM');
  });

  it('returns SOLD when operacion_actual is SOLD', () => {
    const spool = makeSpool({ operacion_actual: 'SOLD', ocupado_por: 'JP(45)' });
    expect(deriveOperation(spool)).toBe('SOLD');
  });

  it('returns REP when operacion_actual is REPARACION', () => {
    const spool = makeSpool({ operacion_actual: 'REPARACION', ocupado_por: 'MM(11)' });
    expect(deriveOperation(spool)).toBe('REP');
  });

  it('returns null for a truly LIBRE spool with no work yet', () => {
    const spool = makeSpool({
      estado_trabajo: 'LIBRE',
      ocupado_por: null,
      fecha_armado: null,
      fecha_soldadura: null,
    });
    expect(deriveOperation(spool)).toBe(null);
  });

  // T-110: post-ARM intermediate state — only valid next op is SOLD.
  it('T-110: returns SOLD for ARM_TERM (LIBRE + fecha_armado set, fecha_soldadura null, not occupied)', () => {
    const spool = makeSpool({
      estado_trabajo: 'LIBRE',
      ocupado_por: null,
      fecha_armado: '21-01-2026',
      fecha_soldadura: null,
      operacion_actual: null,
    });
    expect(deriveOperation(spool)).toBe('SOLD');
  });

  // T-110 guard: spool with fecha_armado but currently occupied (e.g. by
  // SOLD worker) has operacion_actual set, which takes precedence.
  it('T-110: occupied SOLD spool returns SOLD via operacion_actual, not via T-110 fallback', () => {
    const spool = makeSpool({
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'JP(45)',
      fecha_armado: '21-01-2026',
      fecha_soldadura: null,
      operacion_actual: 'SOLD',
    });
    expect(deriveOperation(spool)).toBe('SOLD');
  });

  // T-110 guard: SOLD already done — should NOT return SOLD again.
  it('T-110: returns null when fecha_soldadura is also set (post-SOLD spool)', () => {
    const spool = makeSpool({
      estado_trabajo: 'PENDIENTE_METROLOGIA',
      ocupado_por: null,
      fecha_armado: '21-01-2026',
      fecha_soldadura: '22-01-2026',
      operacion_actual: null,
    });
    // PENDIENTE_METROLOGIA path is handled by isMetReady, not deriveOperation.
    expect(deriveOperation(spool)).toBe(null);
  });
});

// ─── isMetReady (T-110) ───────────────────────────────────────────────────────

describe('isMetReady', () => {
  it('returns true for PENDIENTE_METROLOGIA spool (post-SOLD intermediate)', () => {
    const spool = makeSpool({ estado_trabajo: 'PENDIENTE_METROLOGIA' });
    expect(isMetReady(spool)).toBe(true);
  });

  it('returns false for LIBRE spool', () => {
    const spool = makeSpool({ estado_trabajo: 'LIBRE' });
    expect(isMetReady(spool)).toBe(false);
  });

  it('returns false for EN_PROGRESO spool', () => {
    const spool = makeSpool({ estado_trabajo: 'EN_PROGRESO', ocupado_por: 'MR(93)' });
    expect(isMetReady(spool)).toBe(false);
  });

  it('returns false for RECHAZADO spool (handoff path, not direct skip)', () => {
    const spool = makeSpool({ estado_trabajo: 'RECHAZADO' });
    expect(isMetReady(spool)).toBe(false);
  });
});
