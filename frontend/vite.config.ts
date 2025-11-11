import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// https://vitejs.dev/config/
export default defineConfig(async () => {
  // Allow dynamic backend origin selection in dev via environment variables
  // Prefer explicit VITE_BACKEND_ORIGIN, fall back to https://127.0.0.1:<VITE_BACKEND_PORT or 8443
  const port = process.env.VITE_BACKEND_PORT || '8443';
  const backendOrigin = process.env.VITE_BACKEND_ORIGIN || `https://127.0.0.1:${port}`;
  const analyze = String(process.env.ANALYZE || '') === '1';

  const plugins: any[] = [vue()];
  if (analyze) {
    try {
      const { visualizer } = await import('rollup-plugin-visualizer');
      plugins.push(
        visualizer({
          open: false,
          filename: 'dist/stats.html',
          gzipSize: true,
          brotliSize: true,
          template: 'treemap',
        }) as any
      );
    } catch (e) {
      // If the plugin is not installed, continue without failing dev server
      console.warn('[vite] rollup-plugin-visualizer not available, skipping analysis');
    }
  }

  return {
    plugins,
    server: {
      port: 5173,
      strictPort: false,
      proxy: {
        '/api': {
          // Backend dev server runs via HTTPS (Uvicorn TLS) by default from serve_https.ps1
          target: backendOrigin,
          changeOrigin: true,
          secure: false, // accept self-signed cert in dev
        },
        '/assets': {
          // Serve Maronia identity assets (fonts/images) directly from Django during dev
          target: backendOrigin,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  };
});
