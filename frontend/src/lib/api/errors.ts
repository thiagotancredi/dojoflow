import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { toast } from 'sonner'

// Textos em português para os códigos de erro do backend ({detail, code}).
// Código sem texto aqui cai na mensagem genérica.
export const ERROR_MESSAGES: Record<string, string> = {
  STUDENT_NOT_FOUND: 'Aluno não encontrado.',
  ENROLLMENT_NOT_FOUND: 'Matrícula não encontrada.',
  ENROLLMENT_ALREADY_EXISTS: 'O aluno já está matriculado nessa modalidade.',
  MODALITY_NOT_FOUND: 'Modalidade não encontrada.',
  MODALITY_NOT_ENABLED: 'Essa modalidade não é oferecida pela academia.',
  MODALITY_HAS_ACTIVE_ENROLLMENTS:
    'Essa modalidade tem alunos com matrícula ativa. Inative as matrículas antes de remover.',
  RESPONSIBLE_LINK_NOT_FOUND: 'Responsável não encontrado.',
  CEP_NOT_FOUND: 'CEP não encontrado.',
  BELT_NAME_TAKEN: 'Já existe uma faixa com esse nome nesta modalidade.',
  BELT_IN_USE:
    'Essa faixa está no histórico de algum aluno ou numa lista de graduação e não pode ser excluída. Você pode renomeá-la.',
  BELT_ORDER_MISMATCH: 'A lista de faixas mudou. Recarregue a página.',
  BELTS_ALREADY_EXIST: 'Esta modalidade já tem faixas cadastradas.',
  PRESET_NOT_AVAILABLE: 'Esta modalidade não tem sequência padrão.',
  BELT_NOT_FOUND: 'Faixa não encontrada.',
  BELT_MODALITY_MISMATCH: 'Essa faixa é de outra modalidade.',
  BELT_RECORD_NOT_FOUND: 'Registro de faixa não encontrado.',
  MODALITY_HAS_NO_BELTS: 'Cadastre as faixas da modalidade antes de criar a lista.',
  GRADUATION_LIST_NOT_FOUND: 'Lista de graduação não encontrada.',
  GRADUATION_ENTRY_NOT_FOUND: 'Esse aluno não está mais na lista.',
  ALREADY_IN_LIST: 'Esse aluno já está na lista.',
  ENROLLMENT_NOT_CANDIDATE:
    'Só alunos com matrícula ativa nesta modalidade podem entrar na lista.',
  TARGET_BELT_REQUIRED:
    'O aluno já está na última faixa: escolha a faixa pretendida.',
  ENROLLMENT_MODALITY_MISMATCH: 'Uma das matrículas é de outra modalidade.',
  DUPLICATE_ENROLLMENT_IN_BATCH: 'O mesmo aluno aparece duas vezes.',
  ENROLLMENT_NOT_PENDING:
    'Um dos alunos já tem faixa ou está inativo. Recarregue a página.',
  CURRENT_PASSWORD_INVALID: 'Senha atual incorreta.',
  SETUP_TOKEN_INVALID:
    'Este link é inválido ou expirou. Envie /web para o bot no Telegram e receba outro.',
  EMAIL_ALREADY_REGISTERED: 'Esse e-mail já é usado por outra conta.',
  NOT_FOUND: 'Não encontrado.',
  CONFLICT: 'Esse registro conflita com outro já existente.',
}

const GENERIC_MESSAGE = 'Não foi possível falar com o servidor. Tente de novo.'

// Erro de validação do FastAPI (422): uma lista de problemas por campo
type ValidationIssue = { loc: (string | number)[]; msg: string; type: string }

function errorCode(error: unknown): string | null {
  if (typeof error === 'object' && error !== null && 'code' in error) {
    const { code } = error as { code: unknown }
    return typeof code === 'string' ? code : null
  }
  return null
}

function validationIssues(error: unknown): ValidationIssue[] | null {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    const { detail } = error as { detail: unknown }
    if (Array.isArray(detail)) return detail as ValidationIssue[]
  }
  return null
}

// 422 do FastAPI (lista de erros por campo)?
export function isValidationError(error: unknown) {
  return validationIssues(error) !== null
}

// Texto para o usuário a partir de qualquer erro (API, rede ou código)
export function messageFor(error: unknown, fallback = GENERIC_MESSAGE) {
  const code = errorCode(error)
  if (code && ERROR_MESSAGES[code]) return ERROR_MESSAGES[code]
  // 422: algum dado não passou na validação (ex.: data com ano errado)
  if (validationIssues(error)) return 'Revise os dados informados (datas e campos).'
  return fallback
}

// Mostra o erro num toast (404, 409, 500, falha de rede)
export function showApiError(error: unknown, fallback?: string) {
  toast.error(messageFor(error, fallback))
}

const FIELD_MESSAGES: Record<string, string> = {
  missing: 'Campo obrigatório.',
  string_too_short: 'Texto muito curto.',
  string_too_long: 'Texto muito longo.',
}

// 422 → marca cada campo do formulário com o erro. O nome do campo no
// formulário é o mesmo da API (ex.: "name", "enrollments.0.due_day").
// Devolve true se era um 422 (aí não precisa de toast).
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
): boolean {
  const issues = validationIssues(error)
  if (!issues) return false

  for (const issue of issues) {
    // loc = ['body', 'enrollments', 0, 'due_day'] → 'enrollments.0.due_day'
    const field = issue.loc.slice(1).join('.') as Path<T>
    setError(field, {
      message: FIELD_MESSAGES[issue.type] ?? 'Valor inválido.',
    })
  }
  return true
}
