import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { AddSpoolModal } from '@/components/AddSpoolModal';

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('@/lib/api', () => ({
  getSpoolsParaIniciar: jest.fn(),
}));

jest.mock('@/components/SpoolTable', () => ({
  SpoolTable: jest.fn((props) => (
    <div data-testid="spool-table">
      {props.spools.map((s) => (
        <button
          key={s.tag_spool}
          data-testid={`spool-row-${s.tag_spool}`}
          data-disabled={props.disabledSpools?.includes(s.tag_spool) ? 'true' : 'false'}
          onClick={() =>
            !props.disabledSpools?.includes(s.tag_spool) && props.onToggleSelect(s.tag_spool)
          }
        >
          {s.tag_spool}
        </button>
      ))}
    </div>
  )),
}));

jest.mock('@/components/SpoolFilterPanel', () => ({
  SpoolFilterPanel: jest.fn((props) => (
    <div
      data-testid="spool-filter-panel"
      data-show-selection={String(props.showSelectionControls)}
    />
  )),
}));

// Mock Modal to render children directly (avoids portal issues in jsdom)
jest.mock('@/components/Modal', () => ({
  Modal: jest.fn((props) =>
    props.isOpen ? (
      <div role="dialog" aria-modal="true" aria-label="Anadir spool">
        {props.children}
        {props.onClose && (
          <button aria-label="Cerrar" onClick={props.onClose}>
            X
          </button>
        )}
      </div>
    ) : null
  ),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

import { getSpoolsParaIniciar } from '@/lib/api';
const mockGetSpoolsParaIniciar = getSpoolsParaIniciar as jest.Mock;

const mockSpools = [
  { tag_spool: 'TEST-01', nv: 'NV-001', arm: 0, sold: 0 },
  { tag_spool: 'TEST-02', nv: 'NV-002', arm: 0, sold: 0 },
  { tag_spool: 'TEST-03', nv: 'NV-003', arm: 1, sold: 0 },
];

const defaultProps = {
  isOpen: true,
  onAdd: jest.fn(),
  onClose: jest.fn(),
  alreadyTracked: [] as string[],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetSpoolsParaIniciar.mockResolvedValue(mockSpools);
});

// ─── Rendering ─────────────────────────────────────────────────────────────────

describe('AddSpoolModal — rendering', () => {
  it('renders SpoolTable when isOpen=true and data is loaded', async () => {
    render(<AddSpoolModal {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
  });

  it('does not render when isOpen=false', () => {
    render(<AddSpoolModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId('spool-table')).not.toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows loading state while fetching', () => {
    // Keep the promise pending
    mockGetSpoolsParaIniciar.mockImplementation(() => new Promise(() => {}));
    render(<AddSpoolModal {...defaultProps} />);
    expect(screen.getByText(/CARGANDO/i)).toBeInTheDocument();
  });

  it('shows error message when fetch fails with retry button', async () => {
    mockGetSpoolsParaIniciar.mockRejectedValueOnce(new Error('Network error'));
    render(<AddSpoolModal {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument();
  });

  it('passes showSelectionControls=false to SpoolFilterPanel', async () => {
    render(<AddSpoolModal {...defaultProps} />);
    await waitFor(() => {
      const panel = screen.getByTestId('spool-filter-panel');
      expect(panel).toHaveAttribute('data-show-selection', 'false');
    });
  });
});

// ─── Disabled spools (UX-01) ──────────────────────────────────────────────────

describe('AddSpoolModal — alreadyTracked as disabledSpools (UX-01)', () => {
  it('passes alreadyTracked tags as disabledSpools to SpoolTable', async () => {
    render(<AddSpoolModal {...defaultProps} alreadyTracked={['TEST-01']} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
    const row = screen.getByTestId('spool-row-TEST-01');
    expect(row).toHaveAttribute('data-disabled', 'true');
  });

  it('non-tracked spools are NOT disabled', async () => {
    render(<AddSpoolModal {...defaultProps} alreadyTracked={['TEST-01']} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
    const row = screen.getByTestId('spool-row-TEST-02');
    expect(row).toHaveAttribute('data-disabled', 'false');
  });
});

// ─── Callbacks ─────────────────────────────────────────────────────────────────

describe('AddSpoolModal — callbacks', () => {
  it('calls onAdd(tag) when a non-disabled spool row is clicked', async () => {
    const onAdd = jest.fn();
    render(<AddSpoolModal {...defaultProps} onAdd={onAdd} alreadyTracked={[]} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('spool-row-TEST-02'));
    expect(onAdd).toHaveBeenCalledWith('TEST-02');
  });

  it('does NOT call onAdd when a disabled spool row is clicked', async () => {
    const onAdd = jest.fn();
    render(<AddSpoolModal {...defaultProps} onAdd={onAdd} alreadyTracked={['TEST-01']} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('spool-row-TEST-01'));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('calls onClose when close button is triggered', async () => {
    const onClose = jest.fn();
    render(<AddSpoolModal {...defaultProps} onClose={onClose} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /cerrar/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('retries fetch when retry button is clicked after error', async () => {
    mockGetSpoolsParaIniciar
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(mockSpools);
    render(<AddSpoolModal {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /reintentar/i }));
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
  });
});

// ─── Accessibility ─────────────────────────────────────────────────────────────

describe('AddSpoolModal — accessibility', () => {
  it('has no axe violations when open and loaded', async () => {
    jest.useRealTimers();
    mockGetSpoolsParaIniciar.mockResolvedValue(mockSpools);
    const { container } = render(<AddSpoolModal {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByTestId('spool-table')).toBeInTheDocument();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  }, 10000);
});
