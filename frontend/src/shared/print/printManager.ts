/* Centralized print manager for the whole platform.
   Provides a single API to trigger professional printing with consistent A4 setup.

   Usage:
     import { printManager } from "@/shared/print/printManager";
     // Default portrait
     printManager.print();
     // Explicit orientation
     printManager.print({ orientation: 'portrait' });
     printManager.print({ orientation: 'landscape' });

   Also exposed globally (configured in main.ts):
     window.printManager.printLandscape();

   Notes:
   - We inject a <style media="print"> with an @page rule to enforce A4 orientation/margins at print time.
   - We remove the injected style shortly after window.print() returns.
*/

export type PrintOrientation = 'portrait' | 'landscape';

export interface PrintOptions {
  orientation?: PrintOrientation; // default 'portrait'
  marginCm?: number;              // default 1 cm
  addBodyClass?: string;          // optional (deprecated) single class to add to body during print (removed afterwards)
  addBodyClasses?: string[];      // optional list of classes to add to body during print (removed afterwards)
  extraCss?: string;              // optional additional CSS (media=print) injected temporarily during print
}

export interface PrintElementOptions extends PrintOptions {
  target: Element | string;       // element or selector to focus printing on
  clean?: boolean;                // hide buttons/inputs/dropdowns inside target during print
}

export interface PrintElementsOptions extends PrintOptions {
  targets: (Element | string)[];  // multiple elements or selectors
  clean?: boolean;
}

function injectPageStyle(orientation: PrintOrientation, marginCm: number): HTMLStyleElement {
  const style = document.createElement('style');
  style.id = 'abs-print-orientation';
  style.media = 'print';
  style.innerHTML = `@page { size: A4 ${orientation}; margin: ${marginCm}cm; }`;
  document.head.appendChild(style);
  return style;
}

function safeRemove(el: Element | null | undefined) {
  if (!el) return;
  try { el.parentElement?.removeChild(el); } catch {}
}

function withTemporarySetup<T>(fn: () => T, opts?: PrintOptions): T {
  const orientation: PrintOrientation = opts?.orientation ?? 'portrait';
  const margin = typeof opts?.marginCm === 'number' ? Math.max(0.5, Math.min(5, opts!.marginCm!)) : 1;
  const bodyClass = opts?.addBodyClass || '';
  const bodyClasses = Array.isArray(opts?.addBodyClasses) ? (opts!.addBodyClasses as string[]) : [];
  // Respect a 'clean' flag if provided (from PrintPanelTrigger), even for full-page printing
  const wantsClean = !!(opts as any)?.clean;
  if (wantsClean && !bodyClasses.includes('print-clean')) bodyClasses.push('print-clean');

  const styleEl = injectPageStyle(orientation, margin);
  let extraStyleEl: HTMLStyleElement | null = null;
  if (opts?.extraCss && typeof opts.extraCss === 'string' && opts.extraCss.trim().length) {
    extraStyleEl = document.createElement('style');
    extraStyleEl.media = 'print';
    extraStyleEl.id = 'abs-print-extra';
    extraStyleEl.innerHTML = opts.extraCss;
    document.head.appendChild(extraStyleEl);
  }
  if (bodyClass) document.body.classList.add(bodyClass);
  for (const c of bodyClasses) {
    if (c && typeof c === 'string') document.body.classList.add(c);
  }
  const cleanup = () => {
    if (bodyClass) document.body.classList.remove(bodyClass);
    for (const c of bodyClasses) {
      if (c && typeof c === 'string') document.body.classList.remove(c);
    }
    safeRemove(styleEl);
    safeRemove(extraStyleEl as any);
  };
  try {
    return fn();
  } finally {
    // Allow the print dialog to open/render before cleanup
    const tidy = () => cleanup();
    setTimeout(tidy, 1000);
    try {
      window.addEventListener('afterprint', tidy, { once: true });
    } catch {}
  }
}

function print(opts?: PrintOptions) {
  withTemporarySetup(() => window.print(), opts);
}

function printPortrait() { print({ orientation: 'portrait' }); }
function printLandscape() { print({ orientation: 'landscape' }); }

function printElement(opts: PrintElementOptions) {
  const targetEl = typeof opts.target === 'string' ? document.querySelector(opts.target as string) : (opts.target as Element | null);
  if (!targetEl) {
    // fallback to normal print if target not found
    return print(opts);
  }
  // mark target and body for focus printing
  const BODY_FOCUS_CLASS = 'print-focus-mode';
  const TARGET_CLASS = 'print-focus-target';
  targetEl.classList.add(TARGET_CLASS);
  const classes = new Set<string>(opts.addBodyClasses || []);
  classes.add(BODY_FOCUS_CLASS);
  if (opts.clean) classes.add('print-clean');
  const merged: PrintOptions = { ...opts, addBodyClasses: Array.from(classes.values()) };
  withTemporarySetup(() => window.print(), merged);
  // cleanup target mark shortly after
  setTimeout(() => { try { targetEl.classList.remove(TARGET_CLASS); } catch {} }, 1000);
}

function printElements(opts: PrintElementsOptions) {
  const targets: Element[] = [];
  for (const t of opts.targets || []) {
    const el = typeof t === 'string' ? document.querySelector(t as string) : (t as Element | null);
    if (el) targets.push(el);
  }
  if (!targets.length) return print(opts);
  const BODY_FOCUS_CLASS = 'print-focus-mode';
  const TARGET_CLASS = 'print-focus-target';
  for (const el of targets) try { el.classList.add(TARGET_CLASS); } catch {}
  const classes = new Set<string>(opts.addBodyClasses || []);
  classes.add(BODY_FOCUS_CLASS);
  if (opts.clean) classes.add('print-clean');
  const merged: PrintOptions = { ...opts, addBodyClasses: Array.from(classes.values()) };
  withTemporarySetup(() => window.print(), merged);
  setTimeout(() => {
    for (const el of targets) try { el.classList.remove(TARGET_CLASS); } catch {}
  }, 1000);
}

export const printManager = {
  print,
  printPortrait,
  printLandscape,
  printElement,
  printElements,
};

// Augment global Window type for TS consumers
declare global {
  interface Window { printManager: typeof printManager }
}

// Auto-attach to window for easy access across the app (optional)
if (typeof window !== 'undefined') {
  // Don't overwrite if already set (hot module replacement)
  // @ts-ignore
  if (!window.printManager) {
    // @ts-ignore
    window.printManager = printManager;
  }
}