import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'

export type StudentPage = Schemas['StudentPageRead']
export type StudentSummary = Schemas['StudentListItemRead']
export type EnrollmentStatus = Schemas['EnrollmentStatus']
export type StudentDetail = Schemas['StudentDetailRead']
export type Enrollment = Schemas['EnrollmentApiRead']
export type ResponsibleLink = Schemas['ResponsibleLinkApiRead']

export const PAGE_SIZE = 20

export type StudentFilters = {
  search: string
  status: EnrollmentStatus
  modalityId: string | null
  missingEmail: boolean
  page: number
}

// Lista paginada; busca vazia não é enviada
export function listStudents(filters: StudentFilters, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/students', {
      params: {
        query: {
          search: filters.search.trim() || undefined,
          status: filters.status,
          modality_id: filters.modalityId ?? undefined,
          missing_email: filters.missingEmail || undefined,
          page: filters.page,
          page_size: PAGE_SIZE,
        },
      },
      signal,
    }),
  )
}

// Ficha completa: dados, endereço, responsáveis e matrículas
export function getStudent(studentId: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/students/{student_id}', {
      params: { path: { student_id: studentId } },
      signal,
    }),
  )
}

export type BasicDataPayload = Schemas['StudentBasicUpdateRequest']
export type AddressPayload = Schemas['StudentAddressPayload']
export type CepAddress = Schemas['CepAddress']

export function updateStudent(studentId: string, payload: BasicDataPayload) {
  return unwrap(
    api.PATCH('/api/v1/students/{student_id}', {
      params: { path: { student_id: studentId } },
      body: payload,
    }),
  )
}

export function saveAddress(studentId: string, payload: AddressPayload) {
  return unwrap(
    api.PUT('/api/v1/students/{student_id}/address', {
      params: { path: { student_id: studentId } },
      body: payload,
    }),
  )
}

export function removeAddress(studentId: string) {
  return unwrap(
    api.DELETE('/api/v1/students/{student_id}/address', {
      params: { path: { student_id: studentId } },
    }),
  )
}

// Endereço pelo CEP (8 números)
export function lookupCep(zipCode: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/cep/{zip_code}', {
      params: { path: { zip_code: zipCode } },
      signal,
    }),
  )
}

export type ResponsiblePayload = Schemas['StudentResponsiblePayload']

export function addResponsible(studentId: string, payload: ResponsiblePayload) {
  return unwrap(
    api.POST('/api/v1/students/{student_id}/responsibles', {
      params: { path: { student_id: studentId } },
      body: payload,
    }),
  )
}

// Remove o vínculo (a pessoa continua cadastrada, ligada a outros alunos)
export function removeResponsible(studentId: string, linkId: string) {
  return unwrap(
    api.DELETE('/api/v1/students/{student_id}/responsibles/{link_id}', {
      params: { path: { student_id: studentId, link_id: linkId } },
    }),
  )
}

export type EnrollmentUpdatePayload = Schemas['EnrollmentApiUpdateRequest']
export type EnrollmentPayload = Schemas['EnrollmentApiPayload']

export function updateEnrollment(
  studentId: string,
  enrollmentId: string,
  payload: EnrollmentUpdatePayload,
) {
  return unwrap(
    api.PATCH('/api/v1/students/{student_id}/enrollments/{enrollment_id}', {
      params: {
        path: { student_id: studentId, enrollment_id: enrollmentId },
      },
      body: payload,
    }),
  )
}

export function addEnrollment(studentId: string, payload: EnrollmentPayload) {
  return unwrap(
    api.POST('/api/v1/students/{student_id}/enrollments', {
      params: { path: { student_id: studentId } },
      body: payload,
    }),
  )
}

export type StudentCreatePayload = Schemas['StudentCreateApiRequest']

// Cadastro completo numa gravação só (aluno, endereço, responsáveis e
// matrículas): se algo falhar, nada é gravado
export function createStudent(payload: StudentCreatePayload) {
  return unwrap(api.POST('/api/v1/students', { body: payload }))
}
