import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'
import { useMutation } from '@/lib/hooks/useMutation'

// Recuperar senha por e-mail (telas públicas, sem login).

export type PasswordResetConfirmPayload = Schemas['PasswordResetConfirm']

// Sempre responde 202, exista o e-mail ou não (a API não revela quem tem conta)
export function requestPasswordReset(email: string) {
  return unwrap(
    api.POST('/api/v1/auth/password-reset/request', { body: { email } }),
  )
}

// Link vencido ou já usado: 401 com code RESET_LINK_INVALID
export function confirmPasswordReset(payload: PasswordResetConfirmPayload) {
  return unwrap(
    api.POST('/api/v1/auth/password-reset/confirm', { body: payload }),
  )
}

export function useRequestPasswordReset() {
  return useMutation((email: string) => requestPasswordReset(email))
}

export function useConfirmPasswordReset() {
  return useMutation((payload: PasswordResetConfirmPayload) =>
    confirmPasswordReset(payload),
  )
}
