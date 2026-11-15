import { useSearchParams } from 'react-router'

import type { OverviewFilter, OverviewFilters } from '@/features/billing/api'
import { currentMonth } from '@/features/billing/labels'

// Filtro na URL (em português) ↔ filtro da API, na ordem da tela.
// A tela abre em "A vencer".
export const FILTERS: { param: string; value: OverviewFilter; label: string }[] = [
  { param: 'a-vencer', value: 'upcoming', label: 'A vencer' },
  { param: 'atrasadas', value: 'overdue', label: 'Atrasadas' },
  { param: 'pagas', value: 'paid', label: 'Pagas' },
  { param: 'todas', value: 'all', label: 'Todas' },
]
export const DEFAULT_FILTER: OverviewFilter = 'upcoming'

export type FinanceTab = 'monthly' | 'graduation'

// ?aba=graduacao&mes=2026-10&filtro=atrasadas&busca=ana&pagina=2
export function readFilters(params: URLSearchParams): OverviewFilters {
  const month = params.get('mes') ?? ''
  const filter = FILTERS.find((item) => item.param === params.get('filtro'))
  const page = Number(params.get('pagina'))

  return {
    month: /^\d{4}-(0[1-9]|1[0-2])$/.test(month) ? month : currentMonth(),
    filter: filter?.value ?? DEFAULT_FILTER,
    search: params.get('busca') ?? '',
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  }
}

// Filtros do Financeiro guardados na URL (o F5 e o "voltar" mantêm a tela)
export function useFinanceParams() {
  const [params, setParams] = useSearchParams()
  const tab: FinanceTab = params.get('aba') === 'graduacao' ? 'graduation' : 'monthly'

  // Muda filtros na URL; qualquer filtro novo volta para a página 1
  function updateParams(changes: Record<string, string | null>) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const [name, value] of Object.entries(changes)) {
          if (value) next.set(name, value)
          else next.delete(name)
        }
        if (!('pagina' in changes)) next.delete('pagina')
        return next
      },
      { replace: true },
    )
  }

  return {
    params,
    tab,
    filters: readFilters(params),
    updateParams,
    // A chave da lista: mudou a URL, a seleção da baixa em lote some
    listKey: params.toString(),
  }
}
