import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolFilterPanel } from '@/components/SpoolFilterPanel';

const defaultProps = {
  isExpanded: false,
  onToggleExpand: jest.fn(),
  searchNV: '',
  onSearchNVChange: jest.fn(),
  searchTag: '',
  onSearchTagChange: jest.fn(),
  selectedCount: 3,
  filteredCount: 10,
  activeFiltersCount: 0,
  onSelectAll: jest.fn(),
  onDeselectAll: jest.fn(),
  onClearFilters: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('SpoolFilterPanel — collapsed state', () => {
  it('shows selection counter', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    expect(screen.getByText('SELECCIONADOS: 3 / 10')).toBeInTheDocument();
  });

  it('does not show search inputs', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    expect(screen.queryByLabelText('Buscar por numero de nota de venta')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Buscar por TAG de spool')).not.toBeInTheDocument();
  });

  it('does not show filter badge when no active filters', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    expect(screen.queryByText(/FILTRO/)).not.toBeInTheDocument();
  });

  it('shows filter badge with count when filters are active', () => {
    render(<SpoolFilterPanel {...defaultProps} activeFiltersCount={2} />);
    expect(screen.getByText('2 FILTROS')).toBeInTheDocument();
  });

  it('shows singular FILTRO for 1 active filter', () => {
    render(<SpoolFilterPanel {...defaultProps} activeFiltersCount={1} />);
    expect(screen.getByText('1 FILTRO')).toBeInTheDocument();
  });

  it('calls onToggleExpand on click', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /Mostrar filtros/i }));
    expect(defaultProps.onToggleExpand).toHaveBeenCalledTimes(1);
  });

  it('calls onToggleExpand on Enter key', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    fireEvent.keyDown(screen.getByRole('button', { name: /Mostrar filtros/i }), { key: 'Enter' });
    expect(defaultProps.onToggleExpand).toHaveBeenCalledTimes(1);
  });

  it('calls onToggleExpand on Space key', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    fireEvent.keyDown(screen.getByRole('button', { name: /Mostrar filtros/i }), { key: ' ' });
    expect(defaultProps.onToggleExpand).toHaveBeenCalledTimes(1);
  });

  it('has aria-expanded=false', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Mostrar filtros/i })).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('SpoolFilterPanel — expanded state', () => {
  const expandedProps = { ...defaultProps, isExpanded: true };

  it('shows search inputs', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    expect(screen.getByLabelText('Buscar por numero de nota de venta')).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar por TAG de spool')).toBeInTheDocument();
  });

  it('shows TODOS and NINGUNO buttons', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    expect(screen.getByText('TODOS')).toBeInTheDocument();
    expect(screen.getByText('NINGUNO')).toBeInTheDocument();
  });

  it('shows LIMPIAR FILTROS when filters are active', () => {
    render(<SpoolFilterPanel {...expandedProps} activeFiltersCount={1} />);
    expect(screen.getByRole('button', { name: /Limpiar todos los filtros/i })).toBeInTheDocument();
  });

  it('does not show LIMPIAR FILTROS when no filters active', () => {
    render(<SpoolFilterPanel {...expandedProps} activeFiltersCount={0} />);
    expect(screen.queryByRole('button', { name: /Limpiar todos los filtros/i })).not.toBeInTheDocument();
  });

  it('calls onSelectAll when TODOS clicked', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    fireEvent.click(screen.getByText('TODOS'));
    expect(expandedProps.onSelectAll).toHaveBeenCalledTimes(1);
  });

  it('calls onDeselectAll when NINGUNO clicked', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    fireEvent.click(screen.getByText('NINGUNO'));
    expect(expandedProps.onDeselectAll).toHaveBeenCalledTimes(1);
  });

  it('calls onClearFilters when LIMPIAR FILTROS clicked', () => {
    render(<SpoolFilterPanel {...expandedProps} activeFiltersCount={1} />);
    fireEvent.click(screen.getByRole('button', { name: /Limpiar todos los filtros/i }));
    expect(expandedProps.onClearFilters).toHaveBeenCalledTimes(1);
  });

  it('calls onSearchNVChange when NV input changes', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    fireEvent.change(screen.getByLabelText('Buscar por numero de nota de venta'), { target: { value: 'NV-2024' } });
    expect(expandedProps.onSearchNVChange).toHaveBeenCalledWith('NV-2024');
  });

  it('calls onSearchTagChange when TAG input changes', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    fireEvent.change(screen.getByLabelText('Buscar por TAG de spool'), { target: { value: 'MK-123' } });
    expect(expandedProps.onSearchTagChange).toHaveBeenCalledWith('MK-123');
  });

  it('disables NINGUNO button when selectedCount is 0', () => {
    render(<SpoolFilterPanel {...expandedProps} selectedCount={0} />);
    expect(screen.getByRole('button', { name: /Deseleccionar todos/i })).toBeDisabled();
  });

  it('has aria-expanded=true on collapse button', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    expect(screen.getByRole('button', { name: /Ocultar filtros/i })).toHaveAttribute('aria-expanded', 'true');
  });

  it('has filter-panel region with aria-label', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    expect(screen.getByRole('region', { name: 'Panel de filtros' })).toBeInTheDocument();
  });

  it('shows expanded counter with FILTRADOS suffix', () => {
    render(<SpoolFilterPanel {...expandedProps} />);
    expect(screen.getByText('SELECCIONADOS: 3 / 10 FILTRADOS')).toBeInTheDocument();
  });
});

describe('SpoolFilterPanel — accessibility', () => {
  it('passes axe audit in collapsed state', async () => {
    const { container } = render(<SpoolFilterPanel {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('passes axe audit in expanded state', async () => {
    const { container } = render(<SpoolFilterPanel {...defaultProps} isExpanded={true} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
