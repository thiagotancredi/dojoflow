import { TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

import type { Enrollment } from '@/features/students/api'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type EnrollmentCardProps = {
  enrollment: Enrollment
  // Ações do card (ex.: botão Editar), desenhadas ao lado do nome
  actions?: ReactNode
  // Conteúdo extra no fim do card (ex.: bloco da faixa)
  children?: ReactNode
}

// Chip pastel com borda colorida à esquerda (referência visual aprovada):
// azul = ativa, verde = isenta, amarelo = pendência de cadastro, cinza = inativa
export function EnrollmentCard({
  enrollment,
  actions,
  children,
}: EnrollmentCardProps) {
  const isPending =
    enrollment.status === 'active' &&
    !enrollment.is_exempt &&
    (enrollment.monthly_fee === null || enrollment.due_day === null)

  const tone =
    enrollment.status === 'inactive'
      ? 'border-status-inactive bg-status-inactive-soft text-status-inactive-foreground'
      : enrollment.is_exempt
        ? 'border-status-exempt bg-status-exempt-soft'
        : isPending
          ? 'border-status-pending bg-status-pending-soft'
          : 'border-status-active bg-status-active-soft'

  return (
    <div
      className={cn(
        'space-y-0.5 rounded-xl border-l-[3px] px-3 py-2.5 text-sm',
        tone,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="font-semibold">{enrollment.modality_name}</p>
        {actions}
      </div>
      <p>
        {enrollment.is_exempt
          ? 'Isenta'
          : isPending
            ? 'Sem mensalidade definida'
            : `${formatMoney(enrollment.monthly_fee)} · vence dia ${enrollment.due_day}`}
      </p>
      <p className="flex items-center gap-1 text-xs text-muted-foreground">
        {isPending && <TriangleAlert className="size-3.5" />}
        {enrollment.status === 'inactive'
          ? 'Inativa'
          : isPending
            ? 'Pendência de cadastro'
            : 'Ativa'}
      </p>
      {children}
    </div>
  )
}
