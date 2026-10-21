import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'

export type Belt = Schemas['BeltApiRead']
export type BeltPayload = Schemas['BeltPayload']
export type DurationUnit = Schemas['DurationUnit']
export type Eligibility = Schemas['Eligibility']
export type EnrollmentBelts = Schemas['EnrollmentBeltsApiRead']
export type BeltRecord = Schemas['BeltRecordApiRead']
export type EnrollmentBeltPayload = Schemas['EnrollmentBeltApiPayload']
export type PendingEnrollment = Schemas['PendingBeltEnrollmentApiRead']
export type BulkBeltItem = Schemas['BulkBeltItemApi']
export type GraduationListSummary = Schemas['GraduationListSummaryApiRead']
export type GraduationListDetail = Schemas['GraduationListDetailApiRead']
export type GraduationEntry = Schemas['GraduationEntryApiRead']
export type GraduationCandidate = Schemas['GraduationCandidateApiRead']
export type GraduationListCreate = Schemas['GraduationListApiCreate']
export type GraduationListUpdate = Schemas['GraduationListUpdate']

// ---------- Faixas da modalidade (Configurações) ----------
const modalityPath = (modalityId: string) => ({
  params: { path: { modality_id: modalityId } },
})
const beltPath = (beltId: string) => ({ params: { path: { belt_id: beltId } } })

export function listBelts(modalityId: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/academy/modalities/{modality_id}/belts', {
      ...modalityPath(modalityId),
      signal,
    }),
  )
}

export function createBelt(modalityId: string, payload: BeltPayload) {
  return unwrap(
    api.POST('/api/v1/academy/modalities/{modality_id}/belts', {
      ...modalityPath(modalityId),
      body: payload,
    }),
  )
}

export function updateBelt(beltId: string, payload: BeltPayload) {
  return unwrap(
    api.PUT('/api/v1/academy/belts/{belt_id}', {
      ...beltPath(beltId),
      body: payload,
    }),
  )
}

export function deleteBelt(beltId: string) {
  return unwrap(api.DELETE('/api/v1/academy/belts/{belt_id}', beltPath(beltId)))
}

// Ordem completa, da menor para a maior
export function reorderBelts(modalityId: string, beltIds: string[]) {
  return unwrap(
    api.PUT('/api/v1/academy/modalities/{modality_id}/belts/order', {
      ...modalityPath(modalityId),
      body: { belt_ids: beltIds },
    }),
  )
}

// Cria a sequência padrão (só Taekwondo e Kickboxing têm uma)
export function applyBeltPreset(modalityId: string) {
  return unwrap(
    api.POST(
      '/api/v1/academy/modalities/{modality_id}/belts/preset',
      modalityPath(modalityId),
    ),
  )
}

// ---------- Lançar faixas dos alunos antigos ----------
export function listPendingEnrollments(modalityId: string, signal?: AbortSignal) {
  return unwrap(
    api.GET(
      '/api/v1/academy/modalities/{modality_id}/belts/pending-enrollments',
      { ...modalityPath(modalityId), signal },
    ),
  )
}

export function registerBeltsInBulk(modalityId: string, items: BulkBeltItem[]) {
  return unwrap(
    api.POST('/api/v1/academy/modalities/{modality_id}/belts/bulk', {
      ...modalityPath(modalityId),
      body: { items },
    }),
  )
}

// ---------- Histórico de faixas de uma matrícula ----------
const enrollmentPath = (studentId: string, enrollmentId: string) => ({
  student_id: studentId,
  enrollment_id: enrollmentId,
})

export function getEnrollmentBelts(
  studentId: string,
  enrollmentId: string,
  signal?: AbortSignal,
) {
  return unwrap(
    api.GET('/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts', {
      params: { path: enrollmentPath(studentId, enrollmentId) },
      signal,
    }),
  )
}

export function addEnrollmentBelt(
  studentId: string,
  enrollmentId: string,
  payload: EnrollmentBeltPayload,
) {
  return unwrap(
    api.POST('/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts', {
      params: { path: enrollmentPath(studentId, enrollmentId) },
      body: payload,
    }),
  )
}

export function updateEnrollmentBelt(
  studentId: string,
  enrollmentId: string,
  recordId: string,
  payload: EnrollmentBeltPayload,
) {
  return unwrap(
    api.PUT(
      '/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts/{record_id}',
      {
        params: {
          path: { ...enrollmentPath(studentId, enrollmentId), record_id: recordId },
        },
        body: payload,
      },
    ),
  )
}

export function deleteEnrollmentBelt(
  studentId: string,
  enrollmentId: string,
  recordId: string,
) {
  return unwrap(
    api.DELETE(
      '/api/v1/students/{student_id}/enrollments/{enrollment_id}/belts/{record_id}',
      {
        params: {
          path: { ...enrollmentPath(studentId, enrollmentId), record_id: recordId },
        },
      },
    ),
  )
}

// ---------- Listas de graduação ----------
const listPath = (listId: string) => ({ params: { path: { list_id: listId } } })

export function listGraduationLists(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/graduation-lists', { signal }))
}

export function createGraduationList(payload: GraduationListCreate) {
  return unwrap(api.POST('/api/v1/graduation-lists', { body: payload }))
}

export function getGraduationList(listId: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/graduation-lists/{list_id}', { ...listPath(listId), signal }),
  )
}

export function updateGraduationList(
  listId: string,
  payload: GraduationListUpdate,
) {
  return unwrap(
    api.PATCH('/api/v1/graduation-lists/{list_id}', {
      ...listPath(listId),
      body: payload,
    }),
  )
}

export function deleteGraduationList(listId: string) {
  return unwrap(api.DELETE('/api/v1/graduation-lists/{list_id}', listPath(listId)))
}

// Faixa pretendida vazia = a próxima da sequência (o backend decide)
export function addGraduationEntry(
  listId: string,
  enrollmentId: string,
  targetBeltId?: string,
) {
  return unwrap(
    api.POST('/api/v1/graduation-lists/{list_id}/entries', {
      ...listPath(listId),
      body: { enrollment_id: enrollmentId, target_belt_id: targetBeltId ?? null },
    }),
  )
}

export function updateGraduationEntry(
  listId: string,
  entryId: string,
  targetBeltId: string,
) {
  return unwrap(
    api.PATCH('/api/v1/graduation-lists/{list_id}/entries/{entry_id}', {
      params: { path: { list_id: listId, entry_id: entryId } },
      body: { target_belt_id: targetBeltId },
    }),
  )
}

export function removeGraduationEntry(listId: string, entryId: string) {
  return unwrap(
    api.DELETE('/api/v1/graduation-lists/{list_id}/entries/{entry_id}', {
      params: { path: { list_id: listId, entry_id: entryId } },
    }),
  )
}
