// Axios HTTP client with safe defaults and robust, minimal interceptors.
// Phase 1: single-flight refresh, queued replay, bounded backoff, and lightweight error hook.

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";

export interface HttpOptions {
  baseURL?: string;
  withCredentials?: boolean;
}

// Use relative base to leverage Vite proxy in dev and avoid CORS
const BASE_URL = "/api";
const DEBUG = Boolean((import.meta as any).env?.VITE_HTTP_DEBUG) || false;

// ---- Refresh single-flight state (memory only; replace later with Pinia) ----
let refreshPromise: Promise<AxiosResponse<any>> | null = null;
let refreshSubscribers: Array<(ok: boolean) => void> = [];

function logDebug(...args: any[]) {
  if (DEBUG && typeof console !== "undefined") console.debug("[http]", ...args);
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function triggerRefresh(): Promise<AxiosResponse<any>> {
  if (!refreshPromise) {
    logDebug("Starting token refresh (single-flight)");
    refreshPromise = axios
      .post(`/api/v1/auth/refresh/`, {}, { withCredentials: true })
      .then((resp) => {
        logDebug("Refresh success");
        refreshSubscribers.forEach((fn) => fn(true));
        refreshSubscribers = [];
        return resp;
      })
      .catch((err) => {
        logDebug("Refresh failed", err?.response?.status || err?.message);
        refreshSubscribers.forEach((fn) => fn(false));
        refreshSubscribers = [];
        throw err;
      })
      .finally(() => {
        refreshPromise = null;
      });
  } else {
    logDebug("Joining in-flight refresh");
  }
  return refreshPromise;
}

let globalErrorHandler: ((error: unknown) => void) | null = null;
export function setHttpErrorHandler(handler: ((error: unknown) => void) | null) {
  globalErrorHandler = handler;
}

function createClient(opts: HttpOptions = {}): AxiosInstance {
  const instance = axios.create({
    baseURL: opts.baseURL || BASE_URL,
    withCredentials: opts.withCredentials ?? true,
    timeout: 15000,
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  });

  // Request interceptor — attach access token if available (memory store placeholder)
  instance.interceptors.request.use((config) => {
    // TODO: integrate with a real auth store (Pinia) when implemented
    const token = (window as any).__accessToken as string | undefined;
    if (token) {
      config.headers = config.headers || {};
      (config.headers as any)["Authorization"] = `Bearer ${token}`;
    }
    return config;
  });

  // Response interceptor — refresh/retry/backoff
  instance.interceptors.response.use(
    (resp) => resp,
    async (error: AxiosError) => {
      const status = error.response?.status;
      const original = (error.config || {}) as AxiosRequestConfig & {
        _retry?: boolean;
        _retryCount?: number;
      };

      // 1) Handle 401 once with single-flight refresh and queued replay
      if (status === 401 && !original._retry) {
        original._retry = true;
        try {
          // queue until refresh resolves
          await triggerRefresh();
          logDebug("Replaying request after refresh", original.url);
          return instance(original);
        } catch (e) {
          // bubble up auth failure
          if (globalErrorHandler) globalErrorHandler(e);
          return Promise.reject(e);
        }
      }

      // 2) Bounded exponential backoff for transient errors (network/5xx except 401)
      const isNetworkError =
        !error.response && (error.code === "ECONNABORTED" || error.message?.includes("Network"));
      const isTransient = isNetworkError || (status !== undefined && status >= 500 && status < 600);
      if (isTransient) {
        const maxRetries = 2;
        original._retryCount = (original._retryCount || 0) + 1;
        if (original._retryCount <= maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, original._retryCount - 1), 4000);
          logDebug(
            `Transient error (status=${status || "net"}). Retry ${original._retryCount}/${maxRetries} after ${delay}ms`,
            original.url
          );
          await sleep(delay);
          return instance(original);
        }
      }

      // 3) Fallback: notify global handler once and reject
      if (globalErrorHandler) globalErrorHandler(error);
      return Promise.reject(error);
    }
  );

  return instance;
}

export const http = createClient();
export const httpNoCreds = createClient({ withCredentials: false });
