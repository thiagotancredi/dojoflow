import { AlertCircle, ArrowLeft, CalendarDays, Check } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'

import { BottomSheet, SheetBlock, SheetRow } from '@/components/BottomSheet'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import type { Charge, Payment } from '@/features/billing/api'
import { ChargeStatusChip } from '@/features/billing/components/ChargeStatusChip'
import { EditChargeDialog } from '@/features/billing/components/EditChargeDialog'
import { HistoryList, Title } from '@/features/billing/components/finance/HistoryList'
import { chargeActions, chargeDetail } from '@/features/billing/history'
import type { ChargeHandlers } from '@/features/billing/history'
import { MoneyTile } from '@/features/billing/components/finance/MoneyTile'
import { LaunchPastChargeDialog } from '@/features/billing/components/LaunchPastChargeDialog'
import {
  useDeletePayment,
  useSetChargeWaived,
  useStudentBilling,
} from '@/features/billing/hooks'
import { chargeTitle, paymentsByCharge } from '@/features/billing/statement'
import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import { AddCard } from '@/features/students/components/tabs/TabParts'
import { useStudent } from '@/features/students/hooks'
import { showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type Scope = 'all' | 'monthly' | 'graduation'

const SCOPES: { value: Scope; label: string }[] = [
  { value: 'all', label: 'Tudo' },
  { value: 'monthly', label: 'Mensalidades' },
  { value: 'graduation', label: 'Graduações' },
]

const isOpen = (charge: Charge) => charge.status !== 'paid' && charge.status !== 'waived'

// Financeiro → histórico de um aluno: todas as mensalidades e graduações,
// com editar, isentar, excluir pagamento e lançar mês anterior
export function StudentHistoryPage() {
  const { studentId = '' } = useParams()
  const student = useStudent(studentId)
  const billing = useStudentBilling(studentId)
  const waive = useSetChargeWaived(studentId)
  const removePayment = useDeletePayment(studentId)
  const [scope, setScope] = useState<Scope>('all')
  const [editing, setEditing] = useState<Charge | null>(null)
  const [removing, setRemoving] = useState<Payment | null>(null)
  const [launching, setLaunching] = useState(false)
  const [detail, setDetail] = useState<Charge | null>(null)

  const detailData = student.data
  const data = billing.data

  if (!detailData || !data) {
    return (
      <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
        {student.error || billing.error ? (
          <div className="space-y-3">
            <p role="alert" className="text-destructive">
              Não foi possível carregar o histórico.
            </p>
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => {
                student.refetch()
                billing.refetch()
              }}
            >
              Tentar de novo
            </Button>
          </div>
        ) : (
          'Carregando…'
        )}
      </div>
    )
  }

  const year = String(new Date().getFullYear())
  const open = data.charges.filter(isOpen)
  const openTotal = open.reduce(
    (sum, charge) => sum + Number(charge.amount) - Number(charge.paid),
    0,
  )
  const paidThisYear = data.payments
    .filter((payment) => payment.paid_on.startsWith(year))
    .reduce((sum, payment) => sum + Number(payment.amount), 0)
  const active = detailData.enrollments
    .filter((item) => item.status === 'active')
    .sort((a, b) => a.modality_name.localeCompare(b.modality_name))
  const charging = active.find(
    (item) => !item.is_exempt && item.due_day !== null && item.monthly_fee !== null,
  )
  const counts: Record<Scope, number> = {
    all: data.charges.length,
    monthly: data.charges.filter((charge) => charge.kind !== 'graduation').length,
    graduation: data.charges.filter((charge) => charge.kind === 'graduation').length,
  }
  const shown = data.charges.filter((charge) =>
    scope === 'all'
      ? true
      : scope === 'graduation'
        ? charge.kind === 'graduation'
        : charge.kind !== 'graduation',
  )
  const byCharge = paymentsByCharge(data.payments)

  async function setWaived(charge: Charge, waived: boolean) {
    try {
      await waive.mutate(charge.id, waived)
      toast.success(waived ? 'Cobrança isenta' : 'Isenção desfeita')
      billing.refetch()
    } catch (caught) {
      showApiError(caught)
    }
  }

  async function confirmRemove() {
    if (!removing) return
    try {
      await removePayment.mutate(removing.id)
      toast.success('Pagamento excluído')
      billing.refetch()
    } catch (caught) {
      showApiError(caught)
    } finally {
      setRemoving(null)
    }
  }

  const handlers: ChargeHandlers = {
    busy: waive.isPending,
    onWaive: (charge, waived) => void setWaived(charge, waived),
    onEdit: setEditing,
    onRemovePayment: setRemoving,
  }

  return (
    <div className="space-y-4">
      <Link
        to="/app/financeiro"
        className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Financeiro
      </Link>

      <header className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <StudentAvatar size="lg" />
          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold tracking-tight md:text-2xl">
              {detailData.student.name}
            </h1>
            <p className="truncate text-sm text-muted-foreground">
              Histórico de pagamentos
              {active.length > 0 && ` · ${active.map((item) => item.modality_name).join(' · ')}`}
            </p>
          </div>
        </div>
        <Button asChild variant="outline" className="shrink-0 rounded-full">
          <Link to={`/app/alunos/${studentId}`}>Ver ficha</Link>
        </Button>
      </header>

      {/* Computador: 3 números */}
      <div
        className={cn(
          'hidden gap-3 md:grid',
          charging ? 'md:grid-cols-3' : 'md:grid-cols-2',
        )}
      >
        <MoneyTile
          label="Em aberto"
          detail={`${open.length} ${open.length === 1 ? 'cobrança' : 'cobranças'}`}
          value={openTotal.toFixed(2)}
          tone="warning"
          icon={<AlertCircle className="size-5" />}
        />
        <MoneyTile
          label={`Pago em ${year}`}
          value={paidThisYear.toFixed(2)}
          icon={<Check className="size-5" />}
        />
        {charging && (
          <MoneyTile
            label={`Vencimento da mensalidade · ${formatMoney(charging.monthly_fee)}`}
            text={`Dia ${charging.due_day}`}
            icon={<CalendarDays className="size-5" />}
          />
        )}
      </div>

      {/* Celular: lista de valores */}
      <section className="flex flex-col divide-y rounded-3xl bg-card px-4 py-2 md:hidden">
        <div className="flex items-baseline justify-between gap-3 py-2 text-sm">
          <span className="text-muted-foreground">Em aberto</span>
          <span className="font-semibold text-status-pending">
            {formatMoney(openTotal.toFixed(2))}
          </span>
        </div>
        <div className="flex items-baseline justify-between gap-3 py-2 text-sm">
          <span className="text-muted-foreground">Pago em {year}</span>
          <span className="font-semibold">{formatMoney(paidThisYear.toFixed(2))}</span>
        </div>
      </section>

      <section className="space-y-3 rounded-3xl bg-card p-4 md:p-5">
        <div className="flex gap-1.5 overflow-x-auto">
          {SCOPES.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={scope === item.value}
              onClick={() => setScope(item.value)}
              className={cn(
                'shrink-0 rounded-full border px-3 py-1 text-xs',
                scope === item.value
                  ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                  : 'text-muted-foreground',
              )}
            >
              {item.label} <span className="ml-0.5 opacity-70">{counts[item.value]}</span>
            </button>
          ))}
        </div>

        {shown.length === 0 ? (
          <p className="py-4 text-sm text-muted-foreground">
            Nenhuma cobrança ainda. A primeira mensalidade aparece no mês seguinte à
            matrícula.
          </p>
        ) : (
          <HistoryList
            charges={shown}
            byCharge={byCharge}
            handlers={handlers}
            onOpen={setDetail}
          />
        )}

        {detailData.enrollments.length > 0 && scope !== 'graduation' && (
          <AddCard
            label="Lançar mês anterior"
            onClick={() => setLaunching(true)}
            className="h-14"
          />
        )}
      </section>

      {detail && (
        <ChargeSheet
          charge={detail}
          payments={byCharge.get(detail.id) ?? []}
          handlers={handlers}
          onClose={() => setDetail(null)}
        />
      )}
      <LaunchPastChargeDialog
        studentId={studentId}
        enrollments={detailData.enrollments}
        open={launching}
        onOpenChange={setLaunching}
        onDone={billing.refetch}
      />
      <EditChargeDialog
        studentId={studentId}
        charge={editing}
        title={editing ? chargeTitle(editing) : ''}
        onClose={() => setEditing(null)}
        onDone={billing.refetch}
      />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(value) => !value && setRemoving(null)}
        title={
          removing
            ? `Excluir o pagamento de ${formatMoney(removing.amount)} de ${formatDate(removing.paid_on)}?`
            : 'Excluir este pagamento?'
        }
        description={removing ? removeDescription(removing, data.charges) : ''}
        confirmLabel="Excluir pagamento"
        onConfirm={() => void confirmRemove()}
      />
    </div>
  )
}

