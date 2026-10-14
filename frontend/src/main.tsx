import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'

import { router } from '@/app/router'

import './index.css'

// Ponto de entrada: desenha o roteador dentro da <div id="root"> do index.html.
// A partir daqui, é o roteador que decide qual tela aparece para cada URL.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
