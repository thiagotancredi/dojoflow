import type { ChargeStatus } from '@/features/billing/api'
import { cn } from '@/lib/utils'

// Cor de cada situação (tokens do tema; atraso usa a cor reservada de alerta)
const STYLES: Record<ChargeStatus, { label: string; dot: string; chip: string }> =
  {
    paid: {
      label: 'Paga',
      dot: 'bg-status-exempt',
      chip: 'bg-status-exempt-soft',
    },
    // Pago em parte e ainda no prazo: o "Falta" do extrato mostra o resto
    partial: {
      label: 'A vencer',
      dot: 'bg-status-active',
      chip: 'bg-status-active-soft',
    },
    overdue: {
      label: 'Atrasada',
      dot: 'bg-status-critical',
      chip: 'bg-status-critical-soft text-status-critical',
    },
    upcoming: {
      label: 'A vencer',
      dot: 'bg-status-active',
      chip: 'bg-status-active-soft',
    },
    waived: {
      label: 'Isenta',
      dot: 'bg-status-inactive',
      chip: 'bg-status-inactive-soft text-status-inactive-foreground',
    },
  }

// Só quatro situações: Paga, A vencer, Atrasada, Isenta
export function ChargeStatusChip({ status }: { status: ChargeStatus }) {
  const style = STYLES[status]

  return (
    <span
      className={cn(
        'inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs whitespace-nowrap',
        style.chip,
      )}
    >
      <span className={cn('size-2 rounded-full', style.dot)} />
      {style.label}
    </span>
  )
}
