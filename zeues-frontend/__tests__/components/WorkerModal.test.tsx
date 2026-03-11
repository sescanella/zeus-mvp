import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { WorkerModal } from '@/components/WorkerModal';
import type { SpoolCardData } from '@/lib/types';

// ─── Mock API ──────────────────────────────────────────────────────────────────
jest.mock('@/lib/api', () => ({
  getWorkers: jest.fn(),
  iniciarSpool: jest.fn(),
  finalizarSpool: jest.fn(),
  tomarReparacion: jest.fn(),
  pausarReparacion: jest.fn(),
  completarReparacion: jest.fn(),
}));

import {
  getWorkers,
  iniciarSpool,
  finalizarSpool,
  tomarReparacion,
  pausarReparacion,
  completarReparacion,
} from '@/lib/api';

const mockGetWorkers = getWorkers as jest.MockedFunction<typeof getWorkers>;
const mockIniciarSpool = iniciarSpool as jest.MockedFunction<typeof iniciarSpool>;
const mockFinalizarSpool = finalizarSpool as jest.MockedFunction<typeof finalizarSpool>;
const mockTomarReparacion = tomarReparacion as jest.MockedFunction<typeof tomarReparacion>;
const mockPausarReparacion = pausarReparacion as jest.MockedFunction<typeof pausarReparacion>;
const mockCompletarReparacion = completarReparacion as jest.MockedFunction<typeof completarReparacion>;

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const baseSpool: SpoolCardData = {
  tag_spool: 'OT-001',
  ocupado_por: null,
  fecha_ocupacion: null,
  estado_detalle: null,
  total_uniones: 5,
  uniones_arm_completadas: null,
  uniones_sold_completadas: null,
  pulgadas_arm: null,
  pulgadas_sold: null,
  operacion_actual: null,
  estado_trabajo: 'LIBRE',
  ciclo_rep: null,
};

const armadorWorker = {
  id: 10,
  nombre: 'Juan',
  apellido: 'Perez',
  roles: ['Armador'],
  activo: true,
  nombre_completo: 'JP(10)',
};

const soldadorWorker = {
  id: 20,
  nombre: 'Maria',
  apellido: 'Garcia',
  roles: ['Soldador'],
  activo: true,
  nombre_completo: 'MG(20)',
};

const ayudanteWorker = {
  id: 30,
  nombre: 'Pedro',
  apellido: 'Lopez',
  roles: ['Ayudante'],
  activo: true,
  nombre_completo: 'PL(30)',
};

const metrologiaWorker = {
  id: 40,
  nombre: 'Carlos',
  apellido: 'Ruiz',
  roles: ['Metrologia'],
  activo: true,
  nombre_completo: 'CR(40)',
};

const allWorkers = [armadorWorker, soldadorWorker, ayudanteWorker, metrologiaWorker];

const defaultProps = {
  isOpen: true,
  spool: baseSpool,
  operation: 'ARM' as const,
  action: 'INICIAR' as const,
  onComplete: jest.fn(),
  onClose: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetWorkers.mockResolvedValue(allWorkers);
});

// ─── Worker Fetching ──────────────────────────────────────────────────────────

describe('WorkerModal — worker fetching', () => {
  it('fetches workers via getWorkers() on open', async () => {
    render(<WorkerModal {...defaultProps} />);
    await waitFor(() => {
      expect(mockGetWorkers).toHaveBeenCalledTimes(1);
    });
  });

  it('shows loading state while fetching workers', () => {
    // Mock never resolves during this test
    mockGetWorkers.mockReturnValue(new Promise(() => {}));
    render(<WorkerModal {...defaultProps} />);
    expect(screen.getByText(/CARGANDO/i)).toBeInTheDocument();
  });

  it('does not fetch workers when modal is closed', () => {
    render(<WorkerModal {...defaultProps} isOpen={false} />);
    expect(mockGetWorkers).not.toHaveBeenCalled();
  });
});

// ─── Worker Filtering (MODAL-03) ──────────────────────────────────────────────

describe('WorkerModal — worker filtering (MODAL-03)', () => {
  it('filters ARM operation — shows Armador and Ayudante, not Soldador', async () => {
    render(<WorkerModal {...defaultProps} operation="ARM" />);
    await waitFor(() => {
      expect(screen.getByText('JP(10)')).toBeInTheDocument(); // Armador
      expect(screen.getByText('PL(30)')).toBeInTheDocument(); // Ayudante
      expect(screen.queryByText('MG(20)')).not.toBeInTheDocument(); // Soldador — filtered out
      expect(screen.queryByText('CR(40)')).not.toBeInTheDocument(); // Metrologia — filtered out
    });
  });

  it('filters SOLD operation — shows Soldador and Ayudante, not Armador', async () => {
    render(<WorkerModal {...defaultProps} operation="SOLD" />);
    await waitFor(() => {
      expect(screen.getByText('MG(20)')).toBeInTheDocument(); // Soldador
      expect(screen.getByText('PL(30)')).toBeInTheDocument(); // Ayudante
      expect(screen.queryByText('JP(10)')).not.toBeInTheDocument(); // Armador — filtered out
      expect(screen.queryByText('CR(40)')).not.toBeInTheDocument(); // Metrologia — filtered out
    });
  });

  it('filters REP operation — shows Armador and Soldador, not Ayudante', async () => {
    render(<WorkerModal {...defaultProps} operation="REP" />);
    await waitFor(() => {
      expect(screen.getByText('JP(10)')).toBeInTheDocument(); // Armador
      expect(screen.getByText('MG(20)')).toBeInTheDocument(); // Soldador
      expect(screen.queryByText('PL(30)')).not.toBeInTheDocument(); // Ayudante — filtered out
      expect(screen.queryByText('CR(40)')).not.toBeInTheDocument(); // Metrologia — filtered out
    });
  });
});

