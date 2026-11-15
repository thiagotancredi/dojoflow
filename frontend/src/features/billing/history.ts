import type { Charge, Payment } from '@/features/billing/api'
import { PAYMENT_METHOD_LABELS, formatDayMonth } from '@/features/billing/labels'
import type { ChargePayment } from '@/features/billing/statement'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'

// "Taekwondo · vence 20/11", "Pago 08/10 · Pix" ou "Pagou R$ 50,00 · falta R$ 60,00"
export function chargeDetail(charge: Charge, payments: ChargePayment[]) {
  const last = payments[0]?.payment
  const missing = Number(charge.amount) - Number(charge.paid)
  const graduation =
    charge.kind === 'graduation' && charge.graduation
      ? `Exame ${formatDayMonth(charge.graduation.exam_date)} · `
      : ''

  if (charge.status === 'waived') return `${graduation}${charge.modality_name} · isenta`
  if (charge.status === 'paid') {
    const how = last?.method ? ` · ${PAYMENT_METHOD_LABELS[last.method]}` : ''
    return `${graduation}Pago ${last ? formatDayMonth(last.paid_on) : ''}${how}`
  }
  if (Number(charge.paid) > 0) {
    return `${graduation}Pagou ${formatMoney(charge.paid)} · falta ${formatMoney(missing.toFixed(2))}`
  }
  const due = charge.kind === 'graduation' ? 'pagar até' : 'vence'
  return `${graduation || `${charge.modality_name} · `}${due} ${formatDayMonth(charge.due_date)}`
}

export type ChargeHandlers = {
  busy: boolean
  onWaive: (charge: Charge, waived: boolean) => void
  onEdit: (charge: Charge) => void
  onRemovePayment: (payment: Payment) => void
}

export type ChargeAction = {
  key: string
  label: string
  destructive?: boolean
  run: () => void
}

// O que dá para fazer com uma cobrança: editar, isentar (ou desfazer) e
// excluir os pagamentos dela. Com pagamento, a cobrança não muda (exclua o
// pagamento antes). Usado no "⋯" (computador) e no painel (celular).
export function chargeActions(
  charge: Charge,
  payments: ChargePayment[],
  handlers: ChargeHandlers,
): ChargeAction[] {
  const canChange = Number(charge.paid) === 0
  const actions: ChargeAction[] = []
  const isMonthly = charge.kind !== 'graduation'

  if (canChange && charge.status === 'waived') {
    actions.push({
      key: 'unwaive',
      label: 'Desfazer isenção',
      run: () => handlers.onWaive(charge, false),
    })
  } else if (canChange) {
    actions.push({
      key: 'edit',
      label: 'Editar valor ou vencimento',
      run: () => handlers.onEdit(charge),
    })
    if (isMonthly) {
      actions.push({
        key: 'waive',
        label: 'Isentar este mês',
        run: () => handlers.onWaive(charge, true),
      })
    }
  }
  for (const { payment } of payments) {
    actions.push({
      key: payment.id,
      label: `Excluir pagamento de ${formatDate(payment.paid_on)}`,
      destructive: true,
      run: () => handlers.onRemovePayment(payment),
    })
  }
  return actions
}
