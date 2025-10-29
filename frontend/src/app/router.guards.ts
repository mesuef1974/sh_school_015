// Router guards scaffolding — not wired by default to avoid breaking current app startup.
// To enable later: import { installRouterGuards } in your router setup and call it with the Router instance.

import type { Router } from "vue-router";
import type { Scope } from "./rbac";
import { requireAny } from "./rbac";

export function installRouterGuards(router: Router) {
  router.beforeEach((to, _from, next) => {
    const required = (to.meta?.scopes as Scope[] | undefined) || [];
    if (required.length && !requireAny(required)) {
      // Optional: preserve intended path for redirect after login/authorization
      return next({ name: "forbidden", query: { r: to.fullPath } });
    }
    next();
  });
}
