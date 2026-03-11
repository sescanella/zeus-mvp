/**
 * Integration tests for app/page.tsx — v5.0 single-page modal orchestration
 *
 * Tests cover:
 * 1.  Renders "Anadir Spool" button and SpoolCardList
 * 2.  "Anadir Spool" button opens AddSpoolModal
 * 3.  AddSpoolModal.onAdd calls addSpool and closes modal
 * 4.  Card click sets selectedSpool and opens OperationModal
 * 5.  OperationModal.onSelectOperation stores operation and opens ActionModal
 * 6.  OperationModal.onSelectMet opens MetrologiaModal
 * 7.  ActionModal.onSelectAction stores action and opens WorkerModal
 * 8.  WorkerModal.onComplete clears modals, refreshes card, shows success toast
 * 9.  MetrologiaModal APROBADO removes spool from list and shows toast
 * 10. MetrologiaModal RECHAZADO keeps spool and shows toast
 * 11. CANCELAR on libre spool (ocupado_por=null) calls removeSpool only (no API)
 * 12. CANCELAR on occupied ARM spool calls finalizarSpool then removeSpool
 * 13. CANCELAR on REPARACION spool calls cancelarReparacion then removeSpool
 * 14. Polling calls refreshAll every 30s (fake timers)
 * 15. alreadyTracked passed to AddSpoolModal contains current spool tags
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
    ocupado_por: null,
    fecha_ocupacion: null,
    estado_detalle: null,
    total_uniones: null,
    uniones_arm_completadas: null,
    uniones_sold_completadas: null,
    pulgadas_arm: null,
    pulgadas_sold: null,
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
        <button onClick={() => (props.onCancel as () => void)()}>
          action-CANCELAR
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
        <button
          data-testid="remove-OT-001"
          onClick={() => (props.onRemove as (tag: string) => void)('OT-001')}
        >
          remove
        </button>
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

jest.mock('@/lib/api', () => ({
  finalizarSpool: jest.fn(),
  cancelarReparacion: jest.fn(),
}));

import { finalizarSpool, cancelarReparacion } from '@/lib/api';
const mockFinalizarSpool = finalizarSpool as jest.MockedFunction<typeof finalizarSpool>;
const mockCancelarReparacion = cancelarReparacion as jest.MockedFunction<
  typeof cancelarReparacion
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
});

// ─── Tests ────────────────────────────────────────────────────────────────────

// Dynamic import to avoid top-level import (SWC mock hoisting)
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Page = require('@/app/page').default;

describe('Page — v5.0 single-page modal orchestration', () => {
  // ── Test 1 ─────────────────────────────────────────────────────────────────
  it('renders Anadir Spool button and SpoolCardList', () => {
    render(<Page />);

    expect(
      screen.getByRole('button', { name: /anadir spool/i })
    ).toBeInTheDocument();
    expect(screen.getByTestId('spool-card-list')).toBeInTheDocument();
  });

  // ── Test 2 ─────────────────────────────────────────────────────────────────
  it('Anadir Spool button opens AddSpoolModal', () => {
    render(<Page />);

    expect(screen.queryByTestId('add-spool-modal')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /anadir spool/i }));

    expect(screen.getByTestId('add-spool-modal')).toBeInTheDocument();
  });

  // ── Test 3 ─────────────────────────────────────────────────────────────────
  it('AddSpoolModal.onAdd calls addSpool and closes modal', async () => {
    render(<Page />);

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /anadir spool/i }));
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
  it('CANCELAR on libre spool calls removeSpool only (no API)', async () => {
    // SPOOL_A has ocupado_por: null (libre)
    render(<Page />);

    // Navigate to ActionModal
    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-ARM'));
    expect(screen.getByTestId('action-modal')).toBeInTheDocument();

    // Trigger CANCELAR
    await act(async () => {
      fireEvent.click(screen.getByText('action-CANCELAR'));
    });

    // No API calls
    expect(mockFinalizarSpool).not.toHaveBeenCalled();
    expect(mockCancelarReparacion).not.toHaveBeenCalled();

    // removeSpool called
    expect(mockRemoveSpool).toHaveBeenCalledWith('OT-001');

    // Modals closed
    expect(screen.queryByTestId('action-modal')).not.toBeInTheDocument();
  });

  // ── Test 12 ────────────────────────────────────────────────────────────────
  it('CANCELAR on occupied ARM spool calls finalizarSpool then removeSpool', async () => {
    // Mutate mockSpools so useSpoolList returns occupied spool
    mockSpools = [
      makeSpoolCard('OT-001', {
        ocupado_por: 'MR(93)',
        operacion_actual: 'ARM',
      }),
      SPOOL_B,
    ];

    mockFinalizarSpool.mockResolvedValue({
      success: true,
      tag_spool: 'OT-001',
      message: 'Cancelled',
      action_taken: 'CANCELADO' as const,
      unions_processed: 0,
      pulgadas: null,
      metrologia_triggered: false,
      new_state: null,
    });

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-ARM'));

    await act(async () => {
      fireEvent.click(screen.getByText('action-CANCELAR'));
    });

    expect(mockFinalizarSpool).toHaveBeenCalledWith(
      expect.objectContaining({
        tag_spool: 'OT-001',
        worker_id: 93,
        operacion: 'ARM',
        selected_unions: [],
      })
    );
    expect(mockRemoveSpool).toHaveBeenCalledWith('OT-001');
  });

  // ── Test 13 ────────────────────────────────────────────────────────────────
  it('CANCELAR on REPARACION spool calls cancelarReparacion then removeSpool', async () => {
    // Mutate mockSpools so useSpoolList returns REPARACION spool
    mockSpools = [
      makeSpoolCard('OT-001', {
        ocupado_por: 'MR(93)',
        operacion_actual: 'REPARACION',
      }),
      SPOOL_B,
    ];

    mockCancelarReparacion.mockResolvedValue({
      success: true,
      message: 'Cancelled',
      tag_spool: 'OT-001',
    });

    render(<Page />);

    fireEvent.click(screen.getByTestId('card-OT-001'));
    fireEvent.click(screen.getByText('select-ARM'));

    await act(async () => {
      fireEvent.click(screen.getByText('action-CANCELAR'));
    });

    expect(mockCancelarReparacion).toHaveBeenCalledWith(
      expect.objectContaining({
        tag_spool: 'OT-001',
        worker_id: 93,
      })
    );
    expect(mockRemoveSpool).toHaveBeenCalledWith('OT-001');
  });

  // ── Test 14 ────────────────────────────────────────────────────────────────
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
    fireEvent.click(screen.getByRole('button', { name: /anadir spool/i }));

    // Check alreadyTracked contains both spool tags
    expect(capturedAddSpoolModalProps.alreadyTracked).toEqual([
      'OT-001',
      'OT-002',
    ]);
  });
});
