import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'

import { router } from '@/app/router'
import { applyInitialMode } from '@/app/theme'
import { Toaster } from '@/components/ui/sonner'
import { AuthProvider } from '@/features/auth/AuthProvider'

import './index.css'

// Claro ou escuro antes de desenhar, para a tela não piscar
applyInitialMode()

// Ponto de entrada: desenha o roteador dentro da <div id="root"> do index.html.
// A partir daqui, é o roteador que decide qual tela aparece para cada URL.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
      {/* Avisos rápidos (toasts) de sucesso e erro, em qualquer tela */}
      <Toaster position="bottom-right" />
    </AuthProvider>
  </StrictMode>,
)
