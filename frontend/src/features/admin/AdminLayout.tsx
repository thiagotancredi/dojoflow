import { LogOut } from 'lucide-react'
import { Outlet } from 'react-router'

import { Logo } from '@/app/components/Logo'
import { ThemeToggle } from '@/app/components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'

// Moldura do painel do administrador: barra no topo + conteúdo
export function AdminLayout() {
  const { signOut } = useAuth()

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-sidebar-border bg-sidebar px-4 py-3 backdrop-blur md:px-6">
        <div className="flex items-center gap-3">
          <Logo />
          <span className="text-lg font-semibold">Katsuflow</span>
          <span className="rounded-full border border-chip-active-border bg-chip-active px-2 py-0.5 text-[11px] font-semibold tracking-wide text-chip-active-foreground uppercase">
            Admin
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            variant="ghost"
            className="rounded-full"
            onClick={() => void signOut()}
          >
            <LogOut className="size-4" />
            Sair
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  )
}
