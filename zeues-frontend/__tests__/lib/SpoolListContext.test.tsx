/**
 * Tests for SpoolListContext — provider + useSpoolList hook
 *
 * Tests cover:
 * 1. useSpoolList throws outside provider
 * 2. addSpool fetches status and adds to list
 * 3. addSpool rejects duplicate tags
 * 4. removeSpool removes from list
 * 5. removeSpool syncs localStorage via savePersistedSpools
 * 6. refreshAll calls batchGetStatus with all tracked tags
 * 7. refreshAll is no-op when list is empty
 * 8. refreshSingle updates one spool in place
 * 9. On mount, loads persisted spools from localStorage and hydrates via batchGetStatus
 * 10. On mount with empty localStorage, state is empty array (no API call)
 * 11. setPriority updates priorities map
 * 12. setPriority persists via savePersistedSpools on next render
 * 13. priorities exposed in context value
 *
 * Reference: 04-01-PLAN.md Task 1
 */

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { SpoolListProvider, useSpoolList } from '@/lib/SpoolListContext';
import type { SpoolCardData } from '@/lib/types';

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('@/lib/api', () => ({
  getSpoolStatus: jest.fn(),
  batchGetStatus: jest.fn(),
}));

jest.mock('@/lib/local-storage', () => ({
  loadPersistedSpools: jest.fn(),
  savePersistedSpools: jest.fn(),
  loadTags: jest.fn(),
}));

import { getSpoolStatus, batchGetStatus } from '@/lib/api';
import { loadPersistedSpools, savePersistedSpools } from '@/lib/local-storage';
import type { PersistedSpool } from '@/lib/local-storage';

const mockGetSpoolStatus = getSpoolStatus as jest.MockedFunction<typeof getSpoolStatus>;
const mockBatchGetStatus = batchGetStatus as jest.MockedFunction<typeof batchGetStatus>;
const mockLoadPersistedSpools = loadPersistedSpools as jest.MockedFunction<typeof loadPersistedSpools>;
const mockSavePersistedSpools = savePersistedSpools as jest.MockedFunction<typeof savePersistedSpools>;

// ─── Helper: build a minimal SpoolCardData ────────────────────────────────────

function makeSpoolCard(tag: string): SpoolCardData {
  return {
    tag_spool: tag,
    nv: null,
    ocupado_por: null,
    ocupado_por_display: null,
    fecha_ocupacion: null,
    estado_detalle: null,
    total_uniones: null,
    uniones_arm_completadas: null,
    uniones_sold_completadas: null,
    pulgadas_arm: null,
    pulgadas_sold: null,
    operacion_actual: null,
    estado_trabajo: 'LIBRE',
    ciclo_rep: null,
  };
}

// ─── Test wrapper ─────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SpoolListProvider>{children}</SpoolListProvider>
);

// ─── Tests ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Default: empty localStorage (no persisted spools)
  mockLoadPersistedSpools.mockReturnValue([]);
  mockBatchGetStatus.mockResolvedValue([]);
});

