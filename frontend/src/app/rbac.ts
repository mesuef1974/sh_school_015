// Minimal RBAC scaffolding for Phase 1 — standalone (not yet wired)
// Define scopes and helper checks. Later, integrate with backend claims or a user store.

export type Scope =
  | "attendance:read"
  | "attendance:write"
  | "grades:read"
  | "grades:write"
  | "timetable:read"
  | "timetable:write"
  | "notifications:read"
  | "notifications:write";

export interface UserInfo {
  id: number;
  username: string;
  roles?: string[];
  scopes?: Scope[];
}

export function getCurrentUser(): UserInfo | null {
  // Placeholder: pull from an auth store or a bootstrap endpoint later
  const w = window as any;
  return w.__currentUser || null;
}

export function getUserScopes(): Set<Scope> {
  const u = getCurrentUser();
  return new Set(u?.scopes || []);
}

export function userHas(scope: Scope): boolean {
  return getUserScopes().has(scope);
}

export function requireAny(scopes: Scope[]): boolean {
  const s = getUserScopes();
  if (!scopes || scopes.length === 0) return true;
  return scopes.some((x) => s.has(x));
}