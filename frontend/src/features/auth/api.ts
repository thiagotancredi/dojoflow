import { api } from '@/lib/api/client'
import type { ApiError, Schemas } from '@/lib/api/client'

export type AuthSession = Schemas['AuthTokenResponse']

export async function login(
  email: string,
  password: string,
): Promise<AuthSession> {
  const { data, error } = await api.POST('/api/v1/auth/login', {
    body: { email, password },
  })

  if (error) {
    throw error as unknown as ApiError
  }

  return data
}

export async function logout(): Promise<void> {
  await api.POST('/api/v1/auth/logout')
}

let refreshInFlight: Promise<AuthSession> | null = null

// Troca o cookie de refresh (httpOnly) por uma sessão nova. Chamadas
// simultâneas (ex.: StrictMode em dev) reaproveitam a mesma requisição.
export function refresh(): Promise<AuthSession> {
  refreshInFlight ??= requestRefresh().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function requestRefresh(): Promise<AuthSession> {
  const { data, error } = await api.POST('/api/v1/auth/refresh')

  if (error) {
    throw error as unknown as ApiError
  }

  return data
}
