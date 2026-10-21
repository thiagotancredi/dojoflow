import { AlertCircle, CalendarClock, HandCoins, Search, Wallet } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { OVERVIEW_PAGE_SIZE } from '@/features/billing/api'
import type {
  BillingOverviewItem,
  OverviewFilter,
  OverviewFilters,
} from '@/features/billing/api'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import { useBillingOverview } from '@/features/billing/hooks'
import { currentMonth } from '@/features/billing/labels'
import { useDebouncedValue } from '@/lib/hooks/useDebouncedValue'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

// Filtro na URL (em português) ↔ filtro da API
const FILTERS: { param: string; value: OverviewFilter; label: string }[] = [
  { param: 'atrasadas', value: 'overdue', label: 'Atrasadas' },
  { param: 'a-vencer', value: 'upcoming', label: 'A vencer' },
  { param: 'pagas', value: 'paid', label: 'Pagas' },
  { param: 'todas', value: 'all', label: 'Todas' },
]

// ?mes=2026-10&filtro=a-vencer&busca=ana&pagina=2 → filtros da consulta
function readFilters(params: URLSearchParams): OverviewFilters {
  const month = params.get('mes') ?? ''
  const filter = FILTERS.find((item) => item.param === params.get('filtro'))
  const page = Number(params.get('pagina'))

  return {
    month: /^\d{4}-(0[1-9]|1[0-2])$/.test(month) ? month : currentMonth(),
    filter: filter?.value ?? 'overdue',
    search: params.get('busca') ?? '',
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  }
}

// Página "Mensalidades": números do mês, quem deve, WhatsApp e baixa
export function BillingPage() {
  const [params, setParams] = useSearchParams()
  const filters = readFilters(params)
  const overview = useBillingOverview(filters)
  const [paying, setPaying] = useState<BillingOverviewItem | null>(null)

  // O campo de busca muda na hora; a URL (e a consulta) só 300 ms depois
  const [searchText, setSearchText] = useState(filters.search)
  const debouncedSearch = useDebouncedValue(searchText)

  // Muda um filtro na URL; qualquer filtro novo volta para a página 1
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

  useEffect(() => {
    if (debouncedSearch.trim() !== filters.search.trim()) {
      updateParams({ busca: debouncedSearch.trim() || null })
    }
    // Só reage à busca já "parada"; o resto dos filtros vem da URL
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  const data = overview.data
  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / OVERVIEW_PAGE_SIZE))
    : 1

  return (
    <div className="space-y-4">
      <PageHeader
        title="Mensalidades"
        actions={
          <Input
            type="month"
            aria-label="Mês"
            value={filters.month}
            onChange={(event) =>
              event.target.value &&
              updateParams({
                mes:
                  event.target.value === currentMonth()
                    ? null
                    : event.target.value,
              })
            }
            className="w-auto rounded-full"
          />
        }
      />

      {/* Números do mês */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MoneyTile
          label="Previsto no mês"
          value={data?.month_expected}
          icon={<Wallet className="size-5" />}
        />
        <MoneyTile
          label="Recebido no mês"
          value={data?.month_received}
          icon={<HandCoins className="size-5" />}
        />
        <MoneyTile
          label="Em atraso (todos os meses)"
          value={data?.overdue_total}
          detail={data ? studentsCount(data.overdue_students) : undefined}
          tone="critical"
          icon={<AlertCircle className="size-5" />}
        />
        <MoneyTile
          label="Vencem em 7 dias"
          value={data?.due_soon_total}
          detail={data ? studentsCount(data.due_soon_students) : undefined}
          tone="warning"
          icon={<CalendarClock className="size-5" />}
        />
      </div>

      <section className="space-y-3 rounded-3xl bg-card p-4 md:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() =>
                  updateParams({
                    filtro: item.value === 'overdue' ? null : item.param,
                  })
                }
                className={cn(
                  'shrink-0 rounded-full border px-3 py-1 text-xs',
                  filters.filter === item.value
                    ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                    : 'text-muted-foreground',
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="relative min-w-0 flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              aria-label="Buscar aluno"
              placeholder="Buscar aluno"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              className="rounded-full pl-9"
            />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {filters.filter === 'overdue'
            ? 'Atrasadas mostra todos os meses, não só o escolhido.'
            : 'Cobranças do mês escolhido.'}
        </p>

        <OverviewList
          state={overview}
          filters={filters}
          onPay={setPaying}
          onRetry={overview.refetch}
        />

        {data && data.total > 0 && (
          <div className="flex items-center justify-between gap-2 pt-1 text-xs text-muted-foreground">
            <Button
              variant="outline"
              size="sm"
              className="rounded-full"
              disabled={filters.page <= 1}
              onClick={() =>
                updateParams({
                  pagina: String(Math.min(filters.page - 1, totalPages)),
                })
              }
            >
              Anterior
            </Button>
            <span>
              Página {Math.min(filters.page, totalPages)} de {totalPages} ·{' '}
              {studentsCount(data.total)}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="rounded-full"
              disabled={filters.page >= totalPages}
              onClick={() => updateParams({ pagina: String(filters.page + 1) })}
            >
              Próxima
            </Button>
          </div>
        )}
      </section>

      <PaymentDialog
        studentId={paying?.student_id ?? ''}
        studentName={paying?.name ?? ''}
        open={paying !== null}
        onOpenChange={(open) => !open && setPaying(null)}
        onDone={overview.refetch}
      />
    </div>
  )
}

function studentsCount(count: number) {
  return `${count} ${count === 1 ? 'aluno' : 'alunos'}`
}

const toneClasses = {
  default: 'bg-accent text-primary',
  critical: 'bg-status-critical-soft text-status-critical',
  warning: 'bg-status-warning-soft text-status-warning',
}

function MoneyTile({
  label,
  value,
  detail,
  icon,
  tone = 'default',
}: {
  label: string
  value: string | undefined
  detail?: string
  icon: ReactNode
  tone?: keyof typeof toneClasses
}) {
  return (
    <div className="flex items-center gap-3 rounded-3xl bg-card p-4">
      <div
        className={cn(
          'hidden size-11 shrink-0 place-items-center rounded-2xl sm:grid',
          toneClasses[tone],
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xl leading-none font-semibold">
          {value === undefined ? '—' : formatMoney(value)}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {label}
          {detail && ` · ${detail}`}
        </p>
      </div>
    </div>
  )
}

function OverviewList({
  state,
  filters,
  onPay,
  onRetry,
}: {
  state: ReturnType<typeof useBillingOverview>
  filters: OverviewFilters
  onPay: (item: BillingOverviewItem) => void
  onRetry: () => void
}) {
  if (state.isLoading && !state.data) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        Carregando…
      </p>
    )
  }

  if (!state.data) {
    return (
      <div className="space-y-3 py-6 text-center text-sm">
        <p role="alert" className="text-destructive">
          Não foi possível carregar as mensalidades.
        </p>
        <Button variant="outline" className="rounded-full" onClick={onRetry}>
          Tentar de novo
        </Button>
      </div>
    )
  }

  const { items } = state.data

  if (items.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        {filters.filter === 'overdue' && !filters.search
          ? 'Ninguém em atraso 🎉'
          : 'Nenhuma mensalidade neste filtro'}
      </p>
    )
  }

  return (
    <>
      {/* Computador: tabela */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Aluno</th>
              <th className="py-2 pr-3 font-medium">Modalidades</th>
              <th className="py-2 pr-3 font-medium">Em aberto</th>
              <th className="py-2 pr-3 font-medium">Atraso</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.student_id} className="border-b last:border-0">
                <td className="py-2 pr-3">
                  <StudentName item={item} />
                </td>
                <td className="py-2 pr-3">{item.modalities.join(' · ')}</td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  {formatMoney(item.open_amount)}
                </td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  <DaysLate days={item.days_late} />
                </td>
                <td className="py-2">
                  <RowActions item={item} onPay={onPay} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Celular: um cartão por aluno */}
      <ul className="space-y-2 md:hidden">
        {items.map((item) => (
          <li key={item.student_id} className="space-y-2 rounded-2xl border p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <StudentName item={item} />
                <p className="text-xs text-muted-foreground">
                  {item.modalities.join(' · ')}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold whitespace-nowrap">
                  {formatMoney(item.open_amount)}
                </p>
                <p className="text-xs">
                  <DaysLate days={item.days_late} />
                </p>
              </div>
            </div>
            <RowActions item={item} onPay={onPay} />
          </li>
        ))}
      </ul>
    </>
  )
}

