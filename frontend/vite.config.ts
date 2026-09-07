import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Split shared vendor libraries into stable, cacheable chunks so the main
    // entry stays small and unchanged vendor code isn't re-downloaded.
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'tanstack-vendor': [
            '@tanstack/react-query',
            '@tanstack/react-table',
            '@tanstack/react-virtual',
          ],
          'chart-vendor': ['recharts'],
          'ui-vendor': ['lucide-react', 'clsx', 'axios'],
        },
      },
    },
    // Vendor chunks legitimately exceed 500 kB (Recharts); raise the warning
    // threshold so the build doesn't warn on intentional vendor splits.
    chunkSizeWarningLimit: 600,
  },
  server: {
    proxy: {
      // Proxy API calls to the FastAPI backend during development.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})