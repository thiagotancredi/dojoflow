import type { Belt, GraduationEntry } from '@/features/belts/api'

// Regras do resultado do exame na lista (sem componentes)

// Faixas puladas: as que ficam ENTRE a de agora e a alvo (sem as pontas).
// Sem faixa de agora ou alvo que não está acima: nenhuma.
export function beltsBetween(belts: Belt[], from: Belt | null, to: Belt): Belt[] {
  if (!from || to.position <= from.position) return []
  return belts
    .filter((belt) => belt.position > from.position && belt.position < to.position)
    .sort((left, right) => left.position - right.position)
}

// Por que o "Aprovar" está apagado: graduação em aberto (nem paga nem isenta).
// Sem cobrança (lista sem data limite ou faixa sem preço): liberado.
export function approveBlock(entry: GraduationEntry): 'unpaid' | null {
  const charge = entry.charge
  if (!charge || charge.status === 'paid' || charge.status === 'waived') return null
  return 'unpaid'
}

// Isentar só vale para cobrança em aberto sem nenhum pagamento
export function canWaive(entry: GraduationEntry) {
  const charge = entry.charge
  return (
    Boolean(charge) &&
    (charge!.status === 'upcoming' || charge!.status === 'overdue') &&
    Number(charge!.paid) === 0
  )
}

// Desfazer isenção: só antes de aprovar
export function canUnwaive(entry: GraduationEntry) {
  return entry.charge?.status === 'waived' && entry.result !== 'approved'
}

// "a Laranja e a Verde" · "a Laranja, a Verde e a Azul"
export function beltNames(belts: Belt[]) {
  const names = belts.map((belt) => `a ${belt.name}`)
  if (names.length <= 1) return names.join('')
  return `${names.slice(0, -1).join(', ')} e ${names[names.length - 1]}`
}
