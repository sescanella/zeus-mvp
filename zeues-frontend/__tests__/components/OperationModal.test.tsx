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

// ─── Fixtures ─────────────────────────────────────────────────────────────────

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

// ─── Always shows all 4 operations ──────────────────────────────────────────

describe('OperationModal — always shows all 4 operations', () => {
  it('shows all 4 operation buttons regardless of spool state', () => {
    render(<OperationModal {...defaultProps} spool={makeSpool({ estado_trabajo: 'LIBRE' })} />);
    expect(screen.getByRole('button', { name: /ARMADO/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /SOLDADURA/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /METROLOGIA/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /REPARACION/i })).toBeInTheDocument();
  });

  it('shows all 4 operations for BLOQUEADO spool', () => {
    render(<OperationModal {...defaultProps} spool={makeSpool({ estado_trabajo: 'BLOQUEADO' })} />);
    expect(screen.getByRole('button', { name: /ARMADO/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /SOLDADURA/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /METROLOGIA/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /REPARACION/i })).toBeInTheDocument();
  });

  it('shows all 4 operations for EN_PROGRESO spool', () => {
    render(<OperationModal {...defaultProps} spool={makeSpool({ estado_trabajo: 'EN_PROGRESO', operacion_actual: 'ARM' })} />);
    expect(screen.getByRole('button', { name: /ARMADO/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /SOLDADURA/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /METROLOGIA/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /REPARACION/i })).toBeInTheDocument();
  });
});

// ─── Callbacks ─────────────────────────────────────────────────────────────────

describe('OperationModal — callbacks', () => {
  it('clicking ARM button calls onSelectOperation("ARM")', () => {
    const onSelectOperation = jest.fn();
    render(<OperationModal {...defaultProps} onSelectOperation={onSelectOperation} />);
    fireEvent.click(screen.getByRole('button', { name: /ARMADO/i }));
    expect(onSelectOperation).toHaveBeenCalledWith('ARM');
  });

  it('clicking SOLD button calls onSelectOperation("SOLD")', () => {
    const onSelectOperation = jest.fn();
    render(<OperationModal {...defaultProps} onSelectOperation={onSelectOperation} />);
    fireEvent.click(screen.getByRole('button', { name: /SOLDADURA/i }));
    expect(onSelectOperation).toHaveBeenCalledWith('SOLD');
  });

  it('clicking REP button calls onSelectOperation("REP")', () => {
    const onSelectOperation = jest.fn();
    render(<OperationModal {...defaultProps} onSelectOperation={onSelectOperation} />);
    fireEvent.click(screen.getByRole('button', { name: /REPARACION/i }));
    expect(onSelectOperation).toHaveBeenCalledWith('REP');
  });

  it('clicking MET button calls onSelectMet() instead of onSelectOperation', () => {
    const onSelectOperation = jest.fn();
    const onSelectMet = jest.fn();
    render(<OperationModal {...defaultProps} onSelectOperation={onSelectOperation} onSelectMet={onSelectMet} />);
    fireEvent.click(screen.getByRole('button', { name: /METROLOGIA/i }));
    expect(onSelectMet).toHaveBeenCalled();
    expect(onSelectOperation).not.toHaveBeenCalled();
  });

  it('does not render when isOpen=false', () => {
    render(<OperationModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

// ─── Accessibility ─────────────────────────────────────────────────────────────

describe('OperationModal — accessibility', () => {
  it('has no axe violations', async () => {
    jest.useRealTimers();
    const { container } = render(<OperationModal {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
