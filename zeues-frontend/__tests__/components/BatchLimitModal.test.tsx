import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BatchLimitModal } from '@/components/BatchLimitModal';

const defaultProps = {
  isOpen: true,
  onClose: jest.fn(),
  maxBatch: 50,
  totalAvailable: 75,
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('BatchLimitModal', () => {
  it('renders modal content when open', () => {
    render(<BatchLimitModal {...defaultProps} />);
    expect(screen.getByText('LIMITE DE SELECCION')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<BatchLimitModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('LIMITE DE SELECCION')).not.toBeInTheDocument();
  });

  it('displays the max batch number', () => {
    render(<BatchLimitModal {...defaultProps} />);
    const maxElements = screen.getAllByText('50');
    expect(maxElements.length).toBeGreaterThanOrEqual(1);
  });

  it('displays the total available number', () => {
    render(<BatchLimitModal {...defaultProps} />);
    expect(screen.getByText('75')).toBeInTheDocument();
  });

  it('calls onClose when ENTENDIDO button is clicked', () => {
    render(<BatchLimitModal {...defaultProps} />);
    fireEvent.click(screen.getByText('ENTENDIDO'));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('shows hint about using filters', () => {
    render(<BatchLimitModal {...defaultProps} />);
    expect(screen.getByText(/Usa los filtros/)).toBeInTheDocument();
  });
});
