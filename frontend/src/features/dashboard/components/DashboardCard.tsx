import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type DashboardCardProps = {
  // Texto ou texto + número (ex.: "Inadimplentes · 5")
  title: ReactNode
  subtitle?: string
  action?: ReactNode
  className?: string
  children: ReactNode
}

// Painel branco padrão do dashboard. "children" é o conteúdo que o pai
// coloca entre <DashboardCard> e </DashboardCard>.
export function DashboardCard({
  title,
  subtitle,
  action,
  className,
  children,
}: DashboardCardProps) {
  return (
    <section className={cn('space-y-4 rounded-3xl bg-card p-5', className)}>
      {/* flex-wrap + shrink-0: o título nunca quebra; se as ações (ex.:
          filtros) não couberem ao lado, descem para a linha de baixo */}
      <header className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
        <div className="shrink-0">
          <h2 className="font-semibold">{title}</h2>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
        {action}
      </header>
      {children}
    </section>
  )
}
