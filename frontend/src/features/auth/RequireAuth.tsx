import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { useAuth } from '@/features/auth/useAuth'

// Guarda de rota: só desenha a área logada se houver sessão.
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()

  // Ainda verificando o cookie: não decide nada antes da resposta
  if (status === 'loading') {
    return (
      <div className="grid min-h-dvh place-items-center text-sm text-muted-foreground">
        Carregando…
      </div>
    )
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" replace />
  }

  return children
}
