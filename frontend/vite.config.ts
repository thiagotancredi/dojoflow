import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // "@/..." aponta para "src/..." (ex.: import { Button } from '@/components/ui/button')
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    // Libera o acesso pelo túnel da Cloudflare (para ver no celular) e o
    // painel do administrador em http://admin.localhost:5173
    allowedHosts: ['.trycloudflare.com', 'admin.localhost'],
    // Em dev, o navegador chama /api no próprio Vite (porta 5173) e o Vite
    // repassa para o FastAPI. Assim tudo é "mesma origem" e o cookie de
    // refresh funciona sem CORS.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
