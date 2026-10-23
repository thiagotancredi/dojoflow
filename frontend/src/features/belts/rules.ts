import type { Belt } from '@/features/belts/api'

// Datas e textos de tempo das faixas. A aptidão ("apto") vem pronta da API.

function parseDate(isoDate: string) {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function toIsoDate(date: Date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export function todayIso() {
  return toIsoDate(new Date())
}

// Data + N meses, com o dia limitado ao fim do mês (31/01 + 1 = 28/02),
// a mesma regra do backend
function addMonthsClamped(start: Date, months: number) {
  const target = new Date(start.getFullYear(), start.getMonth() + months, 1)
  const lastDay = new Date(
    target.getFullYear(),
    target.getMonth() + 1,
    0,
  ).getDate()
  target.setDate(Math.min(start.getDate(), lastDay))
  return target
}

// Só a data (sem a hora), para a conta de dias não arredondar à tarde
function atMidnight(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

// Anos, meses e dias entre duas datas (meses pelo calendário)
function elapsed(isoDate: string, until: Date) {
  const start = parseDate(isoDate)
  const today = atMidnight(until)
  let months = Math.max(
    (today.getFullYear() - start.getFullYear()) * 12 +
      today.getMonth() -
      start.getMonth(),
    0,
  )
  while (months > 0 && addMonthsClamped(start, months) > today) months -= 1

  const base = addMonthsClamped(start, months)
  const days = Math.max(
    Math.round((today.getTime() - base.getTime()) / 86_400_000),
    0,
  )

  return { years: Math.floor(months / 12), months: months % 12, days }
}

// "há 1 ano e 3 meses", "há 3 meses e 12 dias", "há 5 dias"
export function timeSince(isoDate: string, today = new Date()) {
  const { years, months, days } = elapsed(isoDate, today)

  const parts: string[] = []
  if (years) parts.push(`${years} ${years > 1 ? 'anos' : 'ano'}`)
  if (months) parts.push(`${months} ${months > 1 ? 'meses' : 'mês'}`)
  if (!years && days) parts.push(`${days} ${days === 1 ? 'dia' : 'dias'}`)

  return parts.length ? `há ${parts.join(' e ')}` : 'desde hoje'
}

const UNIT_LABELS = {
  days: ['dia', 'dias'],
  months: ['mês', 'meses'],
  years: ['ano', 'anos'],
} as const

// "3 meses", "1 ano", "sem tempo mínimo"
export function minTimeLabel(
  amount: number | null,
  unit: keyof typeof UNIT_LABELS | null,
) {
  if (amount === null || unit === null) return 'sem tempo mínimo'
  const [one, many] = UNIT_LABELS[unit]
  return `${amount} ${amount === 1 ? one : many}`
}

// Tempo curto para as listas: "1a 3m", "3m 12d" (de isoDate até reference)
export function shortTimeSince(isoDate: string, reference: string) {
  const { years, months, days } = elapsed(isoDate, parseDate(reference))
  const parts = [
    years && `${years}a`,
    months && `${months}m`,
    !years && days && `${days}d`,
  ].filter(Boolean)

  return parts.length ? parts.join(' ') : '0d'
}

// Dia em que o aluno fica apto: data da graduação + tempo mínimo da faixa
// (mesma conta do backend, services/belt_rules.py). null = sem tempo mínimo
export function eligibleOn(
  graduatedOn: string,
  amount: number | null,
  unit: keyof typeof UNIT_LABELS | null,
): string | null {
  if (amount === null || unit === null) return null
  const start = parseDate(graduatedOn)
  if (unit === 'days') {
    return toIsoDate(
      new Date(start.getFullYear(), start.getMonth(), start.getDate() + amount),
    )
  }
  const months = unit === 'years' ? amount * 12 : amount
  return toIsoDate(addMonthsClamped(start, months))
}

// Quanto falta para ficar apto, contando a partir de "reference" (hoje ou
// a data do exame): "2m 3d", "18d". null = já está apto ou não há como saber
export function timeLeft(eligibleOnIso: string | null, reference: string) {
  if (!eligibleOnIso || eligibleOnIso <= reference) return null
  return shortTimeSince(reference, eligibleOnIso)
}

// Próxima faixa da sequência (sem faixa → a primeira; última → nenhuma)
export function nextBeltId(belts: Belt[], currentId: string | null) {
  if (!currentId) return belts[0]?.id ?? null
  const index = belts.findIndex((belt) => belt.id === currentId)
  return belts[index + 1]?.id ?? null
}
