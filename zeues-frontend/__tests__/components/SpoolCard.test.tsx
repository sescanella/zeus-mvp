import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SpoolCard } from '@/components/SpoolCard';
import type { SpoolCardData } from '@/lib/types';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const baseOccupied: SpoolCardData = {
  tag_spool: 'OT-001',
  nv: null,
  ocupado_por: 'MR(93)',
  ocupado_por_display: null,
  fecha_ocupacion: '10-03-2026 14:30:00',
  estado_detalle: 'En progreso de armado',
  total_uniones: 5,
  uniones_arm_completadas: 2,
  uniones_sold_completadas: 0,
  pulgadas_arm: 4.5,
  pulgadas_sold: null,
  operacion_actual: 'ARM',
  estado_trabajo: 'EN_PROGRESO',
  ciclo_rep: null,
};

const baseFree: SpoolCardData = {
  tag_spool: 'OT-002',
  nv: null,
  ocupado_por: null,
  ocupado_por_display: null,
  fecha_ocupacion: null,
  estado_detalle: 'Libre para armado',
  total_uniones: 3,
  uniones_arm_completadas: 0,
  uniones_sold_completadas: 0,
  pulgadas_arm: null,
  pulgadas_sold: null,
  operacion_actual: null,
  estado_trabajo: 'LIBRE',
  ciclo_rep: null,
};

const pausadoSpool: SpoolCardData = {
  ...baseOccupied,
  tag_spool: 'OT-003',
  ocupado_por: 'JP(91)',
  estado_trabajo: 'PAUSADO',
  estado_detalle: 'Pausado en armado',
};

const mockOnCardClick = jest.fn();

const defaultProps = {
  onCardClick: mockOnCardClick,
};

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
  // parseFechaOcupacion uses new Date(year, month-1, day, h, m, s) — local time.
  // '10-03-2026 14:30:00' → local 14:30 = UTC 17:30 (UTC-3, America/Santiago).
  // Set system time to the same LOCAL epoch expressed as UTC so elapsed starts at 0.
  jest.setSystemTime(new Date('2026-03-10T17:30:00.000Z'));
});

afterEach(() => {
  jest.useRealTimers();
});

// ─── Tag rendering ─────────────────────────────────────────────────────────────

describe('SpoolCard — tag_spool', () => {
  it('renders tag_spool prominently', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    expect(screen.getByText('OT-001')).toBeInTheDocument();
  });
});

// ─── Operacion badge ───────────────────────────────────────────────────────────

describe('SpoolCard — operacion_actual badge', () => {
  it('renders ARM badge when operacion_actual is ARM', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    expect(screen.getByText('Armado')).toBeInTheDocument();
  });

  it('renders SOLD badge when operacion_actual is SOLD', () => {
    const spool: SpoolCardData = { ...baseOccupied, operacion_actual: 'SOLD' };
    render(<SpoolCard spool={spool} {...defaultProps} />);
    expect(screen.getByText('Soldadura')).toBeInTheDocument();
  });

  it('renders REP badge when operacion_actual is REPARACION', () => {
    const spool: SpoolCardData = { ...baseOccupied, operacion_actual: 'REPARACION' };
    render(<SpoolCard spool={spool} {...defaultProps} />);
    expect(screen.getByText('Reparación')).toBeInTheDocument();
  });

  it('does not render operacion badge when operacion_actual is null', () => {
    render(<SpoolCard spool={baseFree} {...defaultProps} />);
    expect(screen.queryByText('Armado')).not.toBeInTheDocument();
    expect(screen.queryByText('Soldadura')).not.toBeInTheDocument();
  });
});

// ─── Estado badge ──────────────────────────────────────────────────────────────

describe('SpoolCard — estado_trabajo badge', () => {
  const estadoTestCases: Array<{
    estado: SpoolCardData['estado_trabajo'];
    label: string;
    colorClass: string;
  }> = [
    { estado: 'LIBRE', label: 'Libre', colorClass: 'text-white' },
    { estado: 'EN_PROGRESO', label: 'En Progreso', colorClass: 'text-zeues-orange' },
    { estado: 'PAUSADO', label: 'Pausado', colorClass: 'text-yellow-400' },
    { estado: 'COMPLETADO', label: 'Completado', colorClass: 'text-green-400' },
    { estado: 'RECHAZADO', label: 'Rechazado', colorClass: 'text-red-400' },
    { estado: 'PENDIENTE_METROLOGIA', label: 'Pend. Metrología', colorClass: 'text-blue-300' },
    { estado: 'BLOQUEADO', label: 'Bloqueado', colorClass: 'text-red-500' },
  ];

  estadoTestCases.forEach(({ estado, label, colorClass }) => {
    it(`renders ${label} badge with correct color class`, () => {
      const spool: SpoolCardData = { ...baseFree, estado_trabajo: estado };
      render(<SpoolCard spool={spool} {...defaultProps} />);
      const badge = screen.getByText(label);
      expect(badge).toBeInTheDocument();
      // Check that the badge or its parent has the color class
      const badgeEl = badge.closest('[class]') ?? badge;
      expect(badgeEl.className).toMatch(new RegExp(colorClass.replace('-', '\\-')));
    });
  });

  it('renders all 7 estado_trabajo states', () => {
    estadoTestCases.forEach(({ estado, label }) => {
      const { unmount } = render(
        <SpoolCard spool={{ ...baseFree, estado_trabajo: estado }} {...defaultProps} />
      );
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    });
  });
});

// ─── Worker name ───────────────────────────────────────────────────────────────

