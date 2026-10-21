import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api is proxied to Django so the browser sees one origin in development
const proxy = { '/api': process.env.VITE_API || 'http://127.0.0.1:8000' }
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 5173, proxy },
})
