import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// În dezvoltare, cererile /api și /media merg la serverul Django (port 8030).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': 'http://127.0.0.1:8030',
      '/media': 'http://127.0.0.1:8030',
    },
  },
  build: {
    chunkSizeWarningLimit: 2000,
  },
})
