import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'

export type StudentPage = Schemas['StudentPageRead']
export type StudentListItem = Schemas['StudentListItemRead']
export type EnrollmentStatus = Schemas['EnrollmentStatus']

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
