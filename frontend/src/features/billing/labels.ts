import type { Schemas } from '@/lib/api/client'

// Textos e formatos das telas de mensalidade

export type PaymentMethod = Schemas['PaymentMethod']

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  pix: 'Pix',
  cash: 'Dinheiro',
  credit_card: 'Cartão de crédito',
  debit_card: 'Cartão de débito',
  bank_transfer: 'Transferência',
  other: 'Outro',
}

const SHORT_MONTHS = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
]

// "2027-03-01" → "Mar/2027"
export function formatMonth(isoDate: string) {
  const [year, month] = isoDate.split('-')
  return `${SHORT_MONTHS[Number(month) - 1]}/${year}`
}

// "2027-03-15" → "15/03"
export function formatDayMonth(isoDate: string) {
  const [, month, day] = isoDate.split('-')
  return `${day}/${month}`
}

// "janeiro" → "Janeiro"
export function capitalize(text: string) {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// Mês atual no formato do campo <input type="month">: "2026-10"
export function currentMonth() {
  const today = new Date()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  return `${today.getFullYear()}-${month}`
}

// Dias de hoje até a data ("2026-11-20"): 0 = hoje, negativo = passou
export function daysFromToday(isoDate: string) {
  const [year, month, day] = isoDate.split('-').map(Number)
  const today = new Date()
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((Date.UTC(year, month - 1, day) - start) / 86_400_000)
}

// "em 5 dias", "amanhã", "hoje"
export function dueIn(isoDate: string) {
  const days = daysFromToday(isoDate)
  if (days <= 0) return 'hoje'
  if (days === 1) return 'amanhã'
  return `em ${days} dias`
}

// "R$ 1.450" (sem centavos), para os blocos do Financeiro
export function formatMoneyShort(value: string | number) {
  return Number(value).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}
