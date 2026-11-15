import { AlertCircle, ChevronRight, HandCoins, Pointer, Search, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import { RealIcon } from '@/app/components/RealIcon'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { OVERVIEW_PAGE_SIZE } from '@/features/billing/api'
import type { BillingOverviewItem, OverviewFilters } from '@/features/billing/api'
import { BulkPaymentDialog } from '@/features/billing/components/BulkPaymentDialog'
import { MoneyTile } from '@/features/billing/components/finance/MoneyTile'
import { MonthBlocks } from '@/features/billing/components/finance/MonthBlocks'
import {
  MonthSummarySheet,
  MonthlySheet,
} from '@/features/billing/components/finance/MonthlySheet'
import {
  DEFAULT_FILTER,
  FILTERS,
} from '@/features/billing/components/finance/useFinanceParams'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import {
  WhatsAppButton,
  WhatsAppDialog,
} from '@/features/billing/components/WhatsAppButton'
import type { useBillingOverview } from '@/features/billing/hooks'
import { dueIn, formatDayMonth } from '@/features/billing/labels'
import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import { useDebouncedValue } from '@/lib/hooks/useDebouncedValue'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type OverviewState = ReturnType<typeof useBillingOverview>

// Aba "Mensalidade" do Financeiro: números do mês, os 3 blocos, a lista
// com WhatsApp, Dar baixa e baixa em lote
export function MonthlyTab({
  overview,
  filters,
  listKey,
  updateParams,
}: {
  overview: OverviewState
  filters: OverviewFilters
  listKey: string
  updateParams: (changes: Record<string, string | null>) => void
}) {
  const [paying, setPaying] = useState<BillingOverviewItem | null>(null)
  // Celular: painel do aluno, painel do resumo e a janela do WhatsApp
  const [detail, setDetail] = useState<BillingOverviewItem | null>(null)
  const [whatsAppFor, setWhatsAppFor] = useState<BillingOverviewItem | null>(null)
  const [summaryOpen, setSummaryOpen] = useState(false)
  // Seleção para a baixa em lote. Vale só para os filtros e a página em que
  // foi feita: mudou a lista, a seleção some (nunca dá baixa em quem saiu
  // da tela).
  const [selection, setSelection] = useState<{
    key: string
    items: Map<string, BillingOverviewItem>
  }>({ key: listKey, items: new Map() })
  const selected =
    selection.key === listKey ? selection.items : new Map<string, BillingOverviewItem>()
  const [bulkPaying, setBulkPaying] = useState<BillingOverviewItem[]>([])
  const selectedTotal = [...selected.values()].reduce(
    (sum, item) => sum + Number(item.open_amount),
    0,
  )

  function setSelected(items: Map<string, BillingOverviewItem>) {
    setSelection({ key: listKey, items })
  }

  function toggle(item: BillingOverviewItem) {
    const next = new Map(selected)
    if (next.has(item.student_id)) next.delete(item.student_id)
    else next.set(item.student_id, item)
    setSelected(next)
  }

  // Marca todos os da página que têm algo em aberto (ou desmarca todos)
  function toggleAll(items: BillingOverviewItem[]) {
    const payable = items.filter((item) => Number(item.open_amount) > 0)
    const allOn = payable.every((item) => selected.has(item.student_id))
    setSelected(
      allOn
        ? new Map()
        : new Map(payable.map((item) => [item.student_id, item])),
    )
  }

  // O campo de busca muda na hora; a URL (e a consulta) só 300 ms depois
  const [searchText, setSearchText] = useState(filters.search)
  const debouncedSearch = useDebouncedValue(searchText)

  useEffect(() => {
    if (debouncedSearch.trim() !== filters.search.trim()) {
      updateParams({ busca: debouncedSearch.trim() || null })
    }
    // Só reage à busca já "parada"; o resto dos filtros vem da URL
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  function setFilter(value: (typeof FILTERS)[number]) {
    updateParams({ filtro: value.value === DEFAULT_FILTER ? null : value.param })
  }

  // "Ver todos" de quem deve há mais tempo: filtro Atrasadas e desce até a
  // lista
  function seeAllOverdue() {
    setSummaryOpen(false)
    setFilter(FILTERS.find((item) => item.value === 'overdue')!)
    document.getElementById('lista-mensalidades')?.scrollIntoView({ behavior: 'smooth' })
  }

  const data = overview.data
  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / OVERVIEW_PAGE_SIZE))
    : 1

  return (
    <div className="space-y-4">
      {/* Celular: os números numa lista de valores + "Ver resumo do mês" */}
      <section className="rounded-3xl bg-card p-4 md:hidden">
        <div className="flex flex-col divide-y">
          <SummaryRow label="Previsto no mês" value={data && formatMoney(data.month_expected)} />
          <SummaryRow label="Recebido" value={data && formatMoney(data.month_received)} />
          <SummaryRow
            label="Falta receber"
            value={data && formatMoney(data.month_open_total)}
            className="text-status-pending"
          />
          <SummaryRow
            label="Ainda não pagaram"
            value={data && studentsCount(data.unpaid_students)}
            className="text-status-critical"
          />
        </div>
        <button
          type="button"
          disabled={!data}
          onClick={() => setSummaryOpen(true)}
          className="flex w-full items-center justify-between pt-2 text-sm font-medium text-sidebar-primary"
        >
          Ver resumo do mês <ChevronRight className="size-4" />
        </button>
      </section>

      {/* Computador: números do mês */}
      <div className="hidden grid-cols-2 gap-3 md:grid lg:grid-cols-4">
        <MoneyTile
          label="Previsto no mês"
          value={data?.month_expected}
          icon={<RealIcon className="size-5" />}
        />
        <MoneyTile
          label="Recebido no mês"
          value={data?.month_received}
          icon={<HandCoins className="size-5" />}
        />
        <MoneyTile
          label="Falta receber"
          value={data?.month_open_total}
          tone="warning"
          icon={<AlertCircle className="size-5" />}
        />
        <MoneyTile
          label="Ainda não pagaram"
          text={data ? studentsCount(data.unpaid_students) : '—'}
          tone="critical"
          valueClassName="text-status-critical"
          icon={<Users className="size-5" />}
        />
      </div>

      {data && (
        <MonthBlocks data={data} onSeeAll={seeAllOverdue} className="hidden md:grid" />
      )}

      <section
        id="lista-mensalidades"
        className="scroll-mt-4 space-y-3 rounded-3xl bg-card p-4 md:p-5"
      >
        <div className="flex flex-wrap items-center gap-2">
          <div className="-mx-1 flex max-w-full gap-1.5 overflow-x-auto px-1 md:flex-wrap">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setFilter(item)}
                className={cn(
                  'shrink-0 rounded-full border px-3 py-1 text-xs',
                  filters.filter === item.value
                    ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                    : 'text-muted-foreground',
                )}
              >
                {item.label}
                {data && (
                  <span className="ml-0.5 opacity-70">
                    {' '}
                    {data.filter_counts[item.value] ?? 0}
                  </span>
                )}
              </button>
            ))}
          </div>
          {/* min-w-40: sem espaço ao lado dos filtros, a busca desce para
              uma linha própria em vez de virar só a lupa */}
          <div className="relative min-w-40 flex-1 sm:max-w-xs">
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
        <p className="hidden text-xs text-muted-foreground md:block">
          {filters.filter === 'overdue'
            ? 'Atrasadas mostra todos os meses, não só o escolhido.'
            : 'Cobranças do mês escolhido.'}
        </p>
        <p className="flex items-center gap-1.5 border-b pb-2 text-xs text-muted-foreground md:hidden">
          <Pointer className="size-3.5" /> Toque no aluno para cobrar ou dar baixa.
        </p>

        <OverviewList
          state={overview}
          filters={filters}
          onPay={setPaying}
          onOpen={setDetail}
          onRetry={overview.refetch}
          selected={selected}
          onToggle={toggle}
          onToggleAll={toggleAll}
        />
        {/* Barra da baixa em lote (aparece ao marcar alunos) */}
        {selected.size > 0 && (
          <div className="sticky bottom-24 z-10 hidden flex-wrap md:flex items-center justify-between gap-3 rounded-2xl bg-primary px-4 py-3 text-sm text-primary-foreground shadow-lg md:bottom-4">
            <span>
              <span className="font-semibold">
                {selected.size} {selected.size === 1 ? 'aluno' : 'alunos'}
              </span>{' '}
              · {formatMoney(selectedTotal.toFixed(2))}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="rounded-full text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
                onClick={() => setSelected(new Map())}
              >
                Limpar
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="rounded-full"
                onClick={() => setBulkPaying([...selected.values()])}
              >
                Dar baixa nos selecionados
              </Button>
            </div>
          </div>
        )}

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

      {detail && (
        <MonthlySheet
          item={detail}
          onClose={() => setDetail(null)}
          onWhatsApp={() => {
            setDetail(null)
            setWhatsAppFor(detail)
          }}
          onPay={() => {
            setDetail(null)
            setPaying(detail)
          }}
        />
      )}
      {summaryOpen && data && (
        <MonthSummarySheet
          data={data}
          onClose={() => setSummaryOpen(false)}
          onSeeAll={seeAllOverdue}
        />
      )}
      {whatsAppFor?.whatsapp_url && (
        <WhatsAppDialog
          url={whatsAppFor.whatsapp_url}
          studentName={whatsAppFor.name}
          responsibleName={whatsAppFor.responsible_name}
          open
          onOpenChange={(open) => !open && setWhatsAppFor(null)}
        />
      )}
      <BulkPaymentDialog
        items={bulkPaying}
        onClose={() => setBulkPaying([])}
        onDone={() => {
          setSelected(new Map())
          overview.refetch()
        }}
      />
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