describe('useSpoolList', () => {
  // Test 1: useSpoolList throws when used outside provider
  it('throws when used outside SpoolListProvider', () => {
    // Suppress React error output for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useSpoolList());
    }).toThrow('useSpoolList must be used within a SpoolListProvider');

    consoleSpy.mockRestore();
  });

  // Test 2: addSpool fetches status via getSpoolStatus and adds to list
  it('addSpool fetches status via getSpoolStatus and adds to list', async () => {
    const spoolCard = makeSpoolCard('OT-001');
    mockGetSpoolStatus.mockResolvedValue(spoolCard);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    // Wait for mount effect
    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    expect(mockGetSpoolStatus).toHaveBeenCalledWith('OT-001');
    expect(result.current.spools).toHaveLength(1);
    expect(result.current.spools[0].tag_spool).toBe('OT-001');
  });

  // Test 3: addSpool rejects duplicate tag (no API call, list unchanged)
  it('addSpool rejects duplicate tag without calling API', async () => {
    const spoolCard = makeSpoolCard('OT-001');
    mockGetSpoolStatus.mockResolvedValue(spoolCard);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    // Add spool once
    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    expect(result.current.spools).toHaveLength(1);

    // Try to add the same spool again
    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    // API called only once (first add), not on duplicate
    expect(mockGetSpoolStatus).toHaveBeenCalledTimes(1);
    expect(result.current.spools).toHaveLength(1);
  });

  // Test 4: removeSpool removes from list
  it('removeSpool removes spool from list', async () => {
    const spoolCard = makeSpoolCard('OT-001');
    mockGetSpoolStatus.mockResolvedValue(spoolCard);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    expect(result.current.spools).toHaveLength(1);

    act(() => {
      result.current.removeSpool('OT-001');
    });

    expect(result.current.spools).toHaveLength(0);
  });

  // Test 5: removeSpool syncs localStorage via savePersistedSpools
  it('removeSpool syncs localStorage via savePersistedSpools', async () => {
    const spoolCard1 = makeSpoolCard('OT-001');
    const spoolCard2 = makeSpoolCard('OT-002');
    mockGetSpoolStatus
      .mockResolvedValueOnce(spoolCard1)
      .mockResolvedValueOnce(spoolCard2);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    await act(async () => {
      await result.current.addSpool('OT-002');
    });

    mockSavePersistedSpools.mockClear();

    act(() => {
      result.current.removeSpool('OT-001');
    });

    // savePersistedSpools called with remaining spool
    await waitFor(() => {
      expect(mockSavePersistedSpools).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ tag: 'OT-002' }),
        ])
      );
      // OT-001 should NOT be in the persisted list
      const lastCall = mockSavePersistedSpools.mock.calls[mockSavePersistedSpools.mock.calls.length - 1][0] as PersistedSpool[];
      expect(lastCall.find((s) => s.tag === 'OT-001')).toBeUndefined();
    });
  });

  // Test 6: refreshAll calls batchGetStatus with all tracked tags
  it('refreshAll calls batchGetStatus with all tracked tags', async () => {
    const spoolCard1 = makeSpoolCard('OT-001');
    const spoolCard2 = makeSpoolCard('OT-002');
    mockGetSpoolStatus
      .mockResolvedValueOnce(spoolCard1)
      .mockResolvedValueOnce(spoolCard2);

    const freshCards = [
      { ...spoolCard1, estado_detalle: 'updated1' },
      { ...spoolCard2, estado_detalle: 'updated2' },
    ];
    mockBatchGetStatus.mockResolvedValue(freshCards);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    await act(async () => {
      await result.current.addSpool('OT-002');
    });

    // batchGetStatus called during mount (empty) — clear before refreshAll test
    mockBatchGetStatus.mockClear();

    await act(async () => {
      await result.current.refreshAll();
    });

    expect(mockBatchGetStatus).toHaveBeenCalledWith(['OT-001', 'OT-002']);
    expect(result.current.spools).toEqual(freshCards);
  });

  // Test 7: refreshAll is no-op when list is empty (no API call)
  it('refreshAll is no-op when list is empty', async () => {
    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    // Clear the initial batchGetStatus call from mount
    mockBatchGetStatus.mockClear();

    await act(async () => {
      await result.current.refreshAll();
    });

    expect(mockBatchGetStatus).not.toHaveBeenCalled();
    expect(result.current.spools).toHaveLength(0);
  });

  // Test 8: refreshSingle updates one spool in place
  it('refreshSingle updates one spool in place', async () => {
    const spoolCard1 = makeSpoolCard('OT-001');
    const spoolCard2 = makeSpoolCard('OT-002');
    mockGetSpoolStatus
      .mockResolvedValueOnce(spoolCard1)
      .mockResolvedValueOnce(spoolCard2);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    await act(async () => {
      await result.current.addSpool('OT-002');
    });

    const updatedCard = { ...spoolCard1, estado_detalle: 'EN_PROGRESO actualizado' };
    mockGetSpoolStatus.mockResolvedValue(updatedCard);

    await act(async () => {
      await result.current.refreshSingle('OT-001');
    });

    expect(mockGetSpoolStatus).toHaveBeenLastCalledWith('OT-001');
    expect(result.current.spools).toHaveLength(2);
    expect(result.current.spools.find((s) => s.tag_spool === 'OT-001')).toEqual(updatedCard);
    // OT-002 should be unchanged
    expect(result.current.spools.find((s) => s.tag_spool === 'OT-002')).toEqual(spoolCard2);
  });

  // Test 9: On mount, loads persisted spools from localStorage and hydrates via batchGetStatus
  it('on mount with persisted spools, loads priorities and hydrates via batchGetStatus', async () => {
    const persisted: PersistedSpool[] = [
      { tag: 'OT-001', priority: 1 },
      { tag: 'OT-002', priority: null },
    ];
    mockLoadPersistedSpools.mockReturnValue(persisted);

    const hydratedCards = [makeSpoolCard('OT-001'), makeSpoolCard('OT-002')];
    mockBatchGetStatus.mockResolvedValue(hydratedCards);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(result.current.spools).toHaveLength(2);
    });

    expect(mockLoadPersistedSpools).toHaveBeenCalled();
    expect(mockBatchGetStatus).toHaveBeenCalledWith(['OT-001', 'OT-002']);
    expect(result.current.spools).toEqual(hydratedCards);
    // Priorities should be loaded
    expect(result.current.priorities.get('OT-001')).toBe(1);
    expect(result.current.priorities.get('OT-002')).toBeNull();
  });

  // Test 10: On mount with empty localStorage, state is empty array (no API call)
  it('on mount with empty localStorage, state is empty array and no API call', async () => {
    mockLoadPersistedSpools.mockReturnValue([]);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    // Give time for any async operations
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(mockBatchGetStatus).not.toHaveBeenCalled();
    expect(result.current.spools).toHaveLength(0);
  });

  // Test 11: setPriority updates priorities map in context
  it('setPriority updates priorities map', async () => {
    const spoolCard = makeSpoolCard('OT-001');
    mockGetSpoolStatus.mockResolvedValue(spoolCard);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    expect(result.current.priorities.get('OT-001')).toBeUndefined();

    act(() => {
      result.current.setPriority('OT-001', 1);
    });

    expect(result.current.priorities.get('OT-001')).toBe(1);

    act(() => {
      result.current.setPriority('OT-001', null);
    });

    expect(result.current.priorities.get('OT-001')).toBeNull();
  });

  // Test 12: setPriority persists via savePersistedSpools
  it('setPriority triggers savePersistedSpools with correct priority', async () => {
    const spoolCard = makeSpoolCard('OT-001');
    mockGetSpoolStatus.mockResolvedValue(spoolCard);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    mockSavePersistedSpools.mockClear();

    act(() => {
      result.current.setPriority('OT-001', 2);
    });

    await waitFor(() => {
      expect(mockSavePersistedSpools).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ tag: 'OT-001', priority: 2 }),
        ])
      );
    });
  });

  // Test 13: priorities is exposed in context value with correct initial state
  it('priorities is an empty Map on initial render with no persisted spools', async () => {
    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    expect(result.current.priorities).toBeInstanceOf(Map);
    expect(result.current.priorities.size).toBe(0);
  });

  // Test 14: removeSpool also removes priority from priorities map
  it('removeSpool removes priority from priorities map', async () => {
    const spoolCard = makeSpoolCard('OT-001');
    mockGetSpoolStatus.mockResolvedValue(spoolCard);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadPersistedSpools).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    act(() => {
      result.current.setPriority('OT-001', 1);
    });

    expect(result.current.priorities.get('OT-001')).toBe(1);

    act(() => {
      result.current.removeSpool('OT-001');
    });

    expect(result.current.priorities.has('OT-001')).toBe(false);
  });
});
