/**
 * Integration tests for app/page.tsx — v5.0 single-page modal orchestration
 *
 * Tests cover:
 * 1.  Renders "Añadir Spool" button and SpoolCardList
 * 2.  "Añadir Spool" button opens AddSpoolModal
 * 3.  AddSpoolModal.onAdd calls addSpool and closes modal
 * 4.  Card click sets selectedSpool and opens OperationModal
 * 5.  OperationModal.onSelectOperation stores operation and opens ActionModal
 * 6.  OperationModal.onSelectMet opens MetrologiaModal
 * 7.  ActionModal.onSelectAction stores action and opens WorkerModal
 * 8.  WorkerModal.onComplete clears modals, refreshes card, shows success toast
 * 9.  MetrologiaModal APROBADO removes spool from list and shows toast
 * 10. MetrologiaModal RECHAZADO keeps spool and shows toast
 * 11. Polling calls refreshAll every 30s (fake timers)
 * 12. alreadyTracked passed to AddSpoolModal contains current spool tags
 *
 * Reference: 04-02-PLAN.md Task 1
 */

import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';

// ─── Mock data ────────────────────────────────────────────────────────────────

import type { SpoolCardData } from '@/lib/types';
import type { Operation, Action } from '@/lib/spool-state-machine';

function makeSpoolCard(
  tag: string,
  overrides: Partial<SpoolCardData> = {}
): SpoolCardData {
  return {
    tag_spool: tag,
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
    estado_trabajo: 'LIBRE',
    ciclo_rep: null,
    ...overrides,
  };
}

const SPOOL_A = makeSpoolCard('OT-001');
const SPOOL_B = makeSpoolCard('OT-002');

// ─── Mock state ───────────────────────────────────────────────────────────────

// Mutable so individual tests can swap to occupied/reparacion spools
let mockSpools: SpoolCardData[] = [SPOOL_A, SPOOL_B];
const mockAddSpool = jest.fn();
const mockRemoveSpool = jest.fn();
const mockRefreshAll = jest.fn();
const mockRefreshSingle = jest.fn();

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('@/lib/SpoolListContext', () => ({
  SpoolListProvider: (props: { children: React.ReactNode }) => props.children,
  // Uses closure over mockSpools — tests can mutate mockSpools before render
  useSpoolList: () => ({
    spools: mockSpools,
    addSpool: mockAddSpool,
    removeSpool: mockRemoveSpool,
    refreshAll: mockRefreshAll,
    refreshSingle: mockRefreshSingle,
  }),
}));

// Captured props from mocked modals so tests can call their callbacks
let capturedAddSpoolModalProps: Record<string, unknown> = {};
let capturedOperationModalProps: Record<string, unknown> = {};
let capturedActionModalProps: Record<string, unknown> = {};
let capturedWorkerModalProps: Record<string, unknown> = {};
let capturedMetrologiaModalProps: Record<string, unknown> = {};
let capturedSpoolCardListProps: Record<string, unknown> = {};

jest.mock('@/components/AddSpoolModal', () => ({
  AddSpoolModal: (props: Record<string, unknown>) => {
    capturedAddSpoolModalProps = props;
    if (!props.isOpen) return null;
    return (
      <div data-testid="add-spool-modal">
        <button onClick={() => (props.onAdd as (tag: string) => void)('OT-999')}>
          add-OT-999
        </button>
        <button onClick={() => (props.onClose as () => void)()}>
          close-add-spool
        </button>
      </div>
    );
  },
}));

jest.mock('@/components/OperationModal', () => ({
  OperationModal: (props: Record<string, unknown>) => {
    capturedOperationModalProps = props;
    if (!props.isOpen) return null;
    return (
      <div data-testid="operation-modal">
        <button
          onClick={() =>
            (props.onSelectOperation as (op: Operation) => void)('ARM')
          }
        >
          select-ARM
        </button>
        <button onClick={() => (props.onSelectMet as () => void)()}>
          select-MET
        </button>
        <button onClick={() => (props.onClose as () => void)()}>
          close-operation
        </button>
      </div>
    );
  },
}));

