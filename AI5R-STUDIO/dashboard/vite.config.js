import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // LOCAL DEV ONLY -- proxies same-origin /api requests (browser sees
  // only http://localhost:5173, so no cross-origin request is ever made,
  // no CORS preflight applies) to the local Docker stack's nginx gateway
  // at :8080. Server-to-server (Vite -> nginx) hop is not subject to
  // browser CORS. Production is unaffected: the built dashboard image
  // never runs `vite dev`, it's a static build served by its own nginx
  // with VITE_API_URL baked in at build time via a separate --build-arg
  // (dashboard.Dockerfile), not this dev-server-only config.
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
