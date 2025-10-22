// Minimal Vite config for NPX fallback when local 'vite' package isn't installed.
// Do not import from 'vite' here to avoid module resolution of local node_modules.

const backend = process.env.VITE_BACKEND_ORIGIN || 'https://127.0.0.1:8443'

/** @type {import('vite').UserConfig} */
const config = {
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: false,
    https: false,
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
        secure: false,
      },
      '/static': {
        target: backend,
        changeOrigin: true,
        secure: false,
      },
      '/media': {
        target: backend,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  preview: {
    port: 5174,
  },
}

export default config