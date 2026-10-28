import { Outlet } from 'react-router'

import { Logo } from '@/app/components/Logo'
import { NavIconLink } from '@/app/components/NavIconLink'
import { SupportBanner } from '@/app/components/SupportBanner'
import { mainNavItems, settingsNavItem } from '@/app/navigation'

// Moldura de toda a área logada: sidebar (desktop) ou barra inferior
// (celular) + o conteúdo da rota filha no <Outlet />.
export function AppLayout() {
  const allItems = [...mainNavItems, settingsNavItem]

  return (
    <>
      {/* Só aparece no modo suporte (administrador vendo outra academia) */}
      <SupportBanner />
      {/* App instalado no celular: a página vai até atrás da hora/bateria
          (viewport-fit=cover); o safe-area empurra o conteúdo para baixo dela */}
      <div className="flex min-h-dvh gap-4 p-3 pt-[max(0.75rem,calc(env(safe-area-inset-top)+0.75rem))] pb-[calc(6rem+env(safe-area-inset-bottom))] md:p-5 md:pb-5">
        {/* Sidebar: só aparece de "md" (768px) para cima */}
        <aside className="sticky top-5 hidden h-[calc(100dvh-2.5rem)] w-16 shrink-0 flex-col items-center gap-3 rounded-3xl bg-sidebar px-2 py-4 md:flex">
          <div className="mb-3">
            <Logo />
          </div>
          {mainNavItems.map((item) => (
            <NavIconLink key={item.to} item={item} />
          ))}
          <div className="flex-1" />
          {/* Botão do tema escuro fora por enquanto (ver app/theme.ts) */}
          <NavIconLink item={settingsNavItem} />
        </aside>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>

        {/* Barra inferior: só no celular (abaixo de "md"). Mesma cor da
            sidebar do computador (bg-sidebar), para os dois combinarem */}
        <nav className="fixed inset-x-3 bottom-[max(0.75rem,calc(env(safe-area-inset-bottom)-0.5rem))] z-40 flex justify-around rounded-3xl bg-sidebar p-2 shadow-lg shadow-black/20 md:hidden">
          {allItems.map((item) => (
            <NavIconLink key={item.to} item={item} />
          ))}
        </nav>
      </div>
    </>
  )
}
