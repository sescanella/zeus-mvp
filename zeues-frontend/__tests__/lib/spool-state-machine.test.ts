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
} from '../../lib/spool-state-machine';
import type { SpoolCardData } from '../../lib/spool-state-machine';

// ─── Helper: build a minimal SpoolCardData for tests ──────────────────────────
function makeSpool(overrides: Partial<SpoolCardData> = {}): SpoolCardData {
  return {
    tag_spool: 'OT-TEST-001',
    ocupado_por: null,
    fecha_ocupacion: null,
    estado_detalle: null,
    total_uniones: null,
    uniones_arm_completadas: null,
    uniones_sold_completadas: null,
    pulgadas_arm: null,
    pulgadas_sold: null,
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
    it('returns [INICIAR, CANCELAR] when ocupado_por is null', () => {
      const spool = makeSpool({ ocupado_por: null });
      expect(getValidActions(spool)).toEqual<Action[]>(['INICIAR', 'CANCELAR']);
    });

    it('returns [INICIAR, CANCELAR] when ocupado_por is empty string', () => {
      const spool = makeSpool({ ocupado_por: '' });
      expect(getValidActions(spool)).toEqual<Action[]>(['INICIAR', 'CANCELAR']);
    });
  });

  describe('occupied spool (ocupado_por is non-null and non-empty)', () => {
    it('returns [FINALIZAR, PAUSAR, CANCELAR] when ocupado_por is set', () => {
      const spool = makeSpool({ ocupado_por: 'MR(93)' });
      expect(getValidActions(spool)).toEqual<Action[]>(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    });

    it('returns [FINALIZAR, PAUSAR, CANCELAR] for different worker format', () => {
      const spool = makeSpool({ ocupado_por: 'JP(12)' });
      expect(getValidActions(spool)).toEqual<Action[]>(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    });
  });

  describe('actions independent of estado_trabajo', () => {
    it('COMPLETADO with no worker -> INICIAR+CANCELAR', () => {
      const spool = makeSpool({ estado_trabajo: 'COMPLETADO', ocupado_por: null });
      expect(getValidActions(spool)).toEqual<Action[]>(['INICIAR', 'CANCELAR']);
    });

    it('LIBRE with worker set -> FINALIZAR+PAUSAR+CANCELAR', () => {
      // Edge case: estado says LIBRE but ocupado_por is set — actions follow ocupado_por
      const spool = makeSpool({ estado_trabajo: 'LIBRE', ocupado_por: 'MR(93)' });
      expect(getValidActions(spool)).toEqual<Action[]>(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    });
  });
});
