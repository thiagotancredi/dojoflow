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
  RESPONSIBLE_LINK_NOT_FOUND: 'Responsável não encontrado.',
  CEP_NOT_FOUND: 'CEP não encontrado.',
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

// Texto para o usuário a partir de qualquer erro (API, rede ou código)
export function messageFor(error: unknown, fallback = GENERIC_MESSAGE) {
  const code = errorCode(error)
  return (code && ERROR_MESSAGES[code]) || fallback
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
