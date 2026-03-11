import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { OperationModal } from '@/components/OperationModal';
import type { SpoolCardData } from '@/lib/types';

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('@/components/Modal', () => ({
  Modal: jest.fn((props) =>
    props.isOpen ? (
      <div role="dialog" aria-modal="true" aria-label={props.ariaLabel || 'Modal'}>
        {props.children}
      </div>
    ) : null
  ),
}));

jest.mock('@/lib/spool-state-machine', () => ({
  getValidOperations: jest.fn(),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

import { getValidOperations } from '@/lib/spool-state-machine';
const mockGetValidOperations = getValidOperations as jest.Mock;

function makeSpool(overrides: Partial<SpoolCardData> = {}): SpoolCardData {
  return {
    tag_spool: 'TEST-01',
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

const defaultProps = {
  isOpen: true,
  spool: makeSpool(),
  onSelectOperation: jest.fn(),
  onSelectMet: jest.fn(),
  onClose: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
});

// ─── STATE-01: Valid operations per spool state ───────────────────────────────

describe('OperationModal — STATE-01: valid operations', () => {
  it('LIBRE spool shows only ARM button', () => {
    mockGetValidOperations.mockReturnValue(['ARM']);
    render(<OperationModal {...defaultProps} spool={makeSpool({ estado_trabajo: 'LIBRE' })} />);
    expect(screen.getByRole('button', { name: /ARMADO/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /SOLDADURA/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /METROLOGIA/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /REPARACION/i })).not.toBeInTheDocument();
  });

  it('COMPLETADO spool shows only MET button', () => {
    mockGetValidOperations.mockReturnValue(['MET']);
    render(
      <OperationModal
        {...defaultProps}
        spool={makeSpool({ estado_trabajo: 'COMPLETADO' })}
      />
    );
    expect(screen.getByRole('button', { name: /METROLOGIA/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ARMADO/i })).not.toBeInTheDocument();
  });

  it('RECHAZADO spool shows only REP button', () => {
    mockGetValidOperations.mockReturnValue(['REP']);
    render(
      <OperationModal
        {...defaultProps}
        spool={makeSpool({ estado_trabajo: 'RECHAZADO' })}
      />
    );
    expect(screen.getByRole('button', { name: /REPARACION/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ARMADO/i })).not.toBeInTheDocument();
  });

  it('EN_PROGRESO ARM spool shows only ARM button', () => {
    mockGetValidOperations.mockReturnValue(['ARM']);
    render(
      <OperationModal
        {...defaultProps}
        spool={makeSpool({ estado_trabajo: 'EN_PROGRESO', operacion_actual: 'ARM' })}
      />
    );
    expect(screen.getByRole('button', { name: /ARMADO/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /SOLDADURA/i })).not.toBeInTheDocument();
  });

  it('BLOQUEADO spool shows empty state with no operation buttons', () => {
    mockGetValidOperations.mockReturnValue([]);
    render(
      <OperationModal
        {...defaultProps}
        spool={makeSpool({ estado_trabajo: 'BLOQUEADO' })}
      />
    );
    expect(screen.queryByRole('button', { name: /ARMADO/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /SOLDADURA/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /METROLOGIA/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /REPARACION/i })).not.toBeInTheDocument();
    expect(screen.getByText(/sin operaciones/i)).toBeInTheDocument();
  });
});

// ─── Callbacks ─────────────────────────────────────────────────────────────────

describe('OperationModal — callbacks', () => {
  it('clicking ARM button calls onSelectOperation("ARM")', () => {
    mockGetValidOperations.mockReturnValue(['ARM']);
    const onSelectOperation = jest.fn();
    render(
      <OperationModal
        {...defaultProps}
        onSelectOperation={onSelectOperation}
        spool={makeSpool({ estado_trabajo: 'LIBRE' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /ARMADO/i }));
    expect(onSelectOperation).toHaveBeenCalledWith('ARM');
  });

  it('clicking SOLD button calls onSelectOperation("SOLD")', () => {
    mockGetValidOperations.mockReturnValue(['SOLD']);
    const onSelectOperation = jest.fn();
    render(
      <OperationModal
        {...defaultProps}
        onSelectOperation={onSelectOperation}
        spool={makeSpool({ estado_trabajo: 'PAUSADO', operacion_actual: 'ARM' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /SOLDADURA/i }));
    expect(onSelectOperation).toHaveBeenCalledWith('SOLD');
  });

  it('clicking REP button calls onSelectOperation("REP")', () => {
    mockGetValidOperations.mockReturnValue(['REP']);
    const onSelectOperation = jest.fn();
    render(
      <OperationModal
        {...defaultProps}
        onSelectOperation={onSelectOperation}
        spool={makeSpool({ estado_trabajo: 'RECHAZADO' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /REPARACION/i }));
    expect(onSelectOperation).toHaveBeenCalledWith('REP');
  });

  it('clicking MET button calls onSelectMet() instead of onSelectOperation', () => {
    mockGetValidOperations.mockReturnValue(['MET']);
    const onSelectOperation = jest.fn();
    const onSelectMet = jest.fn();
    render(
      <OperationModal
        {...defaultProps}
        onSelectOperation={onSelectOperation}
        onSelectMet={onSelectMet}
        spool={makeSpool({ estado_trabajo: 'COMPLETADO' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /METROLOGIA/i }));
    expect(onSelectMet).toHaveBeenCalled();
    expect(onSelectOperation).not.toHaveBeenCalled();
  });

  it('does not render when isOpen=false', () => {
    mockGetValidOperations.mockReturnValue(['ARM']);
    render(<OperationModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

// ─── Accessibility ─────────────────────────────────────────────────────────────

describe('OperationModal — accessibility', () => {
  it('has no axe violations', async () => {
    jest.useRealTimers();
    mockGetValidOperations.mockReturnValue(['ARM']);
    const { container } = render(<OperationModal {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
