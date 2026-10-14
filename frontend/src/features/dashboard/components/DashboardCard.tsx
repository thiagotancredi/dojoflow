import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type DashboardCardProps = {
  title: string
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
      <header className="flex items-start justify-between gap-3">
        <div>
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
