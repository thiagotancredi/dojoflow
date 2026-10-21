import { ShieldOff } from 'lucide-react'
import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { getAdminMe } from '@/features/admin/api'
import { useAuth } from '@/features/auth/useAuth'
import { useResource } from '@/lib/hooks/useResource'

function Centered({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh place-items-center p-4 text-sm text-muted-foreground">
      {children}
    </div>
  )
}

// Guarda do painel: precisa de sessão E ser o administrador (GET /admin/me)
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { status, master, signOut } = useAuth()
  const check = useResource(
    status === 'authenticated' && master ? `admin-me:${master.id}` : null,
    (signal) => getAdminMe(signal),
  )

  if (status === 'loading') return <Centered>Carregando…</Centered>
  if (status === 'anonymous') return <Navigate to="/login" replace />
  if (check.isLoading || (!check.data && !check.error)) {
    return <Centered>Carregando…</Centered>
  }

  if (check.error) {
    return (
      <Centered>
        <div className="flex max-w-sm flex-col items-center gap-3 rounded-3xl bg-card p-8 text-center shadow-sm">
          <ShieldOff className="size-8 text-muted-foreground" />
          <p className="text-base font-semibold text-foreground">Sem acesso</p>
          <p>Esta conta não tem acesso a esta área.</p>
          <Button
            variant="outline"
            className="rounded-full"
            onClick={() => void signOut()}
          >
            Sair
          </Button>
        </div>
      </Centered>
    )
  }

  return children
}
