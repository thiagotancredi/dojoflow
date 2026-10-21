import { api, unwrap } from '@/lib/api/client'
import type { ApiError, Schemas } from '@/lib/api/client'

// Login/refresh devolvem só a sessão (token); quem é o usuário vem de getMe().
export type AuthTokens = Schemas['AuthTokenResponse']
export type Master = Schemas['MasterContextApiRead']
export type SetCredentialsInput = Schemas['SetCredentialsRequest']
export type TelegramLink = Schemas['TelegramLinkTokenResponse']

// Define e-mail e senha. Dois jeitos de provar quem é:
// - logado: manda current_password (troca de senha em Configurações)
// - pelo bot: manda setup_token (link do /web, página /definir-acesso)
// Devolve uma sessão nova; o backend derruba as sessões antigas.
export function setCredentials(body: SetCredentialsInput): Promise<AuthTokens> {
  return unwrap(api.POST('/api/v1/auth/set-credentials', { body }))
}

// Link de uso único (15 min) que abre o bot e vincula o Telegram à conta
export function createTelegramLink(): Promise<TelegramLink> {
  return unwrap(api.POST('/api/v1/auth/telegram/link-token'))
}

export async function login(
  email: string,
  password: string,
): Promise<AuthTokens> {
  const { data, error } = await api.POST('/api/v1/auth/login', {
    body: { email, password },
  })

  if (error) {
    throw error as unknown as ApiError
  }

  return data
}

// Dados do mestre logado e da academia (GET /auth/me)
export async function getMe(): Promise<Master> {
  const { data, error } = await api.GET('/api/v1/auth/me')

  if (error) {
    throw error as unknown as ApiError
  }

  return data
}

export async function logout(): Promise<void> {
  await api.POST('/api/v1/auth/logout')
}

let refreshInFlight: Promise<AuthTokens> | null = null

// Troca o cookie de refresh (httpOnly) por um token novo. Chamadas
// simultâneas (ex.: StrictMode em dev) reaproveitam a mesma requisição.
export function refresh(): Promise<AuthTokens> {
  refreshInFlight ??= requestRefresh().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function requestRefresh(): Promise<AuthTokens> {
  const { data, error } = await api.POST('/api/v1/auth/refresh')

  if (error) {
    throw error as unknown as ApiError
  }

  return data
}