jest.mock('@/components/ActionModal', () => ({
  ActionModal: (props: Record<string, unknown>) => {
    capturedActionModalProps = props;
    if (!props.isOpen) return null;
    return (
      <div data-testid="action-modal">
        <button
          onClick={() =>
            (props.onSelectAction as (action: Action) => void)('INICIAR')
          }
        >
          select-INICIAR
        </button>
        <button onClick={() => (props.onClose as () => void)()}>
          close-action
        </button>
      </div>
    );
  },
}));

jest.mock('@/components/WorkerModal', () => ({
  WorkerModal: (props: Record<string, unknown>) => {
    capturedWorkerModalProps = props;
    if (!props.isOpen) return null;
    return (
      <div data-testid="worker-modal">
        <button onClick={() => (props.onComplete as () => void)()}>
          worker-complete
        </button>
        <button onClick={() => (props.onClose as () => void)()}>
          close-worker
        </button>
      </div>
    );
  },
}));

jest.mock('@/components/MetrologiaModal', () => ({
  MetrologiaModal: (props: Record<string, unknown>) => {
    capturedMetrologiaModalProps = props;
    if (!props.isOpen) return null;
    return (
      <div data-testid="metrologia-modal">
        <button
          onClick={() =>
            (props.onComplete as (r: 'APROBADO' | 'RECHAZADO') => void)(
              'APROBADO'
            )
          }
        >
          met-APROBADO
        </button>
        <button
          onClick={() =>
            (props.onComplete as (r: 'APROBADO' | 'RECHAZADO') => void)(
              'RECHAZADO'
            )
          }
        >
          met-RECHAZADO
        </button>
        <button onClick={() => (props.onClose as () => void)()}>
          close-metrologia
        </button>
      </div>
    );
  },
}));

jest.mock('@/components/SpoolCardList', () => ({
  SpoolCardList: (props: Record<string, unknown>) => {
    capturedSpoolCardListProps = props;
    const spools = props.spools as SpoolCardData[];
    return (
      <div data-testid="spool-card-list">
        {spools.map((s) => (
          <button
            key={s.tag_spool}
            data-testid={`card-${s.tag_spool}`}
            onClick={() =>
              (props.onCardClick as (spool: SpoolCardData) => void)(s)
            }
          >
            {s.tag_spool}
          </button>
        ))}
      </div>
    );
  },
}));

jest.mock('@/components/NotificationToast', () => ({
  NotificationToast: (props: Record<string, unknown>) => {
    const toasts = props.toasts as Array<{ id: string; message: string; type: string }>;
    return (
      <div data-testid="notification-toast">
        {toasts.map((t) => (
          <div key={t.id} data-testid={`toast-${t.type}`}>
            {t.message}
          </div>
        ))}
      </div>
    );
  },
}));

// Captured props from UnionesModal so T-111 tests can drive its onComplete.
let capturedUnionesModalProps: Record<string, unknown> = {};

jest.mock('@/components/UnionesModal', () => ({
  UnionesModal: (props: Record<string, unknown>) => {
    capturedUnionesModalProps = props;
    if (!props.isOpen) return null;
    return (
      <div data-testid="uniones-modal">
        <button
          onClick={() =>
            (props.onComplete as (ids: string[]) => void)(['u1', 'u2', 'u3'])
          }
        >
          uniones-finalizar
        </button>
        <button
          onClick={() => (props.onComplete as (ids: string[]) => void)([])}
        >
          uniones-pausar-empty
        </button>
      </div>
    );
  },
}));

jest.mock('@/lib/api', () => {
  // Keep the real ApiError class so error-classifier's `instanceof ApiError`
  // check still works inside tests that simulate API failures.
  const actual = jest.requireActual('@/lib/api');
  return {
    ...actual,
    finalizarSpool: jest.fn(),
    cancelarReparacion: jest.fn(),
    completarReparacion: jest.fn(),
    pausarReparacion: jest.fn(),
    iniciarSpool: jest.fn(),
  };
});

