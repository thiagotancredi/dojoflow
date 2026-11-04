import type { GraduationEntry } from '@/features/belts/api'

// Regras da cobrança da graduação na lista (sem componentes)

// "2026-12-05" → "05/12"
export function dayMonth(isoDate: string) {
  const [, month, day] = isoDate.split('-')
  return `${day}/${month}`
}

// Valor ainda em aberto (0 sem cobrança ou já paga)
export function openAmount(entry: GraduationEntry) {
  const charge = entry.charge
  if (!charge || charge.status === 'paid' || charge.status === 'waived') return 0
  return Number(charge.open_amount)
}
