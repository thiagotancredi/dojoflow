import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

// Cliente HTTP tipado a partir do OpenAPI do backend (schema.d.ts).
// URL, parâmetros, corpo e resposta de cada rota são checados pelo TypeScript.
//
// baseUrl vazio = mesma origem: em dev o Vite repassa /api para o FastAPI
// (ver vite.config.ts), então o cookie de refresh funciona sem CORS.
//
// Uso:
//   const { data, error } = await api.GET('/api/v1/students', {
//     params: { query: { page: 1 } },
//   })
export const api = createClient<paths>({ baseUrl: '' })

// Atalho para os modelos do backend: Schemas['StudentDetailRead'] etc.
export type Schemas = components['schemas']

// Erros de regra de negócio ({detail, code}) vêm dos exception handlers do
// backend e não aparecem no OpenAPI, por isso o tipo é escrito à mão.
export type ApiError = {
  detail: string
  code: string
}

// Token atual, atualizado pelo AuthProvider (o React não alcança este módulo)
let accessToken: string | null = null

export function setApiToken(token: string | null) {
  accessToken = token
}

// Quem renova a sessão quando a API devolve 401 (registrado pelo AuthProvider).
// Devolve o token novo, ou null se não deu para renovar.
let refreshHandler: (() => Promise<string | null>) | null = null

export function setRefreshHandler(
  handler: (() => Promise<string | null>) | null,
) {
  refreshHandler = handler
}

// Cópias das requisições em andamento, para repetir depois de um refresh
// (o corpo de uma requisição só pode ser lido uma vez).
const retryCopies = new Map<string, Request>()

// Rotas da própria sessão nunca disparam refresh (ex.: senha errada no login
// dá 401). As outras /auth/* (me, set-credentials, telegram) renovam normal.
const SESSION_ROUTES = new Set([
  '/api/v1/auth/login',
  '/api/v1/auth/register',
  '/api/v1/auth/refresh',
  '/api/v1/auth/logout',
])

function isSessionRoute(request: Request) {
  return SESSION_ROUTES.has(new URL(request.url).pathname)
}

api.use({
  // Antes de toda requisição: anexa o token e guarda uma cópia
  onRequest({ request, id }) {
    if (accessToken) {
      request.headers.set('Authorization', `Bearer ${accessToken}`)
    }
    if (!isSessionRoute(request)) {
      retryCopies.set(id, request.clone())
    }
    return request
  },

  // 401 (token expirado): renova a sessão uma vez e repete a requisição
  async onResponse({ response, id }) {
    const copy = retryCopies.get(id)
    retryCopies.delete(id)

    if (response.status !== 401 || !copy || !refreshHandler) {
      return response
    }

    const newToken = await refreshHandler()
    if (!newToken) {
      return response
    }

    copy.headers.set('Authorization', `Bearer ${newToken}`)
    return fetch(copy)
  },

  // Falha de rede: só descarta a cópia
  onError({ id }) {
    retryCopies.delete(id)
  },
})

// Resposta da API → dado, ou lança o corpo do erro ({detail, code} ou 422).
// Uso: const page = await unwrap(api.GET('/api/v1/students', {...}))
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request

  if (error !== undefined) {
    throw error
  }

  return data as T
}
