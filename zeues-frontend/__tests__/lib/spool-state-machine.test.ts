/**
 * Tests for spool-state-machine — getValidOperations and getValidActions
 *
 * Pure functions that determine what operations and actions are available
 * for a given spool based on its current state.
 *
 * Reference: 01-02-PLAN.md Feature 2
 */
import {
  getValidOperations,
  getValidActions,
  Operation,
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

// ─── getValidOperations ────────────────────────────────────────────────────────

describe('getValidOperations', () => {
  describe('LIBRE -> ARM only', () => {
    it('returns [ARM] for LIBRE spool', () => {
      const spool = makeSpool({ estado_trabajo: 'LIBRE' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['ARM']);
    });
  });

  describe('EN_PROGRESO -> operation-specific', () => {
    it('returns [ARM] for EN_PROGRESO + ARM', () => {
      const spool = makeSpool({ estado_trabajo: 'EN_PROGRESO', operacion_actual: 'ARM' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['ARM']);
    });

    it('returns [SOLD] for EN_PROGRESO + SOLD', () => {
      const spool = makeSpool({ estado_trabajo: 'EN_PROGRESO', operacion_actual: 'SOLD' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['SOLD']);
    });

    it('returns [REP] for EN_PROGRESO + REPARACION', () => {
      const spool = makeSpool({ estado_trabajo: 'EN_PROGRESO', operacion_actual: 'REPARACION' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['REP']);
    });

    it('returns [] for EN_PROGRESO + null operacion', () => {
      const spool = makeSpool({ estado_trabajo: 'EN_PROGRESO', operacion_actual: null });
      expect(getValidOperations(spool)).toEqual<Operation[]>([]);
    });
  });

  describe('PAUSADO + ARM disambiguation', () => {
    it('returns [ARM] for PAUSADO + ARM + arm partially done (arm < total)', () => {
      const spool = makeSpool({
        estado_trabajo: 'PAUSADO',
        operacion_actual: 'ARM',
        total_uniones: 10,
        uniones_arm_completadas: 5,
      });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['ARM']);
    });

    it('returns [SOLD] for PAUSADO + ARM + arm fully done (arm == total)', () => {
      const spool = makeSpool({
        estado_trabajo: 'PAUSADO',
        operacion_actual: 'ARM',
        total_uniones: 10,
        uniones_arm_completadas: 10,
      });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['SOLD']);
    });

    it('returns [SOLD] for PAUSADO + ARM + arm exceeds total (defensive)', () => {
      const spool = makeSpool({
        estado_trabajo: 'PAUSADO',
        operacion_actual: 'ARM',
        total_uniones: 10,
        uniones_arm_completadas: 12,
      });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['SOLD']);
    });

    it('returns [ARM] for PAUSADO + ARM + null uniones (fallback ARM)', () => {
      const spool = makeSpool({
        estado_trabajo: 'PAUSADO',
        operacion_actual: 'ARM',
        total_uniones: null,
        uniones_arm_completadas: null,
      });
      // When we cannot determine, default to ARM (partial ARM still in progress)
      expect(getValidOperations(spool)).toEqual<Operation[]>(['ARM']);
    });

    it('returns [ARM] for PAUSADO + ARM + zero total (edge case)', () => {
      const spool = makeSpool({
        estado_trabajo: 'PAUSADO',
        operacion_actual: 'ARM',
        total_uniones: 0,
        uniones_arm_completadas: 0,
      });
      // 0 == 0 -> technically done, but 0 total_uniones means no unions -> ARM
      // Backend guards against this upstream. We return ARM when total is 0.
      expect(getValidOperations(spool)).toEqual<Operation[]>(['ARM']);
    });
  });

  describe('COMPLETADO -> MET only', () => {
    it('returns [MET] for COMPLETADO spool', () => {
      const spool = makeSpool({ estado_trabajo: 'COMPLETADO' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['MET']);
    });
  });

  describe('PENDIENTE_METROLOGIA -> MET only', () => {
    it('returns [MET] for PENDIENTE_METROLOGIA spool', () => {
      const spool = makeSpool({ estado_trabajo: 'PENDIENTE_METROLOGIA' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['MET']);
    });
  });

  describe('RECHAZADO -> REP only', () => {
    it('returns [REP] for RECHAZADO spool', () => {
      const spool = makeSpool({ estado_trabajo: 'RECHAZADO' });
      expect(getValidOperations(spool)).toEqual<Operation[]>(['REP']);
    });
  });

  describe('BLOQUEADO -> empty', () => {
    it('returns [] for BLOQUEADO spool', () => {
      const spool = makeSpool({ estado_trabajo: 'BLOQUEADO' });
      expect(getValidOperations(spool)).toEqual<Operation[]>([]);
    });
  });

  describe('null estado_trabajo -> empty', () => {
    it('returns [] for null estado_trabajo', () => {
      const spool = makeSpool({ estado_trabajo: null });
      expect(getValidOperations(spool)).toEqual<Operation[]>([]);
    });
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
