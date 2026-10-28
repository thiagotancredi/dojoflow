import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Versão do site: a data e hora do build. Vai para o código (para o app
// saber qual versão está rodando) e para /version.json (a mais nova no
// servidor). Quando as duas diferem, o app avisa "Nova versão disponível".
const appVersion = new Date().toISOString()

function versionFile(): Plugin {
  return {
    name: 'katsuflow-version-file',
    apply: 'build',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify({ version: appVersion }),
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), versionFile()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
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
