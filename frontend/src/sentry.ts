// Optional Sentry bootstrap for Vue 3
// This module is safe to import dynamically only when VITE_SENTRY_DSN is defined.
// It does nothing if DSN is empty.

import type { App } from 'vue'

export async function initSentry(app: App) {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
  if (!dsn) return
  try {
    const Sentry = await import('@sentry/vue')
    const env = (import.meta.env.MODE || 'development') as string
    const release = (import.meta.env.VITE_RELEASE || '') as string
    const traces = parseFloat((import.meta as any).env.VITE_SENTRY_TRACES || '0') || 0

    Sentry.init({
      app,
      dsn,
      environment: env,
      release: release || undefined,
      // Keep tracing disabled by default unless explicitly set
      integrations: [Sentry.browserTracingIntegration?.()].filter(Boolean) as any,
      tracesSampleRate: traces,
      // PII off by default
      sendDefaultPii: false as any,
    } as any)
  } catch (e) {
    // Silently ignore any errors to avoid impacting the app
    console.warn('[sentry] init skipped:', (e as any)?.message || e)
  }
}