// Celular: tocar numa cobrança abre o painel com os números e as ações
function ChargeSheet({
  charge,
  payments,
  handlers,
  onClose,
}: {
  charge: Charge
  payments: Parameters<typeof chargeActions>[1]
  handlers: ChargeHandlers
  onClose: () => void
}) {
  const actions = chargeActions(charge, payments, handlers)
  const missing = Number(charge.amount) - Number(charge.paid)

  return (
    <BottomSheet title={chargeTitle(charge)} subtitle={chargeDetail(charge, payments)} onClose={onClose}>
      <SheetBlock title={charge.kind === 'graduation' ? 'Graduação' : 'Cobrança'}>
        {charge.kind === 'graduation' && (
          <SheetRow label="Faixa">
            <Title charge={charge} short />
          </SheetRow>
        )}
        <SheetRow label="Valor">{formatMoney(charge.amount)}</SheetRow>
        <SheetRow label="Pago">{formatMoney(charge.paid)}</SheetRow>
        {isOpen(charge) && (
          <SheetRow label="Falta">
            <span className="font-semibold text-status-pending">
              {formatMoney(missing.toFixed(2))}
            </span>
          </SheetRow>
        )}
        <SheetRow label="Situação">
          <ChargeStatusChip status={charge.status} />
        </SheetRow>
      </SheetBlock>
      {actions.length > 0 && (
        <div className="grid gap-2">
          {actions.map((action) => (
            <Button
              key={action.key}
              variant="outline"
              className={cn(
                'h-11 rounded-full',
                action.destructive && 'text-destructive hover:text-destructive',
              )}
              onClick={() => {
                onClose()
                action.run()
              }}
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </BottomSheet>
  )
}

// Quando um pagamento quitou mais de uma cobrança, avisa todas
function removeDescription(payment: Payment, charges: Charge[]) {
  const back = 'As cobranças voltam ao saldo que tinham antes dele.'
  if (payment.allocations.length < 2) return back

  const parts = payment.allocations.map((allocation) => {
    const charge = charges.find((item) => item.id === allocation.charge_id)
    const title = charge ? chargeTitle(charge) : allocation.label
    return `${title} (${formatMoney(allocation.amount)})`
  })
  return `Este pagamento foi dividido entre: ${parts.join(', ')}. ${back}`
}
