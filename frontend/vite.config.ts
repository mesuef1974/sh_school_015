import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        // Backend dev server runs via HTTPS (Uvicorn TLS) by default from serve_https.ps1
        target: 'https://127.0.0.1:8443',
        changeOrigin: true,
        secure: false // accept self-signed cert in dev
      },
      '/assets': {
        // Serve Maronia identity assets (fonts/images) directly from Django during dev
        target: 'https://127.0.0.1:8443',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
});