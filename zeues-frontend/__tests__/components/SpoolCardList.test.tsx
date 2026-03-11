import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolCardList } from '@/components/SpoolCardList';
import type { SpoolCardData } from '@/lib/types';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const makeSpool = (tag: string): SpoolCardData => ({
  tag_spool: tag,
  ocupado_por: null,
  fecha_ocupacion: null,
  estado_detalle: null,
  total_uniones: 3,
  uniones_arm_completadas: 0,
  uniones_sold_completadas: 0,
  pulgadas_arm: null,
  pulgadas_sold: null,
  operacion_actual: null,
  estado_trabajo: 'LIBRE',
  ciclo_rep: null,
});

const spools = [makeSpool('OT-001'), makeSpool('OT-002'), makeSpool('OT-003')];

const mockOnCardClick = jest.fn();

const defaultProps = {
  onCardClick: mockOnCardClick,
};

beforeEach(() => {
  jest.clearAllMocks();
});

// ─── Empty state ───────────────────────────────────────────────────────────────

describe('SpoolCardList — empty state', () => {
  it('renders empty state message when spools array is empty', () => {
    render(<SpoolCardList spools={[]} {...defaultProps} />);
    expect(screen.getByText(/No hay spools en tu lista/i)).toBeInTheDocument();
  });

  it('renders empty state subtext about Anadir Spool button', () => {
    render(<SpoolCardList spools={[]} {...defaultProps} />);
    expect(
      screen.getByText(/Usa el boton Anadir Spool para comenzar/i)
    ).toBeInTheDocument();
  });

  it('renders PackageOpen icon in empty state', () => {
    const { container } = render(<SpoolCardList spools={[]} {...defaultProps} />);
    // Lucide icons render as SVG elements
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('does not render any spool cards in empty state', () => {
    render(<SpoolCardList spools={[]} {...defaultProps} />);
    expect(screen.queryByRole('button', { name: /^Spool/ })).not.toBeInTheDocument();
  });
});

// ─── Non-empty state ───────────────────────────────────────────────────────────

describe('SpoolCardList — with spools', () => {
  it('renders correct number of spool cards for 3 spools', () => {
    render(<SpoolCardList spools={spools} {...defaultProps} />);
    const cards = screen.getAllByRole('button', { name: /^Spool/ });
    expect(cards).toHaveLength(3);
  });

  it('renders a card for each spool tag', () => {
    render(<SpoolCardList spools={spools} {...defaultProps} />);
    expect(screen.getByText('OT-001')).toBeInTheDocument();
    expect(screen.getByText('OT-002')).toBeInTheDocument();
    expect(screen.getByText('OT-003')).toBeInTheDocument();
  });

  it('renders 1 card when spools has 1 item', () => {
    render(<SpoolCardList spools={[makeSpool('SINGLE-01')]} {...defaultProps} />);
    const cards = screen.getAllByRole('button', { name: /^Spool/ });
    expect(cards).toHaveLength(1);
  });

  it('does not render empty state when spools is non-empty', () => {
    render(<SpoolCardList spools={spools} {...defaultProps} />);
    expect(
      screen.queryByText(/No hay spools en tu lista/i)
    ).not.toBeInTheDocument();
  });
});

// ─── Callback propagation ──────────────────────────────────────────────────────

describe('SpoolCardList — callback propagation', () => {
  it('calls onCardClick with spool data when a card is clicked', () => {
    render(<SpoolCardList spools={[makeSpool('OT-001')]} {...defaultProps} />);
    const card = screen.getByRole('button', { name: /^Spool OT-001/ });
    fireEvent.click(card);
    expect(mockOnCardClick).toHaveBeenCalledWith(makeSpool('OT-001'));
  });

  it('propagates onCardClick for each card independently', () => {
    render(<SpoolCardList spools={spools} {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /^Spool OT-002/ }));
    expect(mockOnCardClick).toHaveBeenCalledWith(makeSpool('OT-002'));
    expect(mockOnCardClick).toHaveBeenCalledTimes(1);
  });
});

// ─── Accessibility ────────────────────────────────────────────────────────────

describe('SpoolCardList — accessibility', () => {
  it('passes axe audit with empty spools', async () => {
    const { container } = render(<SpoolCardList spools={[]} {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);

  it('passes axe audit with spools present', async () => {
    const { container } = render(
      <SpoolCardList spools={[makeSpool('OT-001'), makeSpool('OT-002')]} {...defaultProps} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
