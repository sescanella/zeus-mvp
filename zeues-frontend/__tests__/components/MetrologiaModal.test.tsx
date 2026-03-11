import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MetrologiaModal } from '@/components/MetrologiaModal';
import type { SpoolCardData } from '@/lib/types';

// ─── Mock API ──────────────────────────────────────────────────────────────────
jest.mock('@/lib/api', () => ({
  getWorkers: jest.fn(),
  completarMetrologia: jest.fn(),
}));

import { getWorkers, completarMetrologia } from '@/lib/api';

const mockGetWorkers = getWorkers as jest.MockedFunction<typeof getWorkers>;
const mockCompletarMetrologia = completarMetrologia as jest.MockedFunction<typeof completarMetrologia>;

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const baseSpool: SpoolCardData = {
  tag_spool: 'OT-MET',
  ocupado_por: null,
  fecha_ocupacion: null,
  estado_detalle: 'Pendiente metrologia',
  total_uniones: 5,
  uniones_arm_completadas: 5,
  uniones_sold_completadas: 5,
  pulgadas_arm: 10.0,
  pulgadas_sold: 10.0,
  operacion_actual: null,
  estado_trabajo: 'PENDIENTE_METROLOGIA',
  ciclo_rep: null,
};

const metrologiaWorker = {
  id: 40,
  nombre: 'Carlos',
  apellido: 'Ruiz',
  roles: ['Metrologia'],
  activo: true,
  nombre_completo: 'CR(40)',
};

const armadorWorker = {
  id: 10,
  nombre: 'Juan',
  apellido: 'Perez',
  roles: ['Armador'],
  activo: true,
  nombre_completo: 'JP(10)',
};

const defaultProps = {
  isOpen: true,
  spool: baseSpool,
  onComplete: jest.fn(),
  onClose: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetWorkers.mockResolvedValue([metrologiaWorker, armadorWorker]);
  mockCompletarMetrologia.mockResolvedValue({
    message: 'Metrologia completada',
    tag_spool: 'OT-MET',
    resultado: 'APROBADO',
  });
});

// ─── Step 1: resultado selection (MODAL-05) ───────────────────────────────────

describe('MetrologiaModal — step 1: resultado selection (MODAL-05)', () => {
  it('renders APROBADA and RECHAZADA buttons when open', () => {
    render(<MetrologiaModal {...defaultProps} />);
    expect(screen.getByText('APROBADA')).toBeInTheDocument();
    expect(screen.getByText('RECHAZADA')).toBeInTheDocument();
  });

  it('shows spool tag in header', () => {
    render(<MetrologiaModal {...defaultProps} />);
    expect(screen.getByText('OT-MET')).toBeInTheDocument();
  });

  it('shows RESULTADO METROLOGIA title in step 1', () => {
    render(<MetrologiaModal {...defaultProps} />);
    expect(screen.getByText(/RESULTADO METROLOGIA/i)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<MetrologiaModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('APROBADA')).not.toBeInTheDocument();
  });
});

// ─── Step 2: worker selection ─────────────────────────────────────────────────

describe('MetrologiaModal — step 2: worker selection', () => {
  it('fetches workers when open', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    await waitFor(() => {
      expect(mockGetWorkers).toHaveBeenCalledTimes(1);
    });
  });

  it('transitions to worker selection after clicking APROBADA', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => {
      expect(screen.getByText(/SELECCIONAR INSPECTOR/i)).toBeInTheDocument();
    });
  });

  it('transitions to worker selection after clicking RECHAZADA', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('RECHAZADA'));

    await waitFor(() => {
      expect(screen.getByText(/SELECCIONAR INSPECTOR/i)).toBeInTheDocument();
    });
  });

  it('shows only Metrologia workers in step 2 (not Armador)', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => {
      expect(screen.getByText('CR(40)')).toBeInTheDocument(); // Metrologia
      expect(screen.queryByText('JP(10)')).not.toBeInTheDocument(); // Armador — filtered out
    });
  });

  it('back button returns to step 1', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => screen.getByText(/SELECCIONAR INSPECTOR/i));

    fireEvent.click(screen.getByText('VOLVER'));

    expect(screen.getByText('APROBADA')).toBeInTheDocument();
    expect(screen.getByText('RECHAZADA')).toBeInTheDocument();
  });
});

// ─── API call (MODAL-06) ──────────────────────────────────────────────────────

describe('MetrologiaModal — API call (MODAL-06)', () => {
  it('calls completarMetrologia with APROBADO after selecting APROBADA + worker', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => screen.getByText('CR(40)'));
    fireEvent.click(screen.getByText('CR(40)'));

    await waitFor(() => {
      expect(mockCompletarMetrologia).toHaveBeenCalledWith('OT-MET', 40, 'APROBADO');
    });
  });

  it('calls completarMetrologia with RECHAZADO after selecting RECHAZADA + worker', async () => {
    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('RECHAZADA'));

    await waitFor(() => screen.getByText('CR(40)'));
    fireEvent.click(screen.getByText('CR(40)'));

    await waitFor(() => {
      expect(mockCompletarMetrologia).toHaveBeenCalledWith('OT-MET', 40, 'RECHAZADO');
    });
  });

  it('shows loading spinner during API call (MODAL-06)', async () => {
    mockCompletarMetrologia.mockReturnValue(new Promise(() => {}));

    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => screen.getByText('CR(40)'));
    fireEvent.click(screen.getByText('CR(40)'));

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows inline error on API failure', async () => {
    mockCompletarMetrologia.mockRejectedValue(new Error('Inspector no autorizado'));

    render(<MetrologiaModal {...defaultProps} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => screen.getByText('CR(40)'));
    fireEvent.click(screen.getByText('CR(40)'));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Inspector no autorizado/i)).toBeInTheDocument();
    });
  });

  it('calls onComplete with resultado on success (MODAL-06)', async () => {
    const onComplete = jest.fn();

    render(<MetrologiaModal {...defaultProps} onComplete={onComplete} />);
    fireEvent.click(screen.getByText('APROBADA'));

    await waitFor(() => screen.getByText('CR(40)'));
    fireEvent.click(screen.getByText('CR(40)'));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('APROBADO');
    });
  });

  it('calls onComplete with RECHAZADO on success', async () => {
    const onComplete = jest.fn();

    render(<MetrologiaModal {...defaultProps} onComplete={onComplete} />);
    fireEvent.click(screen.getByText('RECHAZADA'));

    await waitFor(() => screen.getByText('CR(40)'));
    fireEvent.click(screen.getByText('CR(40)'));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('RECHAZADO');
    });
  });
});

// ─── Accessibility ────────────────────────────────────────────────────────────

describe('MetrologiaModal — accessibility', () => {
  it('has no axe violations', async () => {
    jest.useRealTimers();
    mockGetWorkers.mockResolvedValue([metrologiaWorker]);
    const { container } = render(<MetrologiaModal {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
