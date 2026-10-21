import { Outlet } from 'react-router'

import { Logo } from '@/app/components/Logo'
import { NavIconLink } from '@/app/components/NavIconLink'
import { ThemeToggle } from '@/app/components/ThemeToggle'
import { mainNavItems, settingsNavItem } from '@/app/navigation'

// Moldura de toda a área logada: sidebar (desktop) ou barra inferior
// (celular) + o conteúdo da rota filha no <Outlet />.
export function AppLayout() {
  const allItems = [...mainNavItems, settingsNavItem]

  return (
    <div className="flex min-h-dvh gap-4 p-3 pb-24 md:p-5 md:pb-5">
      {/* Sidebar: só aparece de "md" (768px) para cima */}
      <aside className="sticky top-5 hidden h-[calc(100dvh-2.5rem)] w-16 shrink-0 flex-col items-center gap-3 rounded-3xl bg-sidebar px-2 py-4 md:flex">
        <div className="mb-3">
          <Logo />
        </div>
        {mainNavItems.map((item) => (
          <NavIconLink key={item.to} item={item} />
        ))}
        <div className="flex-1" />
        <ThemeToggle />
        <NavIconLink item={settingsNavItem} />
      </aside>

      <main className="min-w-0 flex-1">
        <Outlet />
      </main>

      {/* Barra inferior: só no celular (abaixo de "md") */}
      <nav className="fixed inset-x-3 bottom-3 flex justify-around rounded-3xl bg-card p-2 shadow-lg shadow-primary/10 md:hidden">
        {allItems.map((item) => (
          <NavIconLink key={item.to} item={item} />
        ))}
      </nav>
    </div>
  )
}
