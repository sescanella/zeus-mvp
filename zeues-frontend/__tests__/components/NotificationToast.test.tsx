import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { NotificationToast } from '@/components/NotificationToast';
import type { Toast } from '@/hooks/useNotificationToast';

const mockToasts: Toast[] = [
  { id: 'toast-1', message: 'Operacion exitosa', type: 'success' },
  { id: 'toast-2', message: 'Error al conectar', type: 'error' },
];

const mockOnDismiss = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
});

describe('NotificationToast — empty state', () => {
  it('renders aria-live container even when toasts array is empty', () => {
    const { container } = render(
      <NotificationToast toasts={[]} onDismiss={mockOnDismiss} />
    );
    const liveRegion = container.querySelector('[aria-live="polite"]');
    expect(liveRegion).toBeInTheDocument();
  });

  it('renders no visible toast items when toasts is empty', () => {
    render(<NotificationToast toasts={[]} onDismiss={mockOnDismiss} />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('NotificationToast — success toast', () => {
  it('renders success toast with role=alert', () => {
    render(<NotificationToast toasts={[mockToasts[0]]} onDismiss={mockOnDismiss} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders success toast message text', () => {
    render(<NotificationToast toasts={[mockToasts[0]]} onDismiss={mockOnDismiss} />);
    expect(screen.getByText('Operacion exitosa')).toBeInTheDocument();
  });

  it('renders success toast with green border class', () => {
    render(<NotificationToast toasts={[mockToasts[0]]} onDismiss={mockOnDismiss} />);
    const alert = screen.getByRole('alert');
    expect(alert.className).toMatch(/border-green-400/);
  });
});

describe('NotificationToast — error toast', () => {
  it('renders error toast with role=alert', () => {
    render(<NotificationToast toasts={[mockToasts[1]]} onDismiss={mockOnDismiss} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders error toast message text', () => {
    render(<NotificationToast toasts={[mockToasts[1]]} onDismiss={mockOnDismiss} />);
    expect(screen.getByText('Error al conectar')).toBeInTheDocument();
  });

  it('renders error toast with red border class', () => {
    render(<NotificationToast toasts={[mockToasts[1]]} onDismiss={mockOnDismiss} />);
    const alert = screen.getByRole('alert');
    expect(alert.className).toMatch(/border-red-400/);
  });
});

describe('NotificationToast — multiple toasts', () => {
  it('renders all toasts simultaneously', () => {
    render(<NotificationToast toasts={mockToasts} onDismiss={mockOnDismiss} />);
    const alerts = screen.getAllByRole('alert');
    expect(alerts).toHaveLength(2);
  });

  it('renders all toast messages', () => {
    render(<NotificationToast toasts={mockToasts} onDismiss={mockOnDismiss} />);
    expect(screen.getByText('Operacion exitosa')).toBeInTheDocument();
    expect(screen.getByText('Error al conectar')).toBeInTheDocument();
  });
});

describe('NotificationToast — dismiss', () => {
  it('renders dismiss button with aria-label', () => {
    render(<NotificationToast toasts={[mockToasts[0]]} onDismiss={mockOnDismiss} />);
    expect(screen.getByLabelText('Cerrar notificacion')).toBeInTheDocument();
  });

  it('calls onDismiss with toast id when dismiss button clicked', () => {
    render(<NotificationToast toasts={[mockToasts[0]]} onDismiss={mockOnDismiss} />);
    fireEvent.click(screen.getByLabelText('Cerrar notificacion'));
    expect(mockOnDismiss).toHaveBeenCalledWith('toast-1');
  });
});

describe('NotificationToast — accessibility', () => {
  it('passes axe audit with empty toasts', async () => {
    const { container } = render(
      <NotificationToast toasts={[]} onDismiss={mockOnDismiss} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('passes axe audit with toasts present', async () => {
    const { container } = render(
      <NotificationToast toasts={mockToasts} onDismiss={mockOnDismiss} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
