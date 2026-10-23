import { TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

import type { Enrollment } from '@/features/students/api'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type EnrollmentFeeCardProps = {
  enrollment: Enrollment
  // Ações do quadro (ex.: botão Editar), ao lado do título
  actions?: ReactNode
}

// Quadro "Mensalidade" da matrícula. A borda da esquerda segue o status
// (referência visual aprovada): azul = ativa, verde = isenta, amarelo =
// pendência de cadastro, cinza = inativa
export function EnrollmentFeeCard({ enrollment, actions }: EnrollmentFeeCardProps) {
  const isPending = isPendingFee(enrollment)

  const tone =
    enrollment.status === 'inactive'
      ? 'border-l-status-inactive'
      : enrollment.is_exempt
        ? 'border-l-status-exempt'
        : isPending
          ? 'border-l-status-pending'
          : 'border-l-status-active'

  return (
    <div
      className={cn(
        'flex flex-col gap-2 rounded-2xl border border-l-4 bg-popover p-4',
        tone,
      )}
    >
      <div className="flex min-h-7 items-center justify-between gap-2">
        <p className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
          Mensalidade
        </p>
        {actions}
      </div>

      {enrollment.is_exempt ? (
        <>
          <p className="text-2xl font-semibold">Isenta</p>
          <p className="text-xs text-muted-foreground">Sem cobrança</p>
        </>
      ) : (
        <>
          <p
            className={cn(
              'font-semibold',
              enrollment.monthly_fee !== null
                ? 'text-2xl'
                : 'text-base text-muted-foreground',
            )}
          >
            {enrollment.monthly_fee !== null
              ? formatMoney(enrollment.monthly_fee)
              : 'Sem valor definido'}
          </p>
          <p className="text-xs text-muted-foreground">
            {enrollment.due_day !== null
              ? `vence todo dia ${enrollment.due_day}`
              : 'Sem dia de vencimento'}
          </p>
        </>
      )}
    </div>
  )
}

// Ativa e não isenta, mas sem valor ou sem dia de vencimento
function isPendingFee(enrollment: Enrollment) {
  return (
    enrollment.status === 'active' &&
    !enrollment.is_exempt &&
    (enrollment.monthly_fee === null || enrollment.due_day === null)
  )
}

// Situação da matrícula (vai ao lado do nome da modalidade)
export function EnrollmentStatusChip({ enrollment }: { enrollment: Enrollment }) {
  const isPending = isPendingFee(enrollment)
  const [label, dot] =
    enrollment.status === 'inactive'
      ? ['Inativa', 'bg-status-inactive']
      : isPending
        ? ['Pendência de cadastro', 'bg-status-pending']
        : ['Ativa', enrollment.is_exempt ? 'bg-status-exempt' : 'bg-status-active']

  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-popover px-2.5 py-0.5 text-xs font-normal">
      {isPending ? (
        <TriangleAlert className="size-3.5 text-status-pending" />
      ) : (
        <span className={cn('size-2 rounded-full', dot)} />
      )}
      {label}
    </span>
  )
}
