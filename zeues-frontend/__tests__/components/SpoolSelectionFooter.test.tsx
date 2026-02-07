import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { SpoolSelectionFooter } from '@/components/SpoolSelectionFooter';

const defaultProps = {
  selectedCount: 2,
  hasSpools: true,
  onContinue: jest.fn(),
  onBack: jest.fn(),
  onHome: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('SpoolSelectionFooter — continue button', () => {
  it('shows continue button when hasSpools is true', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    expect(screen.getByText(/CONTINUAR CON 2 SPOOLS/)).toBeInTheDocument();
  });

  it('hides continue button when hasSpools is false', () => {
    render(<SpoolSelectionFooter {...defaultProps} hasSpools={false} />);
    expect(screen.queryByText(/CONTINUAR/)).not.toBeInTheDocument();
  });

  it('disables continue button when selectedCount is 0', () => {
    render(<SpoolSelectionFooter {...defaultProps} selectedCount={0} />);
    const btn = screen.getByText(/CONTINUAR CON 0 SPOOLS/).closest('button');
    expect(btn).toBeDisabled();
  });

  it('enables continue button when selectedCount > 0', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    const btn = screen.getByText(/CONTINUAR CON 2 SPOOLS/).closest('button');
    expect(btn).not.toBeDisabled();
  });

  it('uses singular SPOOL for count of 1', () => {
    render(<SpoolSelectionFooter {...defaultProps} selectedCount={1} />);
    expect(screen.getByText('CONTINUAR CON 1 SPOOL')).toBeInTheDocument();
  });

  it('uses plural SPOOLS for count > 1', () => {
    render(<SpoolSelectionFooter {...defaultProps} selectedCount={5} />);
    expect(screen.getByText('CONTINUAR CON 5 SPOOLS')).toBeInTheDocument();
  });

  it('calls onContinue when clicked', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    fireEvent.click(screen.getByText(/CONTINUAR CON 2 SPOOLS/).closest('button')!);
    expect(defaultProps.onContinue).toHaveBeenCalledTimes(1);
  });
});

describe('SpoolSelectionFooter — navigation buttons', () => {
  it('always shows VOLVER button', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    expect(screen.getByText('VOLVER')).toBeInTheDocument();
  });

  it('always shows INICIO button', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    expect(screen.getByText('INICIO')).toBeInTheDocument();
  });

  it('calls onBack when VOLVER clicked', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    fireEvent.click(screen.getByText('VOLVER').closest('button')!);
    expect(defaultProps.onBack).toHaveBeenCalledTimes(1);
  });

  it('calls onHome when INICIO clicked', () => {
    render(<SpoolSelectionFooter {...defaultProps} />);
    fireEvent.click(screen.getByText('INICIO').closest('button')!);
    expect(defaultProps.onHome).toHaveBeenCalledTimes(1);
  });

  it('shows VOLVER and INICIO even when hasSpools is false', () => {
    render(<SpoolSelectionFooter {...defaultProps} hasSpools={false} />);
    expect(screen.getByText('VOLVER')).toBeInTheDocument();
    expect(screen.getByText('INICIO')).toBeInTheDocument();
  });
});