import {
  finalizarSpool,
  cancelarReparacion,
  completarReparacion,
  pausarReparacion,
} from '@/lib/api';
const mockFinalizarSpool = finalizarSpool as jest.MockedFunction<typeof finalizarSpool>;
const mockCancelarReparacion = cancelarReparacion as jest.MockedFunction<
  typeof cancelarReparacion
>;
const mockCompletarReparacion = completarReparacion as jest.MockedFunction<
  typeof completarReparacion
>;
const mockPausarReparacion = pausarReparacion as jest.MockedFunction<
  typeof pausarReparacion
>;

// ─── Setup / Teardown ─────────────────────────────────────────────────────────

beforeEach(() => {
  // Reset mockSpools to default libre spools
  mockSpools = [SPOOL_A, SPOOL_B];
  jest.clearAllMocks();
  capturedAddSpoolModalProps = {};
  capturedOperationModalProps = {};
  capturedActionModalProps = {};
  capturedWorkerModalProps = {};
  capturedMetrologiaModalProps = {};
  capturedSpoolCardListProps = {};
  capturedUnionesModalProps = {};
});

// ─── Tests ────────────────────────────────────────────────────────────────────

// Dynamic import to avoid top-level import (SWC mock hoisting)
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Page = require('@/app/page').default;

