import { TriangleAlert } from 'lucide-react'

import type { Enrollment } from '@/features/students/types'
import { cn } from '@/lib/utils'

type EnrollmentCardProps = {
  enrollment: Enrollment
}

// Chip pastel com borda colorida à esquerda (referência visual aprovada):
// azul = ativa, verde = isenta, amarelo = pendência de cadastro, cinza = inativa
export function EnrollmentCard({ enrollment }: EnrollmentCardProps) {
  const isPending =
    enrollment.status === 'active' &&
    !enrollment.isExempt &&
    (enrollment.monthlyFee === null || enrollment.dueDay === null)

  const tone =
    enrollment.status === 'inactive'
      ? 'border-status-inactive bg-status-inactive-soft text-status-inactive-foreground'
      : enrollment.isExempt
        ? 'border-status-exempt bg-status-exempt-soft'
        : isPending
          ? 'border-status-pending bg-status-pending-soft'
          : 'border-status-active bg-status-active-soft'

  return (
    <div className={cn('rounded-xl border-l-[3px] px-3 py-2.5 text-sm', tone)}>
      <p className="font-semibold">{enrollment.modalityName}</p>
      <p>
        {enrollment.isExempt
          ? 'Isenta'
          : isPending
            ? 'Sem mensalidade definida'
            : `R$ ${enrollment.monthlyFee} · vence dia ${enrollment.dueDay}`}
      </p>
      <p className="flex items-center gap-1 text-xs text-muted-foreground">
        {isPending && <TriangleAlert className="size-3.5" />}
        {enrollment.status === 'inactive'
          ? 'Inativa'
          : isPending
            ? 'Pendência de cadastro'
            : 'Ativa'}
      </p>
    </div>
  )
}
