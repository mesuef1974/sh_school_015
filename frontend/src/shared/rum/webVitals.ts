// Lightweight Web Vitals collection with safe fallbacks
// Opt-in via VITE_RUM=1. If backend endpoint is missing, this will silently no-op.
import { onCLS, onFID, onLCP, onINP, onTTFB, type Metric } from 'web-vitals';

function sendToAnalytics(metric: Metric) {
  try {
    const body = JSON.stringify({
      name: metric.name,
      value: metric.value,
      id: metric.id,
      rating: (metric as any).rating,
      navigationType: (performance.getEntriesByType('navigation')[0] as any)?.type,
      url: location.pathname + location.search,
      ts: Date.now(),
    });
    const url = '/api/rum/vitals/';
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(url, blob);
    } else {
      // Fire-and-forget fetch
      fetch(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' }, keepalive: true }).catch(() => {});
    }
  } catch (e) {
    // As a fallback, log to console in dev
    try { if (import.meta.env.DEV) console.debug('[web-vitals]', metric.name, metric.value); } catch {}
  }
}

export function initWebVitals() {
  try {
    onCLS(sendToAnalytics);
    onFID(sendToAnalytics);
    onLCP(sendToAnalytics);
    onINP(sendToAnalytics);
    onTTFB(sendToAnalytics);
  } catch (e) {
    try { if (import.meta.env.DEV) console.warn('web-vitals init failed', e); } catch {}
  }
}

// Auto-init when imported
initWebVitals();
