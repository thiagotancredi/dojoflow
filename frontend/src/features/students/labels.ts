import type { Schemas } from '@/lib/api/client'

type Relationship = Schemas['StudentResponsibleRelationship']
type Sex = Schemas['StudentSex']

// "self" (o próprio aluno) não entra aqui: como no bot do Telegram, quando o
// responsável é o próprio aluno nada é gravado.
export const RELATIONSHIP_LABELS: Record<Exclude<Relationship, 'self'>, string> =
  {
    father: 'Pai',
    mother: 'Mãe',
    grandmother: 'Avó',
    grandfather: 'Avô',
    uncle: 'Tio',
    aunt: 'Tia',
    brother: 'Irmão',
    sister: 'Irmã',
  }

export function relationshipLabel(relationship: Relationship) {
  return relationship === 'self'
    ? 'O próprio aluno'
    : RELATIONSHIP_LABELS[relationship]
}

export const SEX_LABELS: Record<Sex, string> = {
  male: 'Masculino',
  female: 'Feminino',
  other: 'Outro',
}
