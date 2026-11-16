import {
  createPayment,
  deletePayment,
  getBillingOverview,
  getBillingSettings,
  getGraduationOverview,
  getStudentBilling,
  createPayLink,
  launchAdvance,
  launchCharge,
  resolveReview,
  saveBillingSettings,
  unwaiveCharge,
  updateCharge,
  waiveCharge,
} from '@/features/billing/api'
import type {
  BillingSettings,
  AdvancePayload,
  CreatePaymentPayload,
  LaunchChargePayload,
  OverviewFilters,
  UpdateChargePayload,
} from '@/features/billing/api'
import { useMutation } from '@/lib/hooks/useMutation'
import { useResource } from '@/lib/hooks/useResource'

// Mensalidades do aluno (a tela chama refetch depois de cada ação)
export function useStudentBilling(studentId: string | null) {
  return useResource(studentId, (signal) =>
    getStudentBilling(studentId as string, signal),
  )
}

// Página Mensalidades; busca de novo quando qualquer filtro muda
export function useBillingOverview(filters: OverviewFilters) {
  return useResource(
    JSON.stringify(filters),
    (signal) => getBillingOverview(filters, signal),
    { keepPrevious: true },
  )
}

// Financeiro, aba Graduação (busca de novo quando o mês muda)
export function useGraduationOverview(month: string) {
  return useResource(`graduation-overview-${month}`, (signal) =>
    getGraduationOverview(month, signal),
  )
}

export function useBillingSettings() {
  return useResource('billing-settings', (signal) =>
    getBillingSettings(signal),
  )
}

// ---------- Escrita ----------
export function useCreatePayLink(studentId: string) {
  return useMutation((amount: string) => createPayLink(studentId, amount))
}

export function useLaunchCharge(studentId: string) {
  return useMutation((payload: LaunchChargePayload) =>
    launchCharge(studentId, payload),
  )
}

export function useLaunchAdvance(studentId: string) {
  return useMutation((payload: AdvancePayload) =>
    launchAdvance(studentId, payload),
  )
}

export function useUpdateCharge(studentId: string) {
  return useMutation((chargeId: string, payload: UpdateChargePayload) =>
    updateCharge(studentId, chargeId, payload),
  )
}

// waived=true isenta; false desfaz
export function useSetChargeWaived(studentId: string) {
  return useMutation((chargeId: string, waived: boolean) =>
    waived
      ? waiveCharge(studentId, chargeId)
      : unwaiveCharge(studentId, chargeId),
  )
}

// studentId no chamado: a página Mensalidades dá baixa em vários alunos
export function useCreatePayment() {
  return useMutation((studentId: string, payload: CreatePaymentPayload) =>
    createPayment(studentId, payload),
  )
}

export function useDeletePayment(studentId: string) {
  return useMutation((paymentId: string) =>
    deletePayment(studentId, paymentId),
  )
}

export function useResolveReview(studentId: string) {
  return useMutation((reviewId: string) => resolveReview(studentId, reviewId))
}

export function useSaveBillingSettings() {
  return useMutation((payload: BillingSettings) =>
    saveBillingSettings(payload),
  )
}
