import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'

// Mensalidades: cobranças, baixas, visão geral e configurações de cobrança.
// Dinheiro vai e volta como texto com ponto ("150.00"), igual ao resto da API.

export type StudentBilling = Schemas['StudentBillingApiRead']
export type Charge = Schemas['ChargeApiRead']
export type ChargeStatus = Charge['status']
export type Payment = Schemas['PaymentApiRead']
export type PaymentPreview = Schemas['PaymentPreviewApiRead']
export type BillingOverview = Schemas['BillingOverviewRead']
export type BillingOverviewItem = Schemas['BillingOverviewItemRead']
export type BillingSettings = Schemas['BillingSettingsApi']

export type LaunchChargePayload = Schemas['LaunchChargeApiPayload']
export type UpdateChargePayload = Schemas['UpdateChargeApiPayload']
export type CreatePaymentPayload = Schemas['CreatePaymentApiPayload']
export type BulkPaymentPayload = Schemas['BulkPaymentApiPayload']

export type OverviewFilter = 'overdue' | 'upcoming' | 'paid' | 'all'

export type OverviewFilters = {
  month: string // "2026-10"
  filter: OverviewFilter
  search: string
  page: number
}

export const OVERVIEW_PAGE_SIZE = 20

// ---------- Ficha do aluno ----------
export function getStudentBilling(studentId: string, signal?: AbortSignal) {
  return unwrap(
    api.GET('/api/v1/students/{student_id}/billing', {
      params: { path: { student_id: studentId } },
      signal,
    }),
  )
}

export function launchPastCharge(
  studentId: string,
  payload: LaunchChargePayload,
) {
  return unwrap(
    api.POST('/api/v1/students/{student_id}/billing/charges', {
      params: { path: { student_id: studentId } },
      body: payload,
    }),
  )
}

export function updateCharge(
  studentId: string,
  chargeId: string,
  payload: UpdateChargePayload,
) {
  return unwrap(
    api.PATCH('/api/v1/students/{student_id}/billing/charges/{charge_id}', {
      params: { path: { student_id: studentId, charge_id: chargeId } },
      body: payload,
    }),
  )
}

export function waiveCharge(studentId: string, chargeId: string) {
  return unwrap(
    api.POST(
      '/api/v1/students/{student_id}/billing/charges/{charge_id}/waive',
      { params: { path: { student_id: studentId, charge_id: chargeId } } },
    ),
  )
}

export function unwaiveCharge(studentId: string, chargeId: string) {
  return unwrap(
    api.DELETE(
      '/api/v1/students/{student_id}/billing/charges/{charge_id}/waive',
      { params: { path: { student_id: studentId, charge_id: chargeId } } },
    ),
  )
}

// Como a baixa vai ser abatida (não grava nada)
export function previewPayment(
  studentId: string,
  amount: string,
  signal?: AbortSignal,
) {
  return unwrap(
    api.POST('/api/v1/students/{student_id}/billing/payments/preview', {
      params: { path: { student_id: studentId } },
      body: { amount },
      signal,
    }),
  )
}

export function createPayment(
  studentId: string,
  payload: CreatePaymentPayload,
) {
  return unwrap(
    api.POST('/api/v1/students/{student_id}/billing/payments', {
      params: { path: { student_id: studentId } },
      body: payload,
    }),
  )
}

export function deletePayment(studentId: string, paymentId: string) {
  return unwrap(
    api.DELETE('/api/v1/students/{student_id}/billing/payments/{payment_id}', {
      params: { path: { student_id: studentId, payment_id: paymentId } },
    }),
  )
}

// ---------- Página Mensalidades ----------
export function getBillingOverview(
  filters: OverviewFilters,
  signal?: AbortSignal,
) {
  return unwrap(
    api.GET('/api/v1/billing/overview', {
      params: {
        query: {
          month: filters.month,
          filter: filters.filter,
          search: filters.search.trim() || undefined,
          page: filters.page,
          page_size: OVERVIEW_PAGE_SIZE,
        },
      },
      signal,
    }),
  )
}

// ---------- Configurações → Cobrança ----------
export function getBillingSettings(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/academy/billing-settings', { signal }))
}

export function saveBillingSettings(payload: BillingSettings) {
  return unwrap(
    api.PUT('/api/v1/academy/billing-settings', { body: payload }),
  )
}

// Baixa em lote: um pagamento por aluno, com o valor da linha (tudo ou nada)
export function createBulkPayments(body: BulkPaymentPayload) {
  return unwrap(api.POST('/api/v1/billing/bulk-payments', { body }))
}
