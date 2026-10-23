import { api, type Schemas, unwrap } from '@/lib/api/client'
import { useResource } from '@/lib/hooks/useResource'

export type PublicPayment = Schemas['PublicPaymentRead']

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
