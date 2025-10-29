// Shared runtime config helpers for Frontend
// Provides backend origin (useful for linking to legacy Django pages during dev)

// Vite injects import.meta.env at build time
const VITE_ORIGIN = (import.meta as any).env?.VITE_BACKEND_ORIGIN as string | undefined;

function normalizeOrigin(x: string | undefined): string {
  if (!x || typeof x !== "string") return "";
  // Remove trailing slash
  return x.replace(/\/+$/, "");
}

// Default to HTTPS dev backend started by scripts/serve_https.ps1
const DEFAULT_DEV_BACKEND = "https://127.0.0.1:8443";

export const backendOrigin: string = normalizeOrigin(VITE_ORIGIN) || DEFAULT_DEV_BACKEND;

export function backendUrl(path: string): string {
  if (!path.startsWith("/")) path = "/" + path;
  return `${backendOrigin}${path}`;
}
