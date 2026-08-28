import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Build lands in dist/ beside this file - the same folder
// settings_for_main_menu.py's SVELTE_DIST points at. The dev server
// proxies API and shared-look requests to the real menu server on its
// own port, so `npm run dev` works while the Python screen runs.
export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/shared': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
