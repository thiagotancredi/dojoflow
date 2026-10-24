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
  EMAIL_ALREADY_REGISTERED: 'Esse e-mail já é usado por outra conta.',
  ENROLLMENT_BILLING_INCOMPLETE:
    'Matrícula ativa precisa de mensalidade e dia de vencimento, ou ser marcada como isenta.',
  CHARGE_ALREADY_EXISTS: 'Esse mês já tem cobrança nesta matrícula.',
  CHARGE_NOT_PAST:
    'Só dá para lançar meses anteriores ao início da cobrança automática.',
  CHARGE_HAS_PAYMENTS:
    'Essa cobrança já tem pagamento. Exclua a baixa antes de mudar.',
  CHARGE_NOT_FOUND: 'Cobrança não encontrada.',
  PAYMENT_EXCEEDS_OPEN: 'O valor é maior que o total em aberto.',
  NOTHING_TO_PAY: 'Este aluno não tem nada em aberto.',
  PAYMENT_NOT_FOUND: 'Pagamento não encontrado. Recarregue a página.',
  ACADEMY_BLOCKED: 'Academia desativada. Fale com o suporte.',
  ADMIN_ONLY: 'Sem acesso.',
  ADMIN_EMAIL_LOCKED: 'Você não pode trocar o seu próprio e-mail por aqui.',
  CANNOT_BLOCK_OWN_ACADEMY: 'Você não pode desativar a sua própria academia.',
  CANNOT_RESET_OWN_PASSWORD:
    'Troque a sua senha em Configurações → Conta, no app.',
  ADMIN_EMAIL_RESERVED: 'Esse e-mail não pode ser usado.',
  ACADEMY_NOT_FOUND: 'Academia não encontrada.',
  SUPPORT_CODE_INVALID:
    'Link de suporte inválido ou expirado. Clique em Entrar de novo no painel.',
  SUPPORT_MODE: 'Indisponível no modo suporte.',
  SUPPORT_SESSION_INVALID: 'Sessão de suporte encerrada.',
  INFINITEPAY_KEY_REJECTED:
    'A chave de API não foi aceita. Crie uma chave nova no app da InfinitePay (Checkout → Configurações → API Keys) e cole aqui.',
  INFINITEPAY_CHECKOUT_DISABLED:
    "A InfinitePay ainda não liberou o checkout para essa tag. Confira se a tag está certa e, no app da InfinitePay, desligue e ligue de novo 'Habilitar Checkout Integrado'.",
  INFINITEPAY_UNAVAILABLE:
    'Não foi possível falar com a InfinitePay agora. Tente de novo.',
  INFINITEPAY_DISABLED: 'O pagamento pela InfinitePay está desligado.',
  REVIEW_NOT_FOUND: 'Esse aviso já foi resolvido. Recarregue a página.',
  NOT_FOUND: 'Não encontrado.',
  CONFLICT: 'Esse registro conflita com outro já existente.',
}

const GENERIC_MESSAGE = 'Não foi possível falar com o servidor. Tente de novo.'

// Códigos cujo "detail" já vem em português e diz mais que o texto fixo
// (ex.: "O máximo é R$ 200,00.")
const DETAIL_IS_MESSAGE = new Set(['PAYMENT_EXCEEDS_OPEN', 'NOTHING_TO_PAY'])

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
  if (code && DETAIL_IS_MESSAGE.has(code)) {
    const { detail } = error as { detail?: unknown }
    if (typeof detail === 'string' && detail) return detail
  }
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
