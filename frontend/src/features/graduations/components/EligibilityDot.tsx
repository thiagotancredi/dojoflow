import type { Eligibility } from '@/features/belts/api'
import { cn } from '@/lib/utils'

// Situação discreta nas listas (spec): ponto verde "Apto", âmbar
// "Ainda não", cinza "Sem faixa". É só um aviso: não impede nada.
const LOOK: Record<Eligibility, { dot: string; text: string; label: string }> = {
  eligible: { dot: 'bg-status-exempt', text: 'text-status-exempt', label: 'Apto' },
  not_yet: {
    dot: 'bg-status-pending',
    text: 'text-muted-foreground',
    label: 'Ainda não',
  },
  no_belt: {
    dot: 'bg-status-inactive',
    text: 'text-muted-foreground',
    label: 'Sem faixa',
  },
  no_requirement: {
    dot: 'bg-status-exempt',
    text: 'text-muted-foreground',
    label: 'Sem tempo mínimo',
  },
}

export function EligibilityDot({ value }: { value: Eligibility }) {
  const look = LOOK[value]

  return (
    <span className={cn('flex items-center gap-1.5 text-xs', look.text)}>
      <span className={cn('size-2 shrink-0 rounded-full', look.dot)} />
      {look.label}
    </span>
  )
}
