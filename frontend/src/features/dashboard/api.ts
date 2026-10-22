import { api, unwrap } from '@/lib/api/client'
import type { Schemas } from '@/lib/api/client'
import { useResource } from '@/lib/hooks/useResource'

export type DashboardSummary = Schemas['DashboardSummaryRead']

// Resumo do dashboard: financeiro, alunos (modalidades, faixa etária,
// aniversariantes) e novos alunos por mês
export function getDashboardSummary(signal?: AbortSignal) {
  return unwrap(api.GET('/api/v1/dashboard/summary', { signal }))
}

export function useDashboardSummary() {
  return useResource('dashboard-summary', (signal) =>
    getDashboardSummary(signal),
  )
}
