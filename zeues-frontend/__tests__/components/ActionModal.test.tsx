import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ActionModal } from '@/components/ActionModal';
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
  getValidActions: jest.fn(),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

import { getValidActions } from '@/lib/spool-state-machine';
const mockGetValidActions = getValidActions as jest.Mock;

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
  operation: 'ARM' as const,
  onSelectAction: jest.fn(),
  onCancel: jest.fn(),
  onClose: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
});

// ─── STATE-02: Valid actions per occupation state ─────────────────────────────

describe('ActionModal — STATE-02: valid actions', () => {
  it('libre spool (ocupado_por=null) shows INICIAR + CANCELAR', () => {
    mockGetValidActions.mockReturnValue(['INICIAR', 'CANCELAR']);
    render(<ActionModal {...defaultProps} spool={makeSpool({ ocupado_por: null })} />);
    expect(screen.getByRole('button', { name: /INICIAR/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /CANCELAR/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /FINALIZAR/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /PAUSAR/i })).not.toBeInTheDocument();
  });

  it('occupied spool shows FINALIZAR + PAUSAR + CANCELAR', () => {
    mockGetValidActions.mockReturnValue(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    render(
      <ActionModal
        {...defaultProps}
        spool={makeSpool({ ocupado_por: 'MR(93)', estado_trabajo: 'EN_PROGRESO' })}
      />
    );
    expect(screen.getByRole('button', { name: /FINALIZAR/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /PAUSAR/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /CANCELAR/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /INICIAR/i })).not.toBeInTheDocument();
  });
});

// ─── Callbacks ─────────────────────────────────────────────────────────────────

describe('ActionModal — callbacks', () => {
  it('clicking CANCELAR calls onCancel directly (MODAL-04 — no worker needed)', () => {
    mockGetValidActions.mockReturnValue(['INICIAR', 'CANCELAR']);
    const onCancel = jest.fn();
    const onSelectAction = jest.fn();
    render(
      <ActionModal
        {...defaultProps}
        onCancel={onCancel}
        onSelectAction={onSelectAction}
        spool={makeSpool({ ocupado_por: null })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /CANCELAR/i }));
    expect(onCancel).toHaveBeenCalled();
    expect(onSelectAction).not.toHaveBeenCalled();
  });

  it('clicking INICIAR calls onSelectAction("INICIAR")', () => {
    mockGetValidActions.mockReturnValue(['INICIAR', 'CANCELAR']);
    const onSelectAction = jest.fn();
    render(
      <ActionModal
        {...defaultProps}
        onSelectAction={onSelectAction}
        spool={makeSpool({ ocupado_por: null })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /INICIAR/i }));
    expect(onSelectAction).toHaveBeenCalledWith('INICIAR');
  });

  it('clicking FINALIZAR calls onSelectAction("FINALIZAR")', () => {
    mockGetValidActions.mockReturnValue(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    const onSelectAction = jest.fn();
    render(
      <ActionModal
        {...defaultProps}
        onSelectAction={onSelectAction}
        spool={makeSpool({ ocupado_por: 'MR(93)', estado_trabajo: 'EN_PROGRESO' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /FINALIZAR/i }));
    expect(onSelectAction).toHaveBeenCalledWith('FINALIZAR');
  });

  it('clicking PAUSAR calls onSelectAction("PAUSAR")', () => {
    mockGetValidActions.mockReturnValue(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    const onSelectAction = jest.fn();
    render(
      <ActionModal
        {...defaultProps}
        onSelectAction={onSelectAction}
        spool={makeSpool({ ocupado_por: 'MR(93)', estado_trabajo: 'EN_PROGRESO' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /PAUSAR/i }));
    expect(onSelectAction).toHaveBeenCalledWith('PAUSAR');
  });

  it('CANCELAR in occupied spool still calls onCancel (MODAL-04)', () => {
    mockGetValidActions.mockReturnValue(['FINALIZAR', 'PAUSAR', 'CANCELAR']);
    const onCancel = jest.fn();
    const onSelectAction = jest.fn();
    render(
      <ActionModal
        {...defaultProps}
        onCancel={onCancel}
        onSelectAction={onSelectAction}
        spool={makeSpool({ ocupado_por: 'MR(93)', estado_trabajo: 'EN_PROGRESO' })}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /CANCELAR/i }));
    expect(onCancel).toHaveBeenCalled();
    expect(onSelectAction).not.toHaveBeenCalled();
  });

  it('does not render when isOpen=false', () => {
    mockGetValidActions.mockReturnValue(['INICIAR', 'CANCELAR']);
    render(<ActionModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

// ─── Accessibility ─────────────────────────────────────────────────────────────

describe('ActionModal — accessibility', () => {
  it('has no axe violations', async () => {
    jest.useRealTimers();
    mockGetValidActions.mockReturnValue(['INICIAR', 'CANCELAR']);
    const { container } = render(<ActionModal {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
