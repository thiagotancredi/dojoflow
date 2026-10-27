import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'
import { useMutation } from '@/lib/hooks/useMutation'
import { useResource } from '@/lib/hooks/useResource'

// Baixa automática pela InfinitePay (Configurações → Cobrança).
// A chave de API vai só na hora de ligar: a API nunca devolve, no máximo
// os 4 últimos caracteres (key_last4).

export type InfinitePayStatus = Schemas['InfinitePayStatusApi']
export type InfinitePayConnectPayload = Schemas['InfinitePayConnectApi']

export function getInfinitePay(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/academy/infinitepay', { signal }))
}

// Testar e ligar (também troca a chave). Erros 409 trazem o texto do que
// fazer no "detail" (chave recusada, checkout não liberado, sem conexão).
export function connectInfinitePay(payload: InfinitePayConnectPayload) {
  return unwrap(api.PUT('/api/v1/academy/infinitepay', { body: payload }))
}

export function disconnectInfinitePay() {
  return unwrap(api.DELETE('/api/v1/academy/infinitepay'))
}

export function useInfinitePay() {
  return useResource('infinitepay', (signal) => getInfinitePay(signal))
}

export function useConnectInfinitePay() {
  return useMutation((payload: InfinitePayConnectPayload) =>
    connectInfinitePay(payload),
  )
}

export function useDisconnectInfinitePay() {
  return useMutation(() => disconnectInfinitePay())
}
