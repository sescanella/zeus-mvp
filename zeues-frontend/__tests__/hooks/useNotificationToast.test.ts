import { renderHook, act } from '@testing-library/react';
import { useNotificationToast, ToastType } from '@/hooks/useNotificationToast';

describe('useNotificationToast', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('has empty toasts array on initial state', () => {
    const { result } = renderHook(() => useNotificationToast());
    expect(result.current.toasts).toEqual([]);
  });

  it('enqueue adds a success toast with message and type', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('Exito', 'success');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Exito');
    expect(result.current.toasts[0].type).toBe('success');
    expect(result.current.toasts[0].id).toBeTruthy();
  });

  it('enqueue adds an error toast with correct type', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('Error', 'error');
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Error');
    expect(result.current.toasts[0].type).toBe('error');
  });

  it('multiple enqueue calls accumulate toasts (queue, not replace)', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('First', 'success');
      result.current.enqueue('Second', 'error');
      result.current.enqueue('Third', 'success');
    });

    expect(result.current.toasts).toHaveLength(3);
    expect(result.current.toasts[0].message).toBe('First');
    expect(result.current.toasts[1].message).toBe('Second');
    expect(result.current.toasts[2].message).toBe('Third');
  });

  it('dismiss removes a specific toast by id', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('First', 'success');
      result.current.enqueue('Second', 'error');
    });

    const idToRemove = result.current.toasts[0].id;

    act(() => {
      result.current.dismiss(idToRemove);
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Second');
  });

  it('dismiss with nonexistent id is a no-op', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('Toast', 'success');
    });

    act(() => {
      result.current.dismiss('nonexistent-id');
    });

    expect(result.current.toasts).toHaveLength(1);
  });

  it('auto-dismisses toast after 4000ms', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('Auto-dismiss me', 'success');
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      jest.advanceTimersByTime(4000);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('toast is not removed before 4000ms', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('Still here', 'success');
    });

    act(() => {
      jest.advanceTimersByTime(3999);
    });

    expect(result.current.toasts).toHaveLength(1);
  });

  it('two rapid enqueue calls produce different IDs (no collision)', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('First', 'success');
      result.current.enqueue('Second', 'error');
    });

    const ids = result.current.toasts.map((t) => t.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it('each toast is independently auto-dismissed at the correct time', () => {
    const { result } = renderHook(() => useNotificationToast());

    act(() => {
      result.current.enqueue('First', 'success');
    });

    act(() => {
      jest.advanceTimersByTime(2000);
    });

    act(() => {
      result.current.enqueue('Second', 'error');
    });

    // First toast should auto-dismiss at 4000ms from its creation
    act(() => {
      jest.advanceTimersByTime(2000); // total 4000ms from first, 2000ms from second
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Second');
  });
});
