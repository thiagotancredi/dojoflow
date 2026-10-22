import type { Charge, Payment } from '@/features/billing/api'
import { formatMonth } from '@/features/billing/labels'

// Um pagamento visto de dentro de uma mensalidade: quanto dele foi para ela
export type ChargePayment = { payment: Payment; amount: string }

export function chargeTitle(charge: Charge) {
  const what =
    charge.kind === 'enrollment_fee' ? 'Taxa de matrícula' : charge.modality_name
  return `${formatMonth(charge.reference_month)} · ${what}`
}

// charge_id → pagamentos que caíram nela (mais recente primeiro)
export function paymentsByCharge(payments: Payment[]) {
  const map = new Map<string, ChargePayment[]>()
  for (const payment of payments) {
    for (const allocation of payment.allocations) {
      const list = map.get(allocation.charge_id) ?? []
      list.push({ payment, amount: allocation.amount })
      map.set(allocation.charge_id, list)
    }
  }
  for (const list of map.values()) {
    list.sort((a, b) => b.payment.paid_on.localeCompare(a.payment.paid_on))
  }
  return map
}

