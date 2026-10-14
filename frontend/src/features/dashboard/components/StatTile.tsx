import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type StatTileProps = {
  label: string
  value: number
  icon: ReactNode
  // Cor do ícone: neutra (cor principal) ou de alerta (atraso/vencimento)
  tone?: 'default' | 'critical' | 'warning'
}

const toneClasses = {
  default: 'bg-accent text-primary',
  critical: 'bg-status-critical-soft text-status-critical',
  warning: 'bg-status-warning-soft text-status-warning',
}

export function StatTile({ label, value, icon, tone = 'default' }: StatTileProps) {
  return (
    <div className="flex items-center gap-3 rounded-3xl bg-card p-4">
      <div
        className={cn(
          'grid size-11 shrink-0 place-items-center rounded-2xl',
          toneClasses[tone],
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-2xl leading-none font-semibold">{value}</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}
