import { listStudents } from '@/features/students/api'
import type { StudentFilters } from '@/features/students/api'
import { useResource } from '@/lib/hooks/useResource'

// Lista de alunos; busca de novo quando qualquer filtro muda
export function useStudents(filters: StudentFilters) {
  return useResource(
    JSON.stringify(filters),
    (signal) => listStudents(filters, signal),
    { keepPrevious: true },
  )
}