describe('Page — v5.0 single-page modal orchestration', () => {
  // ── Test 1 ─────────────────────────────────────────────────────────────────
  it('renders Añadir Spool button and SpoolCardList', () => {
    render(<Page />);

    expect(
      screen.getByRole('button', { name: /añadir spool/i })
    ).toBeInTheDocument();
    expect(screen.getByTestId('spool-card-list')).toBeInTheDocument();
  });

  // ── Test 2 ─────────────────────────────────────────────────────────────────
  it('Añadir Spool button opens AddSpoolModal', () => {
    render(<Page />);

    expect(screen.queryByTestId('add-spool-modal')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /añadir spool/i }));

    expect(screen.getByTestId('add-spool-modal')).toBeInTheDocument();
  });

  // ── Test 3 ─────────────────────────────────────────────────────────────────
  it('AddSpoolModal.onAdd calls addSpool and closes modal', async () => {
    render(<Page />);

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /añadir spool/i }));
    expect(screen.getByTestId('add-spool-modal')).toBeInTheDocument();

    // Trigger onAdd
    await act(async () => {
      fireEvent.click(screen.getByText('add-OT-999'));
    });

    expect(mockAddSpool).toHaveBeenCalledWith('OT-999');
    // Modal should be closed
    expect(screen.queryByTestId('add-spool-modal')).not.toBeInTheDocument();
  });

  // ── Test 4 ─────────────────────────────────────────────────────────────────
  it('card click sets selectedSpool and opens OperationModal', () => {
    render(<Page />);

    expect(screen.queryByTestId('operation-modal')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('card-OT-001'));

    expect(screen.getByTestId('operation-modal')).toBeInTheDocument();
    // The spool prop should be SPOOL_A
    expect(capturedOperationModalProps.spool).toEqual(SPOOL_A);
  });

  // ── Test 5 ─────────────────────────────────────────────────────────────────
  it('OperationModal.onSelectOperation stores operation and opens ActionModal', () => {
    render(<Page />);

    // Open operation modal via card click
    fireEvent.click(screen.getByTestId('card-OT-001'));
    expect(screen.getByTestId('operation-modal')).toBeInTheDocument();

    // Select ARM
    fireEvent.click(screen.getByText('select-ARM'));

    expect(screen.getByTestId('action-modal')).toBeInTheDocument();
    expect(capturedActionModalProps.operation).toBe('ARM');
  });

  // ── Test 6 ─────────────────────────────────────────────────────────────────
  it('OperationModal.onSelectMet opens MetrologiaModal', () => {
    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    expect(screen.getByTestId('operation-modal')).toBeInTheDocument();

    fireEvent.click(screen.getByText('select-MET'));

    expect(screen.getByTestId('metrologia-modal')).toBeInTheDocument();
  });

  // ── Test 7 ─────────────────────────────────────────────────────────────────
  it('ActionModal.onSelectAction stores action and opens WorkerModal', () => {
    render(<Page />);

    // Navigate to ActionModal
    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-ARM'));
    expect(screen.getByTestId('action-modal')).toBeInTheDocument();

    // Select INICIAR
    fireEvent.click(screen.getByText('select-INICIAR'));

    expect(screen.getByTestId('worker-modal')).toBeInTheDocument();
    expect(capturedWorkerModalProps.action).toBe('INICIAR');
  });

  // ── Test 8 ─────────────────────────────────────────────────────────────────
  it('WorkerModal.onComplete clears modals, refreshes card, shows success toast', async () => {
    mockRefreshSingle.mockResolvedValue(undefined);
    render(<Page />);

    // Navigate to WorkerModal
    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-ARM'));
    fireEvent.click(screen.getByText('select-INICIAR'));
    expect(screen.getByTestId('worker-modal')).toBeInTheDocument();

    // Complete worker action
    await act(async () => {
      fireEvent.click(screen.getByText('worker-complete'));
    });

    // Modals closed
    expect(screen.queryByTestId('worker-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('action-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('operation-modal')).not.toBeInTheDocument();

    // refreshSingle called with spool tag
    expect(mockRefreshSingle).toHaveBeenCalledWith('OT-001');

    // Toast shown
    await waitFor(() => {
      expect(screen.getByTestId('toast-success')).toBeInTheDocument();
    });
  });

  // ── Test 9 ─────────────────────────────────────────────────────────────────
  it('MetrologiaModal APROBADO removes spool from list and shows toast', async () => {
    render(<Page />);

    // Navigate to MetrologiaModal
    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-MET'));
    expect(screen.getByTestId('metrologia-modal')).toBeInTheDocument();

    // Complete with APROBADO
    await act(async () => {
      fireEvent.click(screen.getByText('met-APROBADO'));
    });

    // Modals closed
    expect(screen.queryByTestId('metrologia-modal')).not.toBeInTheDocument();

    // removeSpool called
    expect(mockRemoveSpool).toHaveBeenCalledWith('OT-001');

    // Toast shown
    await waitFor(() => {
      expect(screen.getByTestId('toast-success')).toBeInTheDocument();
    });
  });

  // ── Test 10 ────────────────────────────────────────────────────────────────
  it('MetrologiaModal RECHAZADO keeps spool and shows toast', async () => {
    mockRefreshSingle.mockResolvedValue(undefined);
    render(<Page />);

    // Navigate to MetrologiaModal
    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-MET'));

    // Complete with RECHAZADO
    await act(async () => {
      fireEvent.click(screen.getByText('met-RECHAZADO'));
    });

    // removeSpool NOT called
    expect(mockRemoveSpool).not.toHaveBeenCalled();

    // refreshSingle called (card stays but refreshed)
    expect(mockRefreshSingle).toHaveBeenCalledWith('OT-001');

    // Toast shown
    await waitFor(() => {
      expect(screen.getByTestId('toast-success')).toBeInTheDocument();
    });
  });

  // ── Test 11 ────────────────────────────────────────────────────────────────
  it('polling calls refreshAll every 30s', async () => {
    jest.useFakeTimers();
    mockRefreshAll.mockResolvedValue(undefined);

    render(<Page />);

    // Advance 30 seconds
    await act(async () => {
      jest.advanceTimersByTime(30_000);
    });

    expect(mockRefreshAll).toHaveBeenCalledTimes(1);

    // Advance another 30 seconds
    await act(async () => {
      jest.advanceTimersByTime(30_000);
    });

    expect(mockRefreshAll).toHaveBeenCalledTimes(2);

    jest.useRealTimers();
  });

  // ── Test 15 ────────────────────────────────────────────────────────────────
  it('alreadyTracked passed to AddSpoolModal contains current spool tags', () => {
    render(<Page />);

    // Open add-spool modal
    fireEvent.click(screen.getByRole('button', { name: /añadir spool/i }));

    // Check alreadyTracked contains both spool tags
    expect(capturedAddSpoolModalProps.alreadyTracked).toEqual([
      'OT-001',
      'OT-002',
    ]);
  });

  // ── T-110 — skip OperationModal in deterministic transitions ──────────────
  // Hotspot H2 of the north-star-clicks audit. Saves 2 clicks per spool cycle:
  // one when ARM finishes and SOLD is the only valid next op, one when SOLD
  // finishes and METROLOGIA is the only valid next op.

  it('T-110: ARM_TERM (LIBRE + fecha_armado set, fecha_soldadura null) skips OperationModal and opens WorkerModal directly with operation=SOLD', () => {
    // Mid-cycle spool: ARM completed, SOLD pending. Backend leaves the
    // spool LIBRE (not occupied) until a worker grabs SOLD.
    const armTermSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'LIBRE',
      ocupado_por: null,
      fecha_armado: '21-01-2026',
      fecha_soldadura: null,
      operacion_actual: null,
    });
    mockSpools = [armTermSpool, SPOOL_B];

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));

    // OperationModal NOT shown — skipped.
    expect(screen.queryByTestId('operation-modal')).not.toBeInTheDocument();
    // ActionModal NOT shown — only one valid action (INICIAR), so it skips too.
    expect(screen.queryByTestId('action-modal')).not.toBeInTheDocument();
    // WorkerModal IS shown, pre-set to SOLD + INICIAR.
    expect(screen.getByTestId('worker-modal')).toBeInTheDocument();
    expect(capturedWorkerModalProps.operation).toBe('SOLD');
    expect(capturedWorkerModalProps.action).toBe('INICIAR');
  });

  it('T-110: SOLD_TERM (PENDIENTE_METROLOGIA) skips OperationModal and opens MetrologiaModal directly', () => {
    const soldTermSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'PENDIENTE_METROLOGIA',
      ocupado_por: null,
      fecha_armado: '21-01-2026',
      fecha_soldadura: '22-01-2026',
      operacion_actual: null,
    });
    mockSpools = [soldTermSpool, SPOOL_B];

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));

    // OperationModal NOT shown — skipped.
    expect(screen.queryByTestId('operation-modal')).not.toBeInTheDocument();
    // MetrologiaModal opens directly.
    expect(screen.getByTestId('metrologia-modal')).toBeInTheDocument();
  });

  it('T-110 regression: truly LIBRE spool (no fecha_armado yet) still opens OperationModal', () => {
    // SPOOL_A is the default LIBRE spool with all dates null.
    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));

    // Original behavior preserved: OperationModal shown when no
    // deterministic next step can be inferred.
    expect(screen.getByTestId('operation-modal')).toBeInTheDocument();
  });

  it('T-110 regression: EN_PROGRESO ARM (occupied + operacion_actual=ARM) still skips via existing deriveOperation path', () => {
    const enArmSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'MR(93)',
      operacion_actual: 'ARM',
    });
    mockSpools = [enArmSpool, SPOOL_B];

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));

    // OperationModal NOT shown — existing skip path (deriveOperation
    // returns 'ARM' from operacion_actual) handles this case.
    expect(screen.queryByTestId('operation-modal')).not.toBeInTheDocument();
    // For an occupied spool, getValidActions returns ['FINALIZAR', 'PAUSAR']
    // (length > 1) — so the ActionModal IS shown, asking the user to pick.
    expect(screen.getByTestId('action-modal')).toBeInTheDocument();
    expect(capturedActionModalProps.operation).toBe('ARM');
  });

  // ── T-111 — auto-chain next modal after FINALIZAR ─────────────────────────
  // Hotspot H1 of the north-star-clicks audit. Replicates the post-RECHAZADO
  // handoff pattern (handleMetComplete) so the operator never has to re-click
  // the card after FINALIZAR ARM/SOLD/REP. Saves -5 clicks on the happy-path
  // branch (rama A 26B → 21B post-T-110+T-111).

  it('T-111: FINALIZAR ARM via UnionesModal auto-opens WorkerModal pre-set to SOLD/INICIAR', async () => {
    const enArmSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'MR(93)',
      operacion_actual: 'ARM',
    });
    mockSpools = [enArmSpool, SPOOL_B];
    mockRefreshSingle.mockResolvedValue(undefined);
    mockFinalizarSpool.mockResolvedValue({
      ok: true,
    } as unknown as Awaited<ReturnType<typeof finalizarSpool>>);

    render(<Page />);

    // Walk the user through: card → ActionModal → FINALIZAR → UnionesModal
    fireEvent.click(screen.getByTestId('card-OT-001'));
    // ActionModal shows FINALIZAR + PAUSAR; pick FINALIZAR via the existing
    // mock helper (re-using select-INICIAR button text would be wrong here).
    expect(screen.getByTestId('action-modal')).toBeInTheDocument();
    await act(async () => {
      (capturedActionModalProps.onSelectAction as (a: Action) => void)(
        'FINALIZAR'
      );
    });

    // UnionesModal opens with FINALIZAR semantics
    expect(screen.getByTestId('uniones-modal')).toBeInTheDocument();

    // User submits 3 selected unions
    await act(async () => {
      fireEvent.click(screen.getByText('uniones-finalizar'));
    });

    // T-111 assertion: WorkerModal opens automatically, pre-set to SOLD/INICIAR.
    await waitFor(() => {
      expect(screen.getByTestId('worker-modal')).toBeInTheDocument();
    });
    expect(capturedWorkerModalProps.operation).toBe('SOLD');
    expect(capturedWorkerModalProps.action).toBe('INICIAR');

    // No flash of OperationModal/ActionModal/UnionesModal underneath.
    expect(screen.queryByTestId('operation-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('action-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('uniones-modal')).not.toBeInTheDocument();

    // API call + refresh both happened with the right tag.
    expect(mockFinalizarSpool).toHaveBeenCalledWith(
      expect.objectContaining({
        tag_spool: 'OT-001',
        operacion: 'ARM',
        selected_unions: ['u1', 'u2', 'u3'],
      })
    );
    expect(mockRefreshSingle).toHaveBeenCalledWith('OT-001');
  });

  it('T-111: FINALIZAR SOLD via UnionesModal auto-opens MetrologiaModal', async () => {
    const enSoldSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'JS(45)',
      operacion_actual: 'SOLD',
      fecha_armado: '21-01-2026',
    });
    mockSpools = [enSoldSpool, SPOOL_B];
    mockRefreshSingle.mockResolvedValue(undefined);
    mockFinalizarSpool.mockResolvedValue({
      ok: true,
    } as unknown as Awaited<ReturnType<typeof finalizarSpool>>);

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    await act(async () => {
      (capturedActionModalProps.onSelectAction as (a: Action) => void)(
        'FINALIZAR'
      );
    });
    expect(screen.getByTestId('uniones-modal')).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByText('uniones-finalizar'));
    });

    // T-111 assertion: MetrologiaModal opens automatically.
    await waitFor(() => {
      expect(screen.getByTestId('metrologia-modal')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('worker-modal')).not.toBeInTheDocument();

    expect(mockFinalizarSpool).toHaveBeenCalledWith(
      expect.objectContaining({
        tag_spool: 'OT-001',
        operacion: 'SOLD',
        selected_unions: ['u1', 'u2', 'u3'],
      })
    );
  });

  it('T-111: FINALIZAR REP via direct action auto-opens MetrologiaModal', async () => {
    const enRepSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'PG(12)',
      operacion_actual: 'REPARACION',
    });
    mockSpools = [enRepSpool, SPOOL_B];
    mockRefreshSingle.mockResolvedValue(undefined);
    mockCompletarReparacion.mockResolvedValue({
      ok: true,
    } as unknown as Awaited<ReturnType<typeof completarReparacion>>);

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    expect(screen.getByTestId('action-modal')).toBeInTheDocument();
    // REP path goes through executeDirectAction (no UnionesModal).
    await act(async () => {
      (capturedActionModalProps.onSelectAction as (a: Action) => void)(
        'FINALIZAR'
      );
    });

    // T-111 assertion: MetrologiaModal opens automatically after REP completes.
    await waitFor(() => {
      expect(screen.getByTestId('metrologia-modal')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('worker-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('action-modal')).not.toBeInTheDocument();

    expect(mockCompletarReparacion).toHaveBeenCalledWith({
      tag_spool: 'OT-001',
      worker_id: 12,
    });
    expect(mockRefreshSingle).toHaveBeenCalledWith('OT-001');
  });

  it('T-111 regression: PAUSAR ARM does NOT auto-open the next modal', async () => {
    const enArmSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'MR(93)',
      operacion_actual: 'ARM',
    });
    mockSpools = [enArmSpool, SPOOL_B];
    mockRefreshSingle.mockResolvedValue(undefined);
    mockFinalizarSpool.mockResolvedValue({
      ok: true,
    } as unknown as Awaited<ReturnType<typeof finalizarSpool>>);

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    await act(async () => {
      (capturedActionModalProps.onSelectAction as (a: Action) => void)(
        'PAUSAR'
      );
    });
    expect(screen.getByTestId('uniones-modal')).toBeInTheDocument();

    // PAUSAR with zero selected unions — saves uniones state, marks paused.
    await act(async () => {
      fireEvent.click(screen.getByText('uniones-pausar-empty'));
    });

    // No chain — operator explicitly chose to stop the flow.
    await waitFor(() => {
      expect(screen.queryByTestId('uniones-modal')).not.toBeInTheDocument();
    });
    expect(screen.queryByTestId('worker-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('metrologia-modal')).not.toBeInTheDocument();
  });

  it('T-111 regression: FINALIZAR API failure does NOT auto-open the next modal', async () => {
    const enArmSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'MR(93)',
      operacion_actual: 'ARM',
    });
    mockSpools = [enArmSpool, SPOOL_B];
    mockFinalizarSpool.mockRejectedValue(new Error('API down'));

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    await act(async () => {
      (capturedActionModalProps.onSelectAction as (a: Action) => void)(
        'FINALIZAR'
      );
    });
    expect(screen.getByTestId('uniones-modal')).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByText('uniones-finalizar'));
    });

    // The API rejected — no chain modal opens. The error toast surfaces and
    // the user can retry by re-clicking the card.
    expect(screen.queryByTestId('worker-modal')).not.toBeInTheDocument();
    expect(screen.queryByTestId('metrologia-modal')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('toast-error')).toBeInTheDocument();
    });
  });

  it('T-111 regression: refreshSingle failure does NOT block the chain', async () => {
    const enSoldSpool = makeSpoolCard('OT-001', {
      estado_trabajo: 'EN_PROGRESO',
      ocupado_por: 'JS(45)',
      operacion_actual: 'SOLD',
      fecha_armado: '21-01-2026',
    });
    mockSpools = [enSoldSpool, SPOOL_B];
    mockFinalizarSpool.mockResolvedValue({
      ok: true,
    } as unknown as Awaited<ReturnType<typeof finalizarSpool>>);
    // Simulate refresh blowing up (eg. transient backend hiccup).
    mockRefreshSingle.mockRejectedValue(new Error('refresh blew up'));

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    await act(async () => {
      (capturedActionModalProps.onSelectAction as (a: Action) => void)(
        'FINALIZAR'
      );
    });
    await act(async () => {
      fireEvent.click(screen.getByText('uniones-finalizar'));
    });

    // Chain still happens — MetrologiaModal opens despite the refresh error.
    await waitFor(() => {
      expect(screen.getByTestId('metrologia-modal')).toBeInTheDocument();
    });
    // And a warning toast tells the operator the card may lag.
    await waitFor(() => {
      expect(screen.getByTestId('toast-error')).toBeInTheDocument();
    });
  });

  // Ensure unused mocks don't trigger lint/jest "unused" complaints.
  void mockPausarReparacion;
  void capturedUnionesModalProps;
});