// Linha da lista de valores do celular ("Recebido ...... R$ 2.130,00")
function SummaryRow({
  label,
  value,
  className,
}: {
  label: string
  value: string | undefined | null | false
  className?: string
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn('font-semibold', className)}>{value || '—'}</span>
    </div>
  )
}

function studentsCount(count: number) {
  return `${count} ${count === 1 ? 'aluno' : 'alunos'}`
}

function OverviewList({
  state,
  filters,
  onPay,
  onOpen,
  onRetry,
  selected,
  onToggle,
  onToggleAll,
}: {
  state: OverviewState
  filters: OverviewFilters
  onPay: (item: BillingOverviewItem) => void
  onOpen: (item: BillingOverviewItem) => void
  onRetry: () => void
  selected: Map<string, BillingOverviewItem>
  onToggle: (item: BillingOverviewItem) => void
  onToggleAll: (items: BillingOverviewItem[]) => void
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
  const payable = items.filter((item) => Number(item.open_amount) > 0)
  const selectedHere = payable.filter((item) => selected.has(item.student_id))
  const headerState =
    payable.length > 0 && selectedHere.length === payable.length
      ? true
      : selectedHere.length > 0
        ? 'indeterminate'
        : false

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
              <th className="w-8 py-2 pr-2">
                {payable.length > 0 && (
                  <Checkbox
                    aria-label="Selecionar todos com valor em aberto"
                    checked={headerState}
                    onCheckedChange={() => onToggleAll(items)}
                  />
                )}
              </th>
              <th className="py-2 pr-3 font-medium">Aluno</th>
              <th className="py-2 pr-3 font-medium">Em aberto</th>
              <th className="py-2 pr-3 font-medium">Vencimento</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.student_id} className="border-b last:border-0">
                <td className="py-2 pr-2">
                  <SelectBox item={item} selected={selected} onToggle={onToggle} />
                </td>
                <td className="py-2 pr-3">
                  <div className="flex items-center gap-3">
                    <StudentAvatar />
                    <div className="min-w-0">
                      <StudentName item={item} />
                      <p className="text-xs text-muted-foreground">
                        {item.modalities.join(' · ')}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="py-2 pr-3 font-medium whitespace-nowrap">
                  {formatMoney(item.open_amount)}
                </td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  <DueOrLate item={item} filter={filters.filter} />
                </td>
                <td className="py-2">
                  <RowActions item={item} onPay={onPay} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Celular: linha enxuta por aluno; tocar abre o painel (cobrar,
          dar baixa). A baixa em lote fica só no computador */}
      <ul className="md:hidden">
        {items.map((item) => (
          <li key={item.student_id} className="border-b last:border-0">
            <button
              type="button"
              onClick={() => onOpen(item)}
              className="flex w-full items-center gap-3 py-3 text-left"
            >
              <StudentAvatar />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{item.name}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {item.modalities.join(' · ')}
                  {item.due_date &&
                    Number(item.open_amount) > 0 &&
                    ` · vence ${formatDayMonth(item.due_date)}`}
                </span>
              </span>
              <span className="shrink-0 text-right">
                <span className="block font-semibold">
                  {formatMoney(item.open_amount)}
                </span>
                {item.days_late !== null && filters.filter !== 'upcoming' && (
                  <span className="block text-xs text-status-critical">
                    {item.days_late} {item.days_late === 1 ? 'dia' : 'dias'} de atraso
                  </span>
                )}
              </span>
              <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
            </button>
          </li>
        ))}
      </ul>
    </>
  )
}

