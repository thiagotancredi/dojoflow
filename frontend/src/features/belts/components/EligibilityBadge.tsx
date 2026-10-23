import type { ReactNode } from 'react'
import { Clock, Star } from 'lucide-react'

import type { Eligibility } from '@/features/belts/api'
import { cn } from '@/lib/utils'

// Situação do aluno para graduar, com os MESMOS nomes em todo o site
// (ficha do aluno e listas de graduação):
//   Apto · Não apto (faltam X) · Liberado pelo mestre · Sem faixa ·
//   Sem tempo mínimo
// É só um aviso: não impede nada.
export function EligibilityBadge({
  value,
  left,
  master = false,
}: {
  value: Eligibility
  // Quanto falta ("2m 3d"), quando não está apto
  left?: string | null
  // Está numa lista de graduação mesmo sem estar apto: decisão do mestre
  master?: boolean
}) {
  if (value === 'eligible') {
    return (
      <Chip className="bg-status-exempt-soft text-status-exempt">
        <Dot className="bg-status-exempt" />
        Apto
      </Chip>
    )
  }

  if (value === 'not_yet' && master) {
    return (
      <span className="inline-flex flex-col items-start gap-0.5">
        <Chip className="bg-status-pending-soft text-foreground">
          <Star className="size-3 fill-status-pending text-status-pending" />
          Liberado pelo mestre
        </Chip>
        {left && (
          <span className="pl-2 text-[11px] text-muted-foreground">
            Não apto · faltam {left}
          </span>
        )}
      </span>
    )
  }

  if (value === 'not_yet') {
    return (
      <Chip className="bg-status-pending-soft text-foreground">
        <Clock className="size-3 text-status-pending" />
        Não apto{left && ` · faltam ${left}`}
      </Chip>
    )
  }

  if (value === 'no_belt') {
    return (
      <Chip className="bg-muted text-muted-foreground">
        <Dot className="bg-status-inactive" />
        Sem faixa
      </Chip>
    )
  }

  return (
    <Chip className="bg-muted text-muted-foreground">
      <Dot className="bg-status-exempt" />
      Sem tempo mínimo
    </Chip>
  )
}

function Chip({
  className,
  children,
}: {
  className: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs whitespace-nowrap',
        className,
      )}
    >
      {children}
    </span>
  )
}

function Dot({ className }: { className: string }) {
  return <span className={cn('size-2 shrink-0 rounded-full', className)} />
}

// Texto do "i" ao lado de "Situação": o que significa cada uma
export function EligibilityHelp() {
  return (
    <div className="space-y-2">
      <p className="font-semibold">O que significa cada situação</p>
      <HelpLine badge={<EligibilityBadge value="eligible" />}>
        já cumpriu o tempo mínimo na faixa até a data do exame.
      </HelpLine>
      <HelpLine badge={<EligibilityBadge value="not_yet" />}>
        ainda não cumpriu; mostra quanto falta, contando até o exame.
      </HelpLine>
      <HelpLine
        badge={
          <Chip className="bg-status-pending-soft text-foreground">
            <Star className="size-3 fill-status-pending text-status-pending" />
            Liberado pelo mestre
          </Chip>
        }
      >
        não está apto, mas você incluiu na lista mesmo assim.
      </HelpLine>
      <HelpLine badge={<EligibilityBadge value="no_belt" />}>
        o aluno ainda não tem faixa registrada.
      </HelpLine>
      <HelpLine badge={<EligibilityBadge value="no_requirement" />}>
        a faixa atual não exige tempo mínimo.
      </HelpLine>
    </div>
  )
}

function HelpLine({
  badge,
  children,
}: {
  badge: ReactNode
  children: ReactNode
}) {
  return (
    <p className="text-xs leading-relaxed text-muted-foreground">
      <span className="mr-1">{badge}</span>
      {children}
    </p>
  )
}
