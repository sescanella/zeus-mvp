/**
 * Tests for SpoolListContext — provider + useSpoolList hook
 *
 * Tests cover:
 * 1. useSpoolList throws outside provider
 * 2. addSpool fetches status and adds to list
 * 3. addSpool rejects duplicate tags
 * 4. removeSpool removes from list
 * 5. removeSpool syncs localStorage via saveTags
 * 6. refreshAll calls batchGetStatus with all tracked tags
 * 7. refreshAll is no-op when list is empty
 * 8. refreshSingle updates one spool in place
 * 9. On mount, loads tags from localStorage and hydrates via batchGetStatus
 * 10. On mount with empty localStorage, state is empty array (no API call)
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
  loadTags: jest.fn(),
  saveTags: jest.fn(),
}));

import { getSpoolStatus, batchGetStatus } from '@/lib/api';
import { loadTags, saveTags } from '@/lib/local-storage';

const mockGetSpoolStatus = getSpoolStatus as jest.MockedFunction<typeof getSpoolStatus>;
const mockBatchGetStatus = batchGetStatus as jest.MockedFunction<typeof batchGetStatus>;
const mockLoadTags = loadTags as jest.MockedFunction<typeof loadTags>;
const mockSaveTags = saveTags as jest.MockedFunction<typeof saveTags>;

// ─── Helper: build a minimal SpoolCardData ────────────────────────────────────

function makeSpoolCard(tag: string): SpoolCardData {
  return {
    tag_spool: tag,
    ocupado_por: null,
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
  // Default: empty localStorage (no persisted tags)
  mockLoadTags.mockReturnValue([]);
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
      expect(mockLoadTags).toHaveBeenCalled();
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
      expect(mockLoadTags).toHaveBeenCalled();
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
      expect(mockLoadTags).toHaveBeenCalled();
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

  // Test 5: removeSpool syncs localStorage via saveTags
  it('removeSpool syncs localStorage via saveTags', async () => {
    const spoolCard1 = makeSpoolCard('OT-001');
    const spoolCard2 = makeSpoolCard('OT-002');
    mockGetSpoolStatus
      .mockResolvedValueOnce(spoolCard1)
      .mockResolvedValueOnce(spoolCard2);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadTags).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.addSpool('OT-001');
    });

    await act(async () => {
      await result.current.addSpool('OT-002');
    });

    mockSaveTags.mockClear();

    act(() => {
      result.current.removeSpool('OT-001');
    });

    // saveTags called with remaining tags
    await waitFor(() => {
      expect(mockSaveTags).toHaveBeenCalledWith(['OT-002']);
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
      expect(mockLoadTags).toHaveBeenCalled();
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
      expect(mockLoadTags).toHaveBeenCalled();
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
      expect(mockLoadTags).toHaveBeenCalled();
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

  // Test 9: On mount, loads tags from localStorage and hydrates via batchGetStatus
  it('on mount with persisted tags, loads and hydrates via batchGetStatus', async () => {
    const persistedTags = ['OT-001', 'OT-002'];
    mockLoadTags.mockReturnValue(persistedTags);

    const hydratedCards = [makeSpoolCard('OT-001'), makeSpoolCard('OT-002')];
    mockBatchGetStatus.mockResolvedValue(hydratedCards);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(result.current.spools).toHaveLength(2);
    });

    expect(mockLoadTags).toHaveBeenCalled();
    expect(mockBatchGetStatus).toHaveBeenCalledWith(['OT-001', 'OT-002']);
    expect(result.current.spools).toEqual(hydratedCards);
  });

  // Test 10: On mount with empty localStorage, state is empty array (no API call)
  it('on mount with empty localStorage, state is empty array and no API call', async () => {
    mockLoadTags.mockReturnValue([]);

    const { result } = renderHook(() => useSpoolList(), { wrapper });

    await waitFor(() => {
      expect(mockLoadTags).toHaveBeenCalled();
    });

    // Give time for any async operations
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(mockBatchGetStatus).not.toHaveBeenCalled();
    expect(result.current.spools).toHaveLength(0);
  });
});
