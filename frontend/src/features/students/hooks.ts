import {
  getStudent,
  listStudents,
  removeAddress,
  saveAddress,
  updateStudent,
} from '@/features/students/api'
import type { AddressPayload, BasicDataPayload } from '@/features/students/api'
import type { StudentFilters } from '@/features/students/api'
import { useMutation } from '@/lib/hooks/useMutation'
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

// ---------- Escrita (a tela chama refetch da ficha depois) ----------
export function useUpdateStudent(studentId: string) {
  return useMutation((payload: BasicDataPayload) =>
    updateStudent(studentId, payload),
  )
}

export function useSaveAddress(studentId: string) {
  return useMutation((payload: AddressPayload) =>
    saveAddress(studentId, payload),
  )
}

export function useRemoveAddress(studentId: string) {
  return useMutation(() => removeAddress(studentId))
}
