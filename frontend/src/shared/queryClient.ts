import { QueryClient } from "@tanstack/vue-query";

// Singleton QueryClient used across the app so we can reliably clear caches on logout
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function clearAllQueries() {
  try {
    queryClient.clear();
  } catch {}
}