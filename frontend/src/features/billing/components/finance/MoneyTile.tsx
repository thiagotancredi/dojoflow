import type { ReactNode } from 'react'

import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

const toneClasses = {
  default: 'bg-accent text-primary',
  critical: 'bg-status-critical-soft text-status-critical',
  warning: 'bg-status-warning-soft text-status-warning',
}

// Número grande do topo do Financeiro: valor, legenda e ícone colorido.
// "value" é dinheiro ("150.00"); "text" é qualquer outra coisa ("8 alunos").
export function MoneyTile({
  label,
  value,
  text,
  detail,
  icon,
  tone = 'default',
  valueClassName,
}: {
  label: string
  value?: string
  text?: string
  detail?: string
  icon: ReactNode
  tone?: keyof typeof toneClasses
  valueClassName?: string
}) {
  const shown = text ?? (value === undefined ? '—' : formatMoney(value))

  return (
    <div className="flex items-center gap-3 rounded-3xl bg-card p-4">
      <div
        className={cn(
          'hidden size-11 shrink-0 place-items-center rounded-2xl sm:grid',
          toneClasses[tone],
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className={cn('text-xl leading-none font-semibold', valueClassName)}>
          {shown}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {label}
          {detail && ` · ${detail}`}
        </p>
      </div>
    </div>
  )
}
