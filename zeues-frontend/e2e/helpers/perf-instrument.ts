/**
 * Shared instrumentation for T-136 performance flows.
 *
 * Each flow spec uses these helpers to:
 *   1. Pre-populate localStorage with the 200 staging tags before navigation.
 *   2. Attach console + network listeners.
 *   3. Capture timing snapshots at marked points.
 *   4. Persist artefacts (JSON metrics + console + network + screenshot).
 *
 * Output structure under test-results/perf-baseline/<flow-name>/:
 *   metrics.json
 *   network.json
 *   console.txt
 *   screenshot.png
 */
import type { Page, BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export const ROOT_OUTPUT = path.resolve(__dirname, '../../test-results/perf-baseline');
export const FIXTURE_PATH = path.resolve(__dirname, '../fixtures/staging-tags.json');

export interface NetworkRecord {
  url: string;
  method: string;
  status: number | null;
  duration_ms: number;
  size_bytes: number | null;
  started_at_ms: number;
}

export interface ConsoleRecord {
  type: string;
  text: string;
  location?: string;
}

export interface FlowMetrics {
  flow: string;
  timestamp: string;
  notes?: string;
  spool_cards_rendered?: number;
  timings_ms: Record<string, number>;
  api_request_count: number;
  api_total_bytes: number;
  api_total_time_ms: number;
  console_error_count: number;
  console_warning_count: number;
}

/**
 * Reads the staging tag fixture written by scripts/dump_staging_tags.py.
 */
export function loadFixtureTags(): string[] {
  const raw = fs.readFileSync(FIXTURE_PATH, 'utf-8');
  const parsed = JSON.parse(raw) as { tags: string[] };
  return parsed.tags;
}

/**
 * Pre-populates localStorage with the given tags BEFORE the page navigates.
 * Must be called before page.goto().
 */
export async function hydrateLocalStorage(
  context: BrowserContext,
  tags: string[]
): Promise<void> {
  const persisted = tags.map((tag) => ({ tag, priority: null }));
  await context.addInitScript((data) => {
    // Same key as zeues-frontend/lib/local-storage.ts STORAGE_KEY.
    localStorage.setItem('zeues_v5_spool_tags', JSON.stringify(data));
  }, persisted);
}

/**
 * Attaches console + network listeners. Returns getters for the captured arrays
 * (mutable references — keep listening until the spec writes artefacts).
 */
export function attachInstrumentation(page: Page): {
  network: NetworkRecord[];
  consoleLog: ConsoleRecord[];
} {
  const network: NetworkRecord[] = [];
  const consoleLog: ConsoleRecord[] = [];

  page.on('console', (msg) => {
    consoleLog.push({
      type: msg.type(),
      text: msg.text(),
      location: msg.location().url,
    });
  });

  page.on('pageerror', (err) => {
    consoleLog.push({ type: 'pageerror', text: err.message });
  });

  const requestStarts = new Map<string, number>();
  page.on('request', (req) => {
    if (req.url().includes('/api/')) {
      requestStarts.set(req.url() + ':' + req.method() + ':' + Date.now(), Date.now());
    }
  });
  page.on('response', async (res) => {
    const req = res.request();
    if (!req.url().includes('/api/')) return;
    let started = Date.now();
    // Best-effort: find the most recent matching start
    for (const [k, v] of requestStarts.entries()) {
      if (k.startsWith(req.url() + ':' + req.method())) {
        started = v;
        requestStarts.delete(k);
        break;
      }
    }
    let size: number | null = null;
    try {
      const body = await res.body();
      size = body.length;
    } catch {
      size = null;
    }
    network.push({
      url: req.url(),
      method: req.method(),
      status: res.status(),
      duration_ms: Date.now() - started,
      size_bytes: size,
      started_at_ms: started,
    });
  });

  return { network, consoleLog };
}

/**
 * Counts SpoolCard elements in the DOM (matches by TAG-shaped textContent).
 * SpoolCard.tsx uses role="button" without a stable testid, so we filter
 * role=button elements that contain a TAG_SPOOL pattern.
 */
export async function countSpoolCards(page: Page): Promise<number> {
  return page.evaluate(() => {
    const allButtons = document.querySelectorAll('[role="button"]');
    let count = 0;
    allButtons.forEach((b) => {
      const text = b.textContent ?? '';
      if (/MK-\d{4}-[A-Z]{2}-\d+-\d{3}/.test(text)) count += 1;
    });
    return count;
  });
}

/**
 * Writes metrics.json + network.json + console.txt + (optional) screenshot
 * to test-results/perf-baseline/<flow>/.
 */
export async function writeArtefacts(
  page: Page,
  flow: string,
  metrics: FlowMetrics,
  network: NetworkRecord[],
  consoleLog: ConsoleRecord[],
  options: { screenshot?: boolean } = { screenshot: true }
): Promise<string> {
  const dir = path.join(ROOT_OUTPUT, flow);
  fs.mkdirSync(dir, { recursive: true });

  fs.writeFileSync(path.join(dir, 'metrics.json'), JSON.stringify(metrics, null, 2));
  fs.writeFileSync(path.join(dir, 'network.json'), JSON.stringify(network, null, 2));
  fs.writeFileSync(
    path.join(dir, 'console.txt'),
    consoleLog
      .map((m) => `[${m.type}] ${m.text}${m.location ? ` (${m.location})` : ''}`)
      .join('\n')
  );

  if (options.screenshot) {
    await page.screenshot({ path: path.join(dir, 'screenshot.png'), fullPage: true });
  }

  console.log(`\n=== ${flow.toUpperCase()} ===`);
  console.log(JSON.stringify(metrics, null, 2));
  console.log(`Artefacts: ${dir}`);

  return dir;
}

/**
 * Helper: summarise network records into the metrics struct fields.
 */
export function summariseNetwork(network: NetworkRecord[]): {
  api_request_count: number;
  api_total_bytes: number;
  api_total_time_ms: number;
} {
  return {
    api_request_count: network.length,
    api_total_bytes: network.reduce((sum, r) => sum + (r.size_bytes ?? 0), 0),
    api_total_time_ms: network.reduce((sum, r) => sum + r.duration_ms, 0),
  };
}

/**
 * Helper: count console errors + warnings.
 */
export function summariseConsole(consoleLog: ConsoleRecord[]): {
  console_error_count: number;
  console_warning_count: number;
} {
  return {
    console_error_count: consoleLog.filter((m) => m.type === 'error' || m.type === 'pageerror')
      .length,
    console_warning_count: consoleLog.filter((m) => m.type === 'warning').length,
  };
}
