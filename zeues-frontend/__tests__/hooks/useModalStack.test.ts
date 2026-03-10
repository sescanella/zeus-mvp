import { renderHook, act } from '@testing-library/react';
import { useModalStack, ModalId } from '@/hooks/useModalStack';

describe('useModalStack', () => {
  it('has empty stack and null current on initial state', () => {
    const { result } = renderHook(() => useModalStack());
    expect(result.current.stack).toEqual([]);
    expect(result.current.current).toBeNull();
  });

  it('push adds a modal to the top of the stack', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.push('operation');
    });

    expect(result.current.stack).toEqual(['operation']);
    expect(result.current.current).toBe('operation');
  });

  it('push builds the stack correctly with multiple modals', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.push('operation');
    });
    act(() => {
      result.current.push('action');
    });

    expect(result.current.stack).toEqual(['operation', 'action']);
    expect(result.current.current).toBe('action');
  });

  it('pop removes only the top modal', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.push('operation');
      result.current.push('action');
    });
    act(() => {
      result.current.pop();
    });

    expect(result.current.stack).toEqual(['operation']);
    expect(result.current.current).toBe('operation');
  });

  it('pop on empty stack is a no-op', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.pop();
    });

    expect(result.current.stack).toEqual([]);
    expect(result.current.current).toBeNull();
  });

  it('clear empties entire stack regardless of size', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.push('operation');
      result.current.push('action');
      result.current.push('worker');
    });
    act(() => {
      result.current.clear();
    });

    expect(result.current.stack).toEqual([]);
    expect(result.current.current).toBeNull();
  });

  it('isOpen returns true when modal is the top of stack', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.push('operation');
      result.current.push('action');
    });

    expect(result.current.isOpen('action')).toBe(true);
  });

  it('isOpen returns false for non-top modals even if they are in the stack', () => {
    const { result } = renderHook(() => useModalStack());

    act(() => {
      result.current.push('operation');
      result.current.push('action');
    });

    expect(result.current.isOpen('operation')).toBe(false);
  });

  it('isOpen returns false for any modal when stack is empty', () => {
    const { result } = renderHook(() => useModalStack());

    expect(result.current.isOpen('operation')).toBe(false);
    expect(result.current.isOpen('action')).toBe(false);
  });

  it('multiple push calls build up the stack correctly', () => {
    const { result } = renderHook(() => useModalStack());

    const modals: ModalId[] = ['add-spool', 'operation', 'action', 'worker', 'metrologia'];
    act(() => {
      modals.forEach((m) => result.current.push(m));
    });

    expect(result.current.stack).toEqual(modals);
    expect(result.current.current).toBe('metrologia');
  });
});