describe('SpoolCard — ocupado_por', () => {
  it('renders worker name when ocupado_por is non-null', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    expect(screen.getByText('MR(93)')).toBeInTheDocument();
  });

  it('does not render worker line when ocupado_por is null', () => {
    render(<SpoolCard spool={baseFree} {...defaultProps} />);
    expect(screen.queryByText('MR(93)')).not.toBeInTheDocument();
  });
});

// ─── Timer ────────────────────────────────────────────────────────────────────

describe('SpoolCard — elapsed timer', () => {
  it('shows elapsed timer when occupied (EN_PROGRESO)', () => {
    // System time is 2026-03-10T17:30:00Z = 14:30:00 local (UTC-3, America/Santiago)
    // fecha_ocupacion = '10-03-2026 14:30:00' → local time → same epoch = 0s elapsed
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    // Timer starts at 0s; after tick it shows time
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    // Should display some time indicator (00:01 after 1s)
    expect(screen.getByText('00:01')).toBeInTheDocument();
  });

  it('shows HH:MM:SS format when elapsed >= 1 hour', () => {
    // System time is 2026-03-10T17:30:00Z = 14:30 local (UTC-3).
    // '10-03-2026 12:30:00' → local 12:30 = UTC 15:30
    // elapsed = 17:30 UTC - 15:30 UTC = 2 hours exactly
    const twoHoursAgo = '10-03-2026 12:30:00';
    const spool: SpoolCardData = { ...baseOccupied, fecha_ocupacion: twoHoursAgo };
    render(<SpoolCard spool={spool} {...defaultProps} />);
    act(() => {
      jest.advanceTimersByTime(0);
    });
    expect(screen.getByText('02:00:00')).toBeInTheDocument();
  });

  it('shows MM:SS format when elapsed < 1 hour', () => {
    // System time is 2026-03-10T17:30:00Z = 14:30 local (UTC-3).
    // '10-03-2026 14:25:00' → local 14:25 = UTC 17:25
    // elapsed = 17:30 UTC - 17:25 UTC = 5 minutes = 300s
    const fiveMinAgo = '10-03-2026 14:25:00';
    const spool: SpoolCardData = { ...baseOccupied, fecha_ocupacion: fiveMinAgo };
    render(<SpoolCard spool={spool} {...defaultProps} />);
    act(() => {
      jest.advanceTimersByTime(0);
    });
    expect(screen.getByText('05:00')).toBeInTheDocument();
  });

  it('does NOT show timer when estado_trabajo is PAUSADO (STATE-06)', () => {
    render(<SpoolCard spool={pausadoSpool} {...defaultProps} />);
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    // Should not show any time pattern like "00:05"
    expect(screen.queryByText(/^\d{2}:\d{2}(:\d{2})?$/)).not.toBeInTheDocument();
  });

  it('does NOT show timer when ocupado_por is null', () => {
    render(<SpoolCard spool={baseFree} {...defaultProps} />);
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(screen.queryByText(/^\d{2}:\d{2}(:\d{2})?$/)).not.toBeInTheDocument();
  });

  it('parses fecha_ocupacion in DD-MM-YYYY HH:MM:SS format (not ISO)', () => {
    // System time is 2026-03-10T17:30:00Z = 14:30 local (UTC-3).
    // '10-03-2026 14:29:00' → local 14:29 = UTC 17:29
    // elapsed = 17:30 UTC - 17:29 UTC = 60s = '01:00'
    const spool: SpoolCardData = {
      ...baseOccupied,
      fecha_ocupacion: '10-03-2026 14:29:00',
    };
    render(<SpoolCard spool={spool} {...defaultProps} />);
    act(() => {
      jest.advanceTimersByTime(0);
    });
    expect(screen.getByText('01:00')).toBeInTheDocument();
  });
});

// ─── Click and keyboard ───────────────────────────────────────────────────────

describe('SpoolCard — interaction', () => {
  it('calls onCardClick with spool data when card is clicked', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    // Click the card element — matches the full aria-label "Procesar spool OT-001 - En Progreso"
    const card = screen.getByRole('button', { name: /^Procesar spool OT-001/ });
    fireEvent.click(card);
    expect(mockOnCardClick).toHaveBeenCalledWith(baseOccupied);
  });

  it('calls onCardClick when Enter key is pressed on card', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    const card = screen.getByRole('button', { name: /^Procesar spool OT-001/ });
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(mockOnCardClick).toHaveBeenCalledWith(baseOccupied);
  });

  it('calls onCardClick when Space key is pressed on card', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    const card = screen.getByRole('button', { name: /^Procesar spool OT-001/ });
    fireEvent.keyDown(card, { key: ' ' });
    expect(mockOnCardClick).toHaveBeenCalledWith(baseOccupied);
  });

});

// ─── Accessibility ────────────────────────────────────────────────────────────

describe('SpoolCard — accessibility', () => {
  // axe uses async internals — must use real timers for these tests
  beforeEach(() => {
    jest.useRealTimers();
  });
  afterEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-03-10T17:30:00.000Z'));
  });

  it('passes axe audit for occupied spool', async () => {
    const { container } = render(
      <SpoolCard spool={baseOccupied} {...defaultProps} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);

  it('passes axe audit for free spool', async () => {
    const { container } = render(
      <SpoolCard spool={baseFree} {...defaultProps} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);

  it('passes axe audit for PAUSADO spool', async () => {
    const { container } = render(
      <SpoolCard spool={pausadoSpool} {...defaultProps} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);

  it('card has tabIndex=0 for keyboard focus', () => {
    render(<SpoolCard spool={baseOccupied} {...defaultProps} />);
    const card = screen.getByRole('button', { name: /^Procesar spool OT-001/ });
    expect(card).toHaveAttribute('tabindex', '0');
  });
});
