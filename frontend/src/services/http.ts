// Axios HTTP client with safe defaults and placeholders for JWT/session refresh.
// Phase 1 scaffolding — not yet wired globally to avoid breaking current pages.

import axios, { AxiosError, AxiosInstance } from 'axios'

export interface HttpOptions {
  baseURL?: string
  withCredentials?: boolean
}

const BASE_URL = import.meta.env.VITE_BACKEND_ORIGIN || 'https://127.0.0.1:8443'

function createClient(opts: HttpOptions = {}): AxiosInstance {
  const instance = axios.create({
    baseURL: opts.baseURL || BASE_URL,
    withCredentials: opts.withCredentials ?? true,
    timeout: 15000,
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
    },
  })

  // Request interceptor — attach access token if available (memory store placeholder)
  instance.interceptors.request.use((config) => {
    // TODO: integrate with a real auth store (Pinia) when implemented
    const token = (window as any).__accessToken as string | undefined
    if (token) {
      config.headers = config.headers || {}
      ;(config.headers as any)['Authorization'] = `Bearer ${token}`
    }
    return config
  })

  // Response interceptor — refresh/retry basic flow (placeholder, non-intrusive)
  instance.interceptors.response.use(
    (resp) => resp,
    async (error: AxiosError) => {
      const status = error.response?.status
      const original = error.config as any
      // Only attempt once
      if (status === 401 && !original?._retry) {
        original._retry = true
        try {
          // Placeholder: call refresh endpoint if available
          await axios.post(`${BASE_URL}/api/v1/auth/refresh/`, {}, { withCredentials: true })
          // Assume cookie-based refresh set a new access token via another endpoint or httpOnly cookie
          // If using memory token pattern, retrieve a fresh token here.
          return instance(original)
        } catch (e) {
          // fallthrough to reject
        }
      }
      return Promise.reject(error)
    }
  )

  return instance
}

export const http = createClient()
export const httpNoCreds = createClient({ withCredentials: false })