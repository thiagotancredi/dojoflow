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
