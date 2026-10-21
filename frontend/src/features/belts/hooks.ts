import {
  getEnrollmentBelts,
  getGraduationList,
  listBelts,
  listGraduationLists,
  listPendingEnrollments,
} from '@/features/belts/api'
import { useResource } from '@/lib/hooks/useResource'

// Faixas da modalidade, em ordem (null = não buscar)
export function useBelts(modalityId: string | null) {
  return useResource(modalityId ? `belts:${modalityId}` : null, (signal) =>
    listBelts(modalityId as string, signal),
  )
}

// Matrículas ativas da modalidade ainda sem faixa registrada
export function usePendingEnrollments(modalityId: string) {
  return useResource(`pending:${modalityId}`, (signal) =>
    listPendingEnrollments(modalityId, signal),
  )
}

// Faixa atual, aptidão e histórico de uma matrícula
export function useEnrollmentBelts(studentId: string, enrollmentId: string) {
  return useResource(`enrollment-belts:${enrollmentId}`, (signal) =>
    getEnrollmentBelts(studentId, enrollmentId, signal),
  )
}

export function useGraduationLists() {
  return useResource('graduation-lists', listGraduationLists)
}

export function useGraduationList(listId: string | undefined) {
  return useResource(listId ? `graduation-list:${listId}` : null, (signal) =>
    getGraduationList(listId as string, signal),
  )
}
