import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// vite.config.js — ESM format required by Vite 6

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