// ─── API Call Routing (MODAL-06, MODAL-08) ────────────────────────────────────

describe('WorkerModal — API routing (MODAL-06)', () => {
  it('INICIAR ARM calls iniciarSpool with correct payload', async () => {
    mockIniciarSpool.mockResolvedValue({
      success: true,
      message: 'OK',
      tag_spool: 'OT-001',
      ocupado_por: 'JP(10)',
    });

    render(<WorkerModal {...defaultProps} operation="ARM" action="INICIAR" />);

    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(mockIniciarSpool).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 10,
        operacion: 'ARM',
      });
    });
  });

  it('INICIAR SOLD calls iniciarSpool with operacion SOLD', async () => {
    mockIniciarSpool.mockResolvedValue({
      success: true,
      message: 'OK',
      tag_spool: 'OT-001',
      ocupado_por: 'MG(20)',
    });

    render(<WorkerModal {...defaultProps} operation="SOLD" action="INICIAR" />);

    await waitFor(() => screen.getByText('MG(20)'));
    fireEvent.click(screen.getByText('MG(20)'));

    await waitFor(() => {
      expect(mockIniciarSpool).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 20,
        operacion: 'SOLD',
      });
    });
  });

  it('FINALIZAR ARM calls finalizarSpool with action_override COMPLETAR (MODAL-08)', async () => {
    mockFinalizarSpool.mockResolvedValue({
      success: true,
      tag_spool: 'OT-001',
      message: 'Completado',
      action_taken: 'COMPLETAR',
      unions_processed: 5,
      pulgadas: 10.0,
      metrologia_triggered: false,
      new_state: null,
    });

    render(<WorkerModal {...defaultProps} operation="ARM" action="FINALIZAR" />);

    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(mockFinalizarSpool).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 10,
        operacion: 'ARM',
        action_override: 'COMPLETAR',
      });
    });
    // Must NOT include selected_unions
    expect(mockFinalizarSpool).not.toHaveBeenCalledWith(
      expect.objectContaining({ selected_unions: expect.anything() })
    );
  });

  it('PAUSAR ARM calls finalizarSpool with action_override PAUSAR (MODAL-08)', async () => {
    mockFinalizarSpool.mockResolvedValue({
      success: true,
      tag_spool: 'OT-001',
      message: 'Pausado',
      action_taken: 'PAUSAR',
      unions_processed: 0,
      pulgadas: null,
      metrologia_triggered: false,
      new_state: null,
    });

    render(<WorkerModal {...defaultProps} operation="ARM" action="PAUSAR" />);

    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(mockFinalizarSpool).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 10,
        operacion: 'ARM',
        action_override: 'PAUSAR',
      });
    });
  });

  it('INICIAR REP calls tomarReparacion', async () => {
    mockTomarReparacion.mockResolvedValue({
      success: true,
      message: 'Tomado',
      tag_spool: 'OT-001',
    });

    render(<WorkerModal {...defaultProps} operation="REP" action="INICIAR" />);

    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(mockTomarReparacion).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 10,
      });
    });
  });

  it('FINALIZAR REP calls completarReparacion', async () => {
    mockCompletarReparacion.mockResolvedValue({
      success: true,
      message: 'Completado',
      tag_spool: 'OT-001',
    });

    render(<WorkerModal {...defaultProps} operation="REP" action="FINALIZAR" />);

    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(mockCompletarReparacion).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 10,
      });
    });
  });

  it('PAUSAR REP calls pausarReparacion', async () => {
    mockPausarReparacion.mockResolvedValue({
      success: true,
      message: 'Pausado',
      tag_spool: 'OT-001',
    });

    render(<WorkerModal {...defaultProps} operation="REP" action="PAUSAR" />);

    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(mockPausarReparacion).toHaveBeenCalledWith({
        tag_spool: 'OT-001',
        worker_id: 10,
      });
    });
  });
});

// ─── Loading / Error / onComplete ─────────────────────────────────────────────

describe('WorkerModal — loading and error states', () => {
  it('shows loading spinner during API call', async () => {
    // Delay the API response
    mockIniciarSpool.mockReturnValue(new Promise(() => {}));

    render(<WorkerModal {...defaultProps} operation="ARM" action="INICIAR" />);
    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    // After click, loading should be visible
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows inline error on API failure', async () => {
    mockIniciarSpool.mockRejectedValue(new Error('Spool ocupado'));

    render(<WorkerModal {...defaultProps} operation="ARM" action="INICIAR" />);
    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Spool ocupado/i)).toBeInTheDocument();
    });
  });

  it('calls onComplete() on successful API call', async () => {
    const onComplete = jest.fn();
    mockIniciarSpool.mockResolvedValue({
      success: true,
      message: 'OK',
      tag_spool: 'OT-001',
      ocupado_por: 'JP(10)',
    });

    render(<WorkerModal {...defaultProps} operation="ARM" action="INICIAR" onComplete={onComplete} />);
    await waitFor(() => screen.getByText('JP(10)'));
    fireEvent.click(screen.getByText('JP(10)'));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
  });
});

// ─── Accessibility ────────────────────────────────────────────────────────────

describe('WorkerModal — accessibility', () => {
  it('has no axe violations', async () => {
    jest.useRealTimers();
    mockGetWorkers.mockResolvedValue([armadorWorker]);
    const { container } = render(<WorkerModal {...defaultProps} />);
    await waitFor(() => screen.getByText('JP(10)'), { timeout: 10000 });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
