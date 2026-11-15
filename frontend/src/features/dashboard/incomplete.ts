import type { DashboardSummary } from '@/features/dashboard/api'

// Cadastro incompleto: o motivo na API, o filtro na URL de Alunos e o texto
export type Incomplete = DashboardSummary['incomplete']
type IncompleteKind = keyof Incomplete

// Linha do cartão → filtro da tela Alunos (?incompleto=...)
export const INCOMPLETE_ITEMS: {
  key: IncompleteKind
  param: string
  label: string
}[] = [
  { key: 'no_phone', param: 'sem-telefone', label: 'Sem telefone' },
  { key: 'no_birth_date', param: 'sem-nascimento', label: 'Sem data de nascimento' },
  { key: 'no_email', param: 'sem-email', label: 'Sem e-mail' },
  {
    key: 'minor_without_responsible',
    param: 'menor-sem-responsavel',
    label: 'Menor sem responsável',
  },
]
