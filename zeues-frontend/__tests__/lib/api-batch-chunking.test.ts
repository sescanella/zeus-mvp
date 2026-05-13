/**
 * Regression tests for batchGetStatus chunking (T-136 Fase 0).
 *
 * The backend BatchStatusRequest enforces max_length=100. Before T-136 the
 * frontend sent a single request regardless of tag count, so any list of
 * >100 spools resulted in a silent 422 and an empty home. These tests pin
 * the chunking contract so a regression that re-removes chunking fails CI.
 */
import { batchGetStatus, BATCH_STATUS_CHUNK_SIZE } from '@/lib/api';
import type { SpoolCardData } from '@/lib/types';

const minimalCard = (tag: string): SpoolCardData =>
  ({
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
    completion_history: [],
    fecha_armado: null,
    armador_display: null,
    fecha_soldadura: null,
    soldador_display: null,
    operacion_actual: null,
    estado_trabajo: 'LIBRE',
    ciclo_rep: null,
  } as unknown as SpoolCardData);

describe('batchGetStatus chunking', () => {
  const originalFetch = global.fetch;
  let fetchMock: jest.Mock;

  beforeEach(() => {
    fetchMock = jest.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body ?? '{}')) as { tags?: string[] };
      const tags = body.tags ?? [];
      // Backend mock: respect the 100-tag cap, return one card per tag.
      if (tags.length > BATCH_STATUS_CHUNK_SIZE) {
        return {
          ok: false,
          status: 422,
          statusText: 'Unprocessable Entity',
          json: async () => ({ detail: [{ msg: 'tags exceeds 100' }] }),
        } as unknown as Response;
      }
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({
          spools: tags.map((t) => minimalCard(t)),
          total: tags.length,
        }),
      } as unknown as Response;
    });
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('returns empty result for empty input without hitting the network', async () => {
    const result = await batchGetStatus([]);
    expect(result).toEqual({ spools: [], errors: [] });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('uses a single request for inputs at or below the chunk size', async () => {
    const tags = Array.from({ length: BATCH_STATUS_CHUNK_SIZE }, (_, i) => `T-${i}`);
    const result = await batchGetStatus(tags);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.spools).toHaveLength(BATCH_STATUS_CHUNK_SIZE);
    expect(result.spools[0].tag_spool).toBe('T-0');
    expect(result.spools[BATCH_STATUS_CHUNK_SIZE - 1].tag_spool).toBe(
      `T-${BATCH_STATUS_CHUNK_SIZE - 1}`
    );
    expect(result.errors).toEqual([]);
  });

  it('splits inputs above the chunk size into multiple requests', async () => {
    const tags = Array.from({ length: 200 }, (_, i) => `T-${i}`);
    const result = await batchGetStatus(tags);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.spools).toHaveLength(200);
  });

  it('preserves input order across chunks', async () => {
    const tags = Array.from({ length: 250 }, (_, i) => `T-${i}`);
    const result = await batchGetStatus(tags);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(result.spools.map((r) => r.tag_spool)).toEqual(tags);
  });

  it('does not send any chunk that exceeds BATCH_STATUS_CHUNK_SIZE', async () => {
    const tags = Array.from({ length: 137 }, (_, i) => `T-${i}`);
    await batchGetStatus(tags);
    const sentChunkSizes = fetchMock.mock.calls.map((call) => {
      const init = call[1] as RequestInit;
      const body = JSON.parse(String(init.body)) as { tags: string[] };
      return body.tags.length;
    });
    expect(sentChunkSizes.every((n) => n <= BATCH_STATUS_CHUNK_SIZE)).toBe(true);
    expect(sentChunkSizes.reduce((a, b) => a + b, 0)).toBe(137);
  });
});
