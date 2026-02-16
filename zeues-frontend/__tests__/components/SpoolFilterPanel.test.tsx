import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolFilterPanel } from '@/components/SpoolFilterPanel';

const defaultProps = {
  isOpen: false,
  onOpen: jest.fn(),
  onClose: jest.fn(),
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

describe('SpoolFilterPanel — closed state (trigger bar)', () => {
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

  it('calls onOpen on click', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /Abrir filtros/i }));
    expect(defaultProps.onOpen).toHaveBeenCalledTimes(1);
  });

  it('has aria-haspopup="dialog"', () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Abrir filtros/i })).toHaveAttribute('aria-haspopup', 'dialog');
  });
});

describe('SpoolFilterPanel — open state (modal)', () => {
  const openProps = { ...defaultProps, isOpen: true };

  it('shows search inputs', () => {
    render(<SpoolFilterPanel {...openProps} />);
    expect(screen.getByLabelText('Buscar por numero de nota de venta')).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar por TAG de spool')).toBeInTheDocument();
  });

  it('renders a dialog', () => {
    render(<SpoolFilterPanel {...openProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows TODOS and NINGUNO buttons', () => {
    render(<SpoolFilterPanel {...openProps} />);
    expect(screen.getByText('TODOS')).toBeInTheDocument();
    expect(screen.getByText('NINGUNO')).toBeInTheDocument();
  });

  it('shows LIMPIAR FILTROS when filters are active', () => {
    render(<SpoolFilterPanel {...openProps} activeFiltersCount={1} />);
    expect(screen.getByRole('button', { name: /Limpiar todos los filtros/i })).toBeInTheDocument();
  });

  it('does not show LIMPIAR FILTROS when no filters active', () => {
    render(<SpoolFilterPanel {...openProps} activeFiltersCount={0} />);
    expect(screen.queryByRole('button', { name: /Limpiar todos los filtros/i })).not.toBeInTheDocument();
  });

  it('calls onSelectAll when TODOS clicked', () => {
    render(<SpoolFilterPanel {...openProps} />);
    fireEvent.click(screen.getByText('TODOS'));
    expect(openProps.onSelectAll).toHaveBeenCalledTimes(1);
  });

  it('calls onDeselectAll when NINGUNO clicked', () => {
    render(<SpoolFilterPanel {...openProps} />);
    fireEvent.click(screen.getByText('NINGUNO'));
    expect(openProps.onDeselectAll).toHaveBeenCalledTimes(1);
  });

  it('calls onClearFilters when LIMPIAR FILTROS clicked', () => {
    render(<SpoolFilterPanel {...openProps} activeFiltersCount={1} />);
    fireEvent.click(screen.getByRole('button', { name: /Limpiar todos los filtros/i }));
    expect(openProps.onClearFilters).toHaveBeenCalledTimes(1);
  });

  it('calls onSearchNVChange when NV input changes', () => {
    render(<SpoolFilterPanel {...openProps} />);
    fireEvent.change(screen.getByLabelText('Buscar por numero de nota de venta'), { target: { value: 'NV-2024' } });
    expect(openProps.onSearchNVChange).toHaveBeenCalledWith('NV-2024');
  });

  it('calls onSearchTagChange when TAG input changes', () => {
    render(<SpoolFilterPanel {...openProps} />);
    fireEvent.change(screen.getByLabelText('Buscar por TAG de spool'), { target: { value: 'MK-123' } });
    expect(openProps.onSearchTagChange).toHaveBeenCalledWith('MK-123');
  });

  it('disables NINGUNO button when selectedCount is 0', () => {
    render(<SpoolFilterPanel {...openProps} selectedCount={0} />);
    expect(screen.getByRole('button', { name: /Deseleccionar todos/i })).toBeDisabled();
  });

  it('shows close button inside modal', () => {
    render(<SpoolFilterPanel {...openProps} />);
    expect(screen.getByRole('button', { name: /Cerrar filtros/i })).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    render(<SpoolFilterPanel {...openProps} />);
    fireEvent.click(screen.getByRole('button', { name: /Cerrar filtros/i }));
    expect(openProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('shows counter with FILTRADOS suffix', () => {
    render(<SpoolFilterPanel {...openProps} />);
    expect(screen.getByText('SELECCIONADOS: 3 / 10 FILTRADOS')).toBeInTheDocument();
  });
});

describe('SpoolFilterPanel — accessibility', () => {
  it('passes axe audit in closed state', async () => {
    render(<SpoolFilterPanel {...defaultProps} />);
    const results = await axe(document.body);
    expect(results).toHaveNoViolations();
  });

  it('passes axe audit in open state', async () => {
    render(<SpoolFilterPanel {...defaultProps} isOpen={true} />);
    const results = await axe(document.body);
    expect(results).toHaveNoViolations();
  });
});
