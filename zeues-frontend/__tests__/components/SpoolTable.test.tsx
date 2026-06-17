import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolTable } from '@/components/SpoolTable';
import type { Spool, ReparacionSpool } from '@/lib/types';

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
  it('renders all column headers (SEL, NV, TAG SPOOL)', () => {
    render(<SpoolTable {...defaultProps} />);
    expect(screen.getByText('SEL')).toBeInTheDocument();
    expect(screen.getByText('NV')).toBeInTheDocument();
    expect(screen.getByText('TAG SPOOL')).toBeInTheDocument();
  });

  it('omits the NV column for tipo="reparacion" (ReparacionSpool has no nv)', () => {
    render(<SpoolTable {...defaultProps} tipo="reparacion" />);
    expect(screen.getByText('SEL')).toBeInTheDocument();
    expect(screen.getByText('TAG SPOOL')).toBeInTheDocument();
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
  const reparacionSpools: ReparacionSpool[] = [
    {
      tag_spool: 'REP-01',
      estado_detalle: 'RECHAZADO - Pendiente reparación',
      fecha_rechazo: '20-05-2026',
    },
    {
      tag_spool: 'REP-02',
      estado_detalle: 'RECHAZADO - Pendiente reparación',
      fecha_rechazo: '21-05-2026',
    },
  ];

  it('renders rows without cycle/bloqueado columns', () => {
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={jest.fn()}
        tipo="reparacion"
      />
    );
    expect(screen.getByText('REP-01')).toBeInTheDocument();
    expect(screen.getByText('REP-02')).toBeInTheDocument();
    expect(screen.queryByText(/Ciclo/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/BLOQUEADO/i)).not.toBeInTheDocument();
  });

  it('lets the user select a reparación row by clicking', () => {
    const onToggle = jest.fn();
    render(
      <SpoolTable
        spools={reparacionSpools}
        selectedSpools={[]}
        onToggleSelect={onToggle}
        tipo="reparacion"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /Seleccionar spool REP-01/ }));
    expect(onToggle).toHaveBeenCalledWith('REP-01');
  });
});

describe('SpoolTable — disabledSpools', () => {
  const disabledTag = 'TEST-02';

  it('renders disabled row with opacity-50 style', () => {
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} />);
    const row = screen.getByRole('button', { name: /spool TEST-02/i });
    expect(row.className).toMatch(/opacity-50/);
  });

  it('renders disabled row with cursor-not-allowed style', () => {
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} />);
    const row = screen.getByRole('button', { name: /spool TEST-02/i });
    expect(row.className).toMatch(/cursor-not-allowed/);
  });

  it('sets aria-disabled="true" on disabled row', () => {
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} />);
    const row = screen.getByRole('button', { name: /spool TEST-02/i });
    expect(row).toHaveAttribute('aria-disabled', 'true');
  });

  it('sets tabIndex=-1 on disabled row', () => {
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} />);
    const row = screen.getByRole('button', { name: /spool TEST-02/i });
    expect(row).toHaveAttribute('tabindex', '-1');
  });

  it('does not call onToggleSelect when disabled row is clicked', () => {
    const onToggle = jest.fn();
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} onToggleSelect={onToggle} />);
    fireEvent.click(screen.getByRole('button', { name: /spool TEST-02/i }));
    expect(onToggle).not.toHaveBeenCalled();
  });

  it('does not call onToggleSelect on Enter for disabled row', () => {
    const onToggle = jest.fn();
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} onToggleSelect={onToggle} />);
    fireEvent.keyDown(screen.getByRole('button', { name: /spool TEST-02/i }), { key: 'Enter' });
    expect(onToggle).not.toHaveBeenCalled();
  });

  it('does not call onToggleSelect on Space for disabled row', () => {
    const onToggle = jest.fn();
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} onToggleSelect={onToggle} />);
    fireEvent.keyDown(screen.getByRole('button', { name: /spool TEST-02/i }), { key: ' ' });
    expect(onToggle).not.toHaveBeenCalled();
  });

  it('non-disabled rows still work when disabledSpools is provided', () => {
    const onToggle = jest.fn();
    render(<SpoolTable {...defaultProps} disabledSpools={[disabledTag]} onToggleSelect={onToggle} />);
    fireEvent.click(screen.getByRole('button', { name: /Seleccionar spool TEST-01/i }));
    expect(onToggle).toHaveBeenCalledWith('TEST-01');
  });

  it('defaults to no disabled rows when disabledSpools is omitted', () => {
    const onToggle = jest.fn();
    render(<SpoolTable {...defaultProps} onToggleSelect={onToggle} />);
    fireEvent.click(screen.getByRole('button', { name: /Seleccionar spool TEST-02/i }));
    expect(onToggle).toHaveBeenCalledWith('TEST-02');
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
