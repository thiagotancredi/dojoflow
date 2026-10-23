// Conversões entre o texto que a API e os formulários usam ("2026-10-23",
// "2026-10") e o Date do calendário. Monta a data no horário local, só com
// ano/mês/dia: new Date("2026-10-23") seria lido como UTC e, no Brasil,
// viraria dia 22 às 21h.

const pad = (n: number) => String(n).padStart(2, '0')

// "2026-10-23" → Date local (ou undefined se vazio/inválido)
export function parseIsoDate(text: string | null | undefined): Date | undefined {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text ?? '')
  if (!match) return undefined
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

// Date → "2026-10-23"
export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

// "2026-10" → Date do dia 1 (ou undefined)
export function parseIsoMonth(text: string | null | undefined): Date | undefined {
  const match = /^(\d{4})-(\d{2})$/.exec(text ?? '')
  if (!match) return undefined
  return new Date(Number(match[1]), Number(match[2]) - 1, 1)
}

// Date → "2026-10"
export function toIsoMonth(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`
}

export const MONTHS_SHORT = [
  'jan', 'fev', 'mar', 'abr', 'mai', 'jun',
  'jul', 'ago', 'set', 'out', 'nov', 'dez',
] as const

export const MONTHS_LONG = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
] as const

// Date → "outubro 2026"
export function formatMonthLong(date: Date): string {
  return `${MONTHS_LONG[date.getMonth()]} ${date.getFullYear()}`
}
