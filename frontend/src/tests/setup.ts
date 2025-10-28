// Vitest setup for Vue + Axios tests
import { vi } from "vitest";

// JSDOM already provided by vitest config; add minor stubs if needed
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Silence console.debug in tests unless explicitly enabled
const originalDebug = console.debug;
console.debug = (...args: any[]) => {
  if (import.meta.env.VITE_HTTP_DEBUG) originalDebug.apply(console, args);
};