function StudentName({ item }: { item: BillingOverviewItem }) {
  // Em atraso e sem link: o aluno (ou responsável) não tem telefone
  const noPhone = item.days_late !== null && !item.whatsapp_url

  return (
    <p className="min-w-0">
      <Link
        to={`/app/alunos/${item.student_id}`}
        state={{ tab: 'billing' }}
        className="font-medium hover:underline"
      >
        {item.name}
      </Link>
      {item.responsible_name && (
        <span className="text-xs text-muted-foreground">
          {' '}
          · resp. {item.responsible_name.split(' ')[0]}
        </span>
      )}
      {noPhone && (
        <span className="text-xs text-muted-foreground"> · sem telefone</span>
      )}
    </p>
  )
}

function DaysLate({ days }: { days: number | null }) {
  if (days === null) return <span className="text-muted-foreground">—</span>

  return (
    <span className="text-status-critical">
      {days} {days === 1 ? 'dia' : 'dias'}
    </span>
  )
}

function RowActions({
  item,
  onPay,
}: {
  item: BillingOverviewItem
  onPay: (item: BillingOverviewItem) => void
}) {
  return (
    <div className="flex justify-end gap-2">
      <WhatsAppButton
        url={item.whatsapp_url}
        studentName={item.name}
        responsibleName={item.responsible_name}
        size="sm"
      />
      <Button
        size="sm"
        className="rounded-full"
        disabled={Number(item.open_amount) <= 0}
        onClick={() => onPay(item)}
      >
        Dar baixa
      </Button>
    </div>
  )
}
