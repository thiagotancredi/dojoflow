// Dinheiro: o mestre digita no formato brasileiro ("1.500,50");
// a API recebe e devolve texto com ponto decimal ("1500.50").

// "150,00" → "150.00" · "1.500,50" → "1500.50" · "150" → "150.00"
// Texto inválido ou negativo → null
export function parseMoney(text: string): string | null {
  const trimmed = text.trim()
  // Sem vírgula e "150.5"/"150.00": o ponto é a casa decimal
  const dotIsDecimal = !trimmed.includes(',') && /^\d+\.\d{1,2}$/.test(trimmed)
  const normalized = dotIsDecimal
    ? trimmed
    : trimmed.replace(/\./g, '').replace(',', '.')

  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return null

  return Number(normalized).toFixed(2)
}

// "150.00" → "R$ 150,00" · null → "—"
export function formatMoney(value: string | null | undefined): string {
  if (value === null || value === undefined) return '—'

  return Number(value).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  })
}

// "150.00" → "150,00" (para preencher um campo de edição)
export function moneyToInput(value: string | null | undefined): string {
  if (value === null || value === undefined) return ''

  return Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
}
