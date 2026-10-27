import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'
import { useMutation } from '@/lib/hooks/useMutation'
import { useResource } from '@/lib/hooks/useResource'

// Cobrança por e-mail (Configurações → Cobrança): liga/desliga o envio do
// dia 1º e mostra a prévia do e-mail.

export type EmailBillingStatus = Schemas['EmailBillingStatusApi']
export type EmailPreview = Schemas['EmailPreviewApi']

export function getEmailBilling(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/academy/email-billing', { signal }))
}

// 409 BILLING_NOT_CONFIGURED quando não há Pix nem InfinitePay
export function setEmailBilling(enabled: boolean) {
  return unwrap(
    api.PUT('/api/v1/academy/email-billing', { body: { enabled } }),
  )
}

export function getEmailPreview(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/academy/email-billing/preview', { signal }))
}

export function useEmailBilling() {
  return useResource('email-billing', (signal) => getEmailBilling(signal))
}

export function useSetEmailBilling() {
  return useMutation((enabled: boolean) => setEmailBilling(enabled))
}

// A prévia só é buscada com a janela aberta (key = null → não busca)
export function useEmailPreview(open: boolean) {
  return useResource(open ? 'email-preview' : null, (signal) =>
    getEmailPreview(signal),
  )
}
