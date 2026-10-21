import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'
import { useResource } from '@/lib/hooks/useResource'

export type DashboardSummary = Schemas['DashboardSummaryRead']

// Resumo do dashboard (por enquanto a tela usa só inadimplentes e
// vencimentos; o resto ainda vem de mock-data.ts — Fase 10)
export function getDashboardSummary(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/dashboard/summary', { signal }))
}

export function useDashboardSummary() {
  return useResource('dashboard-summary', (signal) =>
    getDashboardSummary(signal),
  )
}
