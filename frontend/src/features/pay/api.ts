import { api, type Schemas, unwrap } from '@/lib/api/client'
import { useResource } from '@/lib/hooks/useResource'

export type PublicPayment = Schemas['PublicPaymentRead']
export type PayConfirm = Schemas['PayConfirmApi']

// Página pública /pagar/:token (sem login: o código do link é o segredo)
export function getPublicPayment(token: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/public/pay/{token}', {
      params: { path: { token } },
      signal,
    }),
  )
}

export function usePublicPayment(token: string | undefined) {
  return useResource(token ? `public-pay:${token}` : null, (signal) =>
    getPublicPayment(token ?? '', signal),
  )
}

// "Pagar mensalidade": o endereço do checkout da InfinitePay com tudo o
// que está em aberto
export function createCheckout(token: string) {
  return unwrap(
    api.POST('/api/v1/public/pay/{token}/checkout', {
      params: { path: { token } },
    }),
  )
}

// Volta do checkout: manda os dados que a InfinitePay acrescentou ao
// endereço; o servidor confere e dá a baixa (a página acompanha pelo GET)
export function confirmPayment(token: string, body: PayConfirm) {
  return unwrap(
    api.POST('/api/v1/public/pay/{token}/confirm', {
      params: { path: { token } },
      body,
    }),
  )
}

// Link que não existe (ou de academia desativada): o backend responde 404
// com este código
export function isInvalidLink(error: unknown) {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    error.code === 'PAY_LINK_INVALID'
  )
}
