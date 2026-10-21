import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'

export type AdminAcademy = Schemas['AdminAcademyRead']
export type AdminAcademyCreate = Schemas['AdminAcademyCreate']
export type AdminAcademyUpdate = Schemas['AdminAcademyUpdate']
export type AdminCredentials = Schemas['AdminCredentialsRead']
export type AcademyStatus = AdminAcademy['status']

// 200 = é o administrador; 403 ADMIN_ONLY = logado, mas sem acesso
export function getAdminMe(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/admin/me', { signal }))
}

export function listAcademies(search: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/admin/academies', {
      params: { query: search ? { search } : {} },
      signal,
    }),
  )
}

export function createAcademy(body: AdminAcademyCreate) {
  return unwrap(api.POST('/api/v1/admin/academies', { body }))
}

export function updateAcademy(academyId: string, body: AdminAcademyUpdate) {
  return unwrap(
    api.PATCH('/api/v1/admin/academies/{academy_id}', {
      params: { path: { academy_id: academyId } },
      body,
    }),
  )
}

// Gera uma senha nova para o mestre e derruba as sessões abertas dele
export function resetPassword(academyId: string) {
  return unwrap(
    api.POST('/api/v1/admin/academies/{academy_id}/reset-password', {
      params: { path: { academy_id: academyId } },
    }),
  )
}

export function setAcademyStatus(academyId: string, status: AcademyStatus) {
  return unwrap(
    api.POST('/api/v1/admin/academies/{academy_id}/status', {
      params: { path: { academy_id: academyId } },
      body: { status },
    }),
  )
}

// Código de uso único (60 s) para abrir a academia em modo suporte
export function createSupportEntry(academyId: string) {
  return unwrap(
    api.POST('/api/v1/admin/academies/{academy_id}/support-entry', {
      params: { path: { academy_id: academyId } },
    }),
  )
}

// Mensagem pronta para colar no WhatsApp do mestre
export function buildWhatsAppAccessMessage(email: string, password: string) {
  return `Seu acesso ao Katsuflow:\nhttps://katsuflow.com.br\nE-mail: ${email}\nSenha: ${password}`
}
