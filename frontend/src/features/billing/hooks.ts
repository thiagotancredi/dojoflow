import {
  createPayment,
  deletePayment,
  getBillingOverview,
  getBillingSettings,
  getStudentBilling,
  launchPastCharge,
  saveBillingSettings,
  unwaiveCharge,
  updateCharge,
  waiveCharge,
} from '@/features/billing/api'
import type {
  BillingSettings,
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

export function useBillingSettings() {
  return useResource('billing-settings', (signal) =>
    getBillingSettings(signal),
  )
}

// ---------- Escrita ----------
export function useLaunchPastCharge(studentId: string) {
  return useMutation((payload: LaunchChargePayload) =>
    launchPastCharge(studentId, payload),
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

export function useSaveBillingSettings() {
  return useMutation((payload: BillingSettings) =>
    saveBillingSettings(payload),
  )
}
