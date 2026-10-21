// Regras de tempo das faixas (as mesmas do backend: meses somados pelo
// calendário; dia inexistente cai no último dia do mês).

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

// "2026-01-31" + 1 mês → "2026-02-28"
export function addMonths(isoDate: string, months: number) {
  const start = parseDate(isoDate)
  const target = new Date(start.getFullYear(), start.getMonth() + months, 1)
  const lastDay = new Date(
    target.getFullYear(),
    target.getMonth() + 1,
    0,
  ).getDate()
  target.setDate(Math.min(start.getDate(), lastDay))
  return toIsoDate(target)
}

// "há 1 ano e 3 meses", "há 3 meses e 12 dias", "há 5 dias"
export function timeSince(isoDate: string, today = new Date()) {
  const start = parseDate(isoDate)
  let months =
    (today.getFullYear() - start.getFullYear()) * 12 +
    today.getMonth() -
    start.getMonth()
  if (today.getDate() < start.getDate()) months -= 1
  months = Math.max(months, 0)

  const base = new Date(
    start.getFullYear(),
    start.getMonth() + months,
    start.getDate(),
  )
  const days = Math.max(
    Math.round((today.getTime() - base.getTime()) / 86_400_000),
    0,
  )

  const parts: string[] = []
  const years = Math.floor(months / 12)
  const restMonths = months % 12
  if (years) parts.push(`${years} ${years > 1 ? 'anos' : 'ano'}`)
  if (restMonths) parts.push(`${restMonths} ${restMonths > 1 ? 'meses' : 'mês'}`)
  if (!years && (days || parts.length === 0)) {
    parts.push(`${days} ${days === 1 ? 'dia' : 'dias'}`)
  }

  return `há ${parts.join(' e ')}`
}

export type Eligibility =
  | { kind: 'eligible'; since: string }
  | { kind: 'not_yet'; on: string }
  | { kind: 'no_requirement' }

// Apto quando faixa + tempo mínimo ≤ a data de referência (hoje)
export function eligibility(
  graduatedOn: string,
  minMonths: number | null,
  reference = todayIso(),
): Eligibility {
  if (minMonths === null) return { kind: 'no_requirement' }

  const on = addMonths(graduatedOn, minMonths)
  return on <= reference ? { kind: 'eligible', since: on } : { kind: 'not_yet', on }
}
