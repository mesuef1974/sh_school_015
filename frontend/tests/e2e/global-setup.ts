/*
 Global setup for Playwright E2E
 - Waits for the Vite dev server to be reachable before any test runs.
 - Honors E2E_BASE_URL (defaults to http://127.0.0.1:5173).
*/

import type { FullConfig } from '@playwright/test';

const DEFAULT_BASE = 'http://127.0.0.1:5173';

async function waitForServer(url: string, timeoutMs = 60_000): Promise<void> {
  const started = Date.now();
  const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

  let lastErr: any;
  while (Date.now() - started < timeoutMs) {
    try {
      const resp = await fetch(url, { method: 'GET' });
      if (resp.ok || (resp.status >= 200 && resp.status < 500)) {
        return;
      }
      lastErr = new Error(`HTTP ${resp.status}`);
    } catch (e) {
      lastErr = e;
    }
    await delay(500);
  }
  throw new Error(`Dev server did not become ready at ${url} within ${timeoutMs}ms. Last error: ${lastErr}`);
}

export default async function globalSetup(_config: FullConfig) {
  const base = (process.env.E2E_BASE_URL || DEFAULT_BASE).replace(/\/?(#.*)?$/, '/');
  // Try a few common paths to increase likelihood of a 2xx/3xx status
  const candidates = [base, base + 'index.html'];
  for (const u of candidates) {
    try {
      await waitForServer(u, 90_000);
      // eslint-disable-next-line no-console
      console.log(`[e2e] Dev server is ready at ${u}`);
      return;
    } catch {
      // try next
    }
  }
  // Final attempt against base
  await waitForServer(base, 90_000);
}