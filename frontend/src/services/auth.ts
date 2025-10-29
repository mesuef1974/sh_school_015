// Minimal auth service helpers (Phase 1)
// - Uses relative /api endpoints to leverage Vite proxy in dev
// - Keeps access token in-memory placeholder to avoid storage risks; to be replaced by Pinia later

import { http, httpNoCreds } from "./http";

export interface LoginPayload {
  username: string;
  password: string;
}

export interface TokenPair {
  access?: string;
  refresh?: string;
}

function setAccessToken(token?: string) {
  // Memory-only placeholder; a proper store will replace this later
  (window as any).__accessToken = token || undefined;
}

export async function login(data: LoginPayload): Promise<TokenPair> {
  // Prefer the unified endpoint
  const resp = await httpNoCreds.post("/v1/auth/login/", data);
  const tokens = (resp.data || {}) as TokenPair;
  if (tokens.access) setAccessToken(tokens.access);
  return tokens;
}

export async function logout(): Promise<void> {
  try {
    await http.post("/v1/auth/logout/", {});
  } finally {
    setAccessToken(undefined);
  }
}

export async function refresh(): Promise<TokenPair | void> {
  const resp = await httpNoCreds.post("/v1/auth/refresh/", {});
  const tokens = (resp.data || {}) as TokenPair;
  if (tokens?.access) setAccessToken(tokens.access);
  return tokens;
}

export function getAccessToken(): string | undefined {
  return (window as any).__accessToken as string | undefined;
}
