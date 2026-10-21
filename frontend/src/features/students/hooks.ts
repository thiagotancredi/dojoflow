import { getStudent, listStudents } from '@/features/students/api'
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

// Ficha de um aluno; trocar de aluno mostra "carregando" (não o anterior)
export function useStudent(studentId: string | undefined) {
  return useResource(studentId ?? null, (signal) =>
    getStudent(studentId as string, signal),
  )
}