function StudentName({ item }: { item: BillingOverviewItem }) {
  // Algo em aberto e sem link: o aluno (ou responsável) não tem telefone
  const noPhone = Number(item.open_amount) > 0 && !item.whatsapp_url

  return (
    <p className="min-w-0">
      <Link
        to={`/app/alunos/${item.student_id}`}
        className="font-medium hover:underline"
      >
        {item.name}
      </Link>
      {/* whitespace-nowrap: "· sem telefone" desce inteiro para a linha de
          baixo, em vez de partir no meio ("sem" / "telefone") */}
      {item.responsible_name && (
        <span className="text-xs whitespace-nowrap text-muted-foreground">
          {' '}
          · resp. {item.responsible_name.split(' ')[0]}
        </span>
      )}
      {noPhone && (
        <span className="text-xs whitespace-nowrap text-muted-foreground">
          {' '}
          · sem telefone
        </span>
      )}
    </p>
  )
}

// Atrasado: "N dias de atraso" em vermelho. Senão (e sempre no filtro
// "A vencer"): "10/11 · em 5 dias"
function DueOrLate({
  item,
  filter,
}: {
  item: BillingOverviewItem
  filter: OverviewFilters['filter']
}) {
  const days = item.days_late
  if (days !== null && filter !== 'upcoming') {
    return (
      <span className="text-status-critical">
        {days} {days === 1 ? 'dia' : 'dias'} de atraso
      </span>
    )
  }
  if (!item.due_date || Number(item.open_amount) <= 0) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <>
      {formatDayMonth(item.due_date)}{' '}
      <span className="text-xs text-muted-foreground">· {dueIn(item.due_date)}</span>
    </>
  )
}

// Caixinha da baixa em lote (só para quem tem algo em aberto)
function SelectBox({
  item,
  selected,
  onToggle,
}: {
  item: BillingOverviewItem
  selected: Map<string, BillingOverviewItem>
  onToggle: (item: BillingOverviewItem) => void
}) {
  if (Number(item.open_amount) <= 0) return <span className="block size-4" />

  return (
    <Checkbox
      aria-label={`Selecionar ${item.name}`}
      checked={selected.has(item.student_id)}
      onCheckedChange={() => onToggle(item)}
      className="mt-0.5"
    />
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
