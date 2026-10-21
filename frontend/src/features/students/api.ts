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
