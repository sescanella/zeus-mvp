import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolTable } from '@/components/SpoolTable';
import type { Spool } from '@/lib/types';

const mockSpools: Spool[] = [
  { tag_spool: 'TEST-01', nv: 'NV-2024-001', arm: 0, sold: 0, total_uniones: 0 },
  { tag_spool: 'TEST-02', nv: 'NV-2024-002', arm: 0, sold: 0, total_uniones: 5 },
  { tag_spool: 'TEST-03', nv: 'NV-2024-003', arm: 0, sold: 0, total_uniones: 0 },
];

const defaultProps = {
  spools: mockSpools,
  selectedSpools: [] as string[],
  onToggleSelect: jest.fn(),
  tipo: null as 'tomar' | 'pausar' | 'completar' | 'cancelar' | 'metrologia' | 'reparacion' | null,
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('SpoolTable — rendering', () => {
  it('renders all column headers', () => {
    render(<SpoolTable {...defaultProps} />);
    expect(screen.getByText('SEL')).toBeInTheDocument();
    expect(screen.getByText('NV')).toBeInTheDocument();
    expect(screen.getByText('TAG SPOOL')).toBeInTheDocument();
  });

  it('renders CICLO/ESTADO header for reparacion tipo', () => {
    render(<SpoolTable {...defaultProps} tipo="reparacion" />);
    expect(screen.getByText('CICLO/ESTADO')).toBeInTheDocument();
    expect(screen.queryByText('NV')).not.toBeInTheDocument();
  });

  it('renders all spool rows', () => {
    render(<SpoolTable {...defaultProps} />);
    expect(screen.getByText('TEST-01')).toBeInTheDocument();
    expect(screen.getByText('TEST-02')).toBeInTheDocument();
    expect(screen.getByText('TEST-03')).toBeInTheDocument();
  });

  it('renders NV values', () => {
    render(<SpoolTable {...defaultProps} />);
    expect(screen.getByText('NV-2024-001')).toBeInTheDocument();
    expect(screen.getByText('NV-2024-002')).toBeInTheDocument();
  });
});

describe('SpoolTable — selection', () => {
  it('calls onToggleSelect when row is clicked', () => {
    render(<SpoolTable {...defaultProps} />);
    fireEvent.click(screen.getByText('TEST-01'));
    expect(defaultProps.onToggleSelect).toHaveBeenCalledWith('TEST-01');
  });

  it('calls onToggleSelect on Enter key', () => {
    render(<SpoolTable {...defaultProps} />);
    const row = screen.getByRole('button', { name: /Seleccionar spool TEST-01/ });
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(defaultProps.onToggleSelect).toHaveBeenCalledWith('TEST-01');
  });

  it('calls onToggleSelect on Space key', () => {
    render(<SpoolTable {...defaultProps} />);
    const row = screen.getByRole('button', { name: /Seleccionar spool TEST-01/ });
    fireEvent.keyDown(row, { key: ' ' });
    expect(defaultProps.onToggleSelect).toHaveBeenCalledWith('TEST-01');
  });

  it('shows Deseleccionar label for selected spools', () => {
    render(<SpoolTable {...defaultProps} selectedSpools={['TEST-01']} />);
    expect(screen.getByRole('button', { name: /Deseleccionar spool TEST-01/ })).toBeInTheDocument();
  });

  it('shows Seleccionar label for unselected spools', () => {
    render(<SpoolTable {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Seleccionar spool TEST-01/ })).toBeInTheDocument();
  });
});

describe('SpoolTable — reparacion mode', () => {
  const reparacionSpools: Spool[] = [
    {
      tag_spool: 'REP-01',
      arm: 0,
      sold: 0,
      ...(({ bloqueado: false, cycle: 2 }) as Record<string, unknown>),
    } as Spool,
    {
      tag_spool: 'REP-02',
      arm: 0,
      sold: 0,
      ...(({ bloqueado: true, cycle: 3 }) as Record<string, unknown>),
    } as Spool,
  ];

  it('shows cycle count for non-bloqueado spools', () => {
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={jest.fn()}
        tipo="reparacion"
      />
    );
    expect(screen.getByText('Ciclo 2/3')).toBeInTheDocument();
  });

  it('shows BLOQUEADO text for bloqueado spools', () => {
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={jest.fn()}
        tipo="reparacion"
      />
    );
    expect(screen.getByText('BLOQUEADO - Supervisor')).toBeInTheDocument();
  });

  it('sets tabIndex=-1 for bloqueado rows', () => {
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={jest.fn()}
        tipo="reparacion"
      />
    );
    const bloqueadoRow = screen.getByRole('button', { name: /bloqueado/i });
    expect(bloqueadoRow).toHaveAttribute('tabindex', '-1');
  });

  it('sets aria-disabled for bloqueado rows', () => {
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={jest.fn()}
        tipo="reparacion"
      />
    );
    const bloqueadoRow = screen.getByRole('button', { name: /bloqueado/i });
    expect(bloqueadoRow).toHaveAttribute('aria-disabled', 'true');
  });

  it('does not call onToggleSelect when bloqueado row is clicked', () => {
    const onToggle = jest.fn();
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={onToggle}
        tipo="reparacion"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /bloqueado/i }));
    expect(onToggle).not.toHaveBeenCalled();
  });

  it('does not call onToggleSelect on Enter for bloqueado row', () => {
    const onToggle = jest.fn();
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={onToggle}
        tipo="reparacion"
      />
    );
    fireEvent.keyDown(screen.getByRole('button', { name: /bloqueado/i }), { key: 'Enter' });
    expect(onToggle).not.toHaveBeenCalled();
  });
});

describe('SpoolTable — accessibility', () => {
  it('all rows have role=button', () => {
    render(<SpoolTable {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(mockSpools.length);
  });

  it('rows have descriptive aria-labels', () => {
    render(<SpoolTable {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Seleccionar spool TEST-01/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Seleccionar spool TEST-02/ })).toBeInTheDocument();
  });

  it('passes axe audit', async () => {
    const { container } = render(<SpoolTable {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
