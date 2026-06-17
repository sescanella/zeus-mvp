import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolCardList } from '@/components/SpoolCardList';
import { SpoolListProvider } from '@/lib/SpoolListContext';
import type { SpoolCardData } from '@/lib/types';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const makeSpool = (tag: string): SpoolCardData => ({
  tag_spool: tag,
  nv: null,
  ocupado_por: null,
  ocupado_por_display: null,
  fecha_ocupacion: null,
  estado_detalle: null,
  total_uniones: 3,
  uniones_arm_completadas: 0,
  uniones_sold_completadas: 0,
  pulgadas_arm: null,
  pulgadas_sold: null,
  fecha_armado: null,
  armador_display: null,
  fecha_soldadura: null,
  soldador_display: null,
  operacion_actual: null,
  estado_trabajo: 'LIBRE',
});

const spools = [makeSpool('OT-001'), makeSpool('OT-002'), makeSpool('OT-003')];

const mockOnCardClick = jest.fn();

const defaultProps = {
  onCardClick: mockOnCardClick,
};

// Helper: wrap SpoolCardList in SpoolListProvider (required by useSpoolList hook)
function renderWithProvider(ui: React.ReactElement) {
  return render(<SpoolListProvider>{ui}</SpoolListProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
});

// ─── Empty state ───────────────────────────────────────────────────────────────

describe('SpoolCardList — empty state', () => {
  it('renders empty state message when spools array is empty', () => {
    renderWithProvider(<SpoolCardList spools={[]} {...defaultProps} />);
    expect(screen.getByText(/No hay spools en tu lista/i)).toBeInTheDocument();
  });

  it('renders empty state subtext about Añadir Spool button', () => {
    renderWithProvider(<SpoolCardList spools={[]} {...defaultProps} />);
    expect(
      screen.getByText(/Usa el botón Añadir Spool para comenzar/i)
    ).toBeInTheDocument();
  });

  it('renders PackageOpen icon in empty state', () => {
    const { container } = renderWithProvider(<SpoolCardList spools={[]} {...defaultProps} />);
    // Lucide icons render as SVG elements
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('does not render any spool cards in empty state', () => {
    renderWithProvider(<SpoolCardList spools={[]} {...defaultProps} />);
    expect(screen.queryByRole('button', { name: /^Spool/ })).not.toBeInTheDocument();
  });
});

// ─── Non-empty state ───────────────────────────────────────────────────────────

describe('SpoolCardList — with spools', () => {
  it('renders correct number of content-area buttons for 3 spools', () => {
    renderWithProvider(<SpoolCardList spools={spools} {...defaultProps} />);
    const cards = screen.getAllByRole('button', { name: /^Procesar spool/ });
    expect(cards).toHaveLength(3);
  });

  it('renders a card for each spool tag', () => {
    renderWithProvider(<SpoolCardList spools={spools} {...defaultProps} />);
    expect(screen.getByText('OT-001')).toBeInTheDocument();
    expect(screen.getByText('OT-002')).toBeInTheDocument();
    expect(screen.getByText('OT-003')).toBeInTheDocument();
  });

  it('renders 1 card when spools has 1 item', () => {
    renderWithProvider(<SpoolCardList spools={[makeSpool('SINGLE-01')]} {...defaultProps} />);
    const cards = screen.getAllByRole('button', { name: /^Procesar spool/ });
    expect(cards).toHaveLength(1);
  });

  it('does not render empty state when spools is non-empty', () => {
    renderWithProvider(<SpoolCardList spools={spools} {...defaultProps} />);
    expect(
      screen.queryByText(/No hay spools en tu lista/i)
    ).not.toBeInTheDocument();
  });
});

// ─── Callback propagation ──────────────────────────────────────────────────────

describe('SpoolCardList — callback propagation', () => {
  it('calls onCardClick with spool data when a card is clicked', () => {
    renderWithProvider(<SpoolCardList spools={[makeSpool('OT-001')]} {...defaultProps} />);
    const card = screen.getByRole('button', { name: /^Procesar spool OT-001/ });
    fireEvent.click(card);
    expect(mockOnCardClick).toHaveBeenCalledWith(makeSpool('OT-001'));
  });

  it('propagates onCardClick for each card independently', () => {
    renderWithProvider(<SpoolCardList spools={spools} {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /^Procesar spool OT-002/ }));
    expect(mockOnCardClick).toHaveBeenCalledWith(makeSpool('OT-002'));
    expect(mockOnCardClick).toHaveBeenCalledTimes(1);
  });
});

// ─── Sorting ──────────────────────────────────────────────────────────────────

describe('SpoolCardList — sorting', () => {
  it('renders spools in original order when fecha_ocupacion is null for all', () => {
    renderWithProvider(<SpoolCardList spools={spools} {...defaultProps} />);
    const tags = screen.getAllByText(/^OT-00[123]$/).map((el) => el.textContent);
    expect(tags).toEqual(['OT-001', 'OT-002', 'OT-003']);
  });

  it('sorts by fecha_ocupacion descending (newest first)', () => {
    const olderSpool: SpoolCardData = {
      ...makeSpool('OLD'),
      fecha_ocupacion: '01-03-2026 09:00:00',
    };
    const newerSpool: SpoolCardData = {
      ...makeSpool('NEW'),
      fecha_ocupacion: '10-03-2026 09:00:00',
    };
    renderWithProvider(
      <SpoolCardList spools={[olderSpool, newerSpool]} {...defaultProps} />
    );
    const cards = screen.getAllByRole('button', { name: /^Procesar spool/ });
    // First card rendered should be the newer one.
    expect(cards[0]).toHaveAccessibleName(/NEW/);
    expect(cards[1]).toHaveAccessibleName(/OLD/);
  });
});

// ─── Accessibility ────────────────────────────────────────────────────────────

describe('SpoolCardList — accessibility', () => {
  it('passes axe audit with empty spools', async () => {
    const { container } = renderWithProvider(<SpoolCardList spools={[]} {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);

  it('passes axe audit with spools present', async () => {
    const { container } = renderWithProvider(
      <SpoolCardList spools={[makeSpool('OT-001'), makeSpool('OT-002')]} {...defaultProps} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
