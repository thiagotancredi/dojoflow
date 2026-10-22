import { ChevronDown, ChevronRight, Ellipsis } from 'lucide-react'
import { Fragment, useState } from 'react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { Charge, Payment } from '@/features/billing/api'
import { ChargeStatusChip } from '@/features/billing/components/ChargeStatusChip'
import {
  PAYMENT_METHOD_LABELS,
  formatDayMonth,
  formatMonth,
} from '@/features/billing/labels'
import { chargeTitle, paymentsByCharge } from '@/features/billing/statement'
import type { ChargePayment } from '@/features/billing/statement'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type StatementProps = {
  charges: Charge[]
  payments: Payment[]
  busy: boolean
  onWaive: (charge: Charge, waived: boolean) => void
  onEdit: (charge: Charge) => void
  onRemovePayment: (payment: Payment) => void
}

// Extrato da aba Mensalidades: uma linha por mensalidade (mais nova em
// cima), com quanto foi pago, quando e quanto falta. Clicar na linha
// mostra os pagamentos dela.
export function ChargeStatement(props: StatementProps) {
  const byCharge = paymentsByCharge(props.payments)
  const [expanded, setExpanded] = useState<string | null>(null)
  const toggle = (id: string) =>
    setExpanded((current) => (current === id ? null : id))

  return (
    <>
      {/* Computador: tabela */}
      <div className="hidden md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">Mês</th>
              <th className="py-2 pr-3 font-medium">Modalidade</th>
              <th className="py-2 pr-3 font-medium">Vence</th>
              <th className="py-2 pr-3 font-medium">Mensalidade</th>
              <th className="py-2 pr-3 font-medium">Total pago</th>
              <th className="py-2 pr-3 font-medium">Pagamento</th>
              <th className="py-2 pr-3 font-medium">Situação</th>
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {props.charges.map((charge) => {
              const payments = byCharge.get(charge.id) ?? []
              const expandable = hasMoreToShow(payments)
              const open = expandable && expanded === charge.id
              return (
                <Fragment key={charge.id}>
                  <tr
                    className={cn(
                      'border-b',
                      expandable && 'cursor-pointer hover:bg-accent/50',
                      open && 'border-b-0',
                    )}
                    onClick={() => expandable && toggle(charge.id)}
                  >
                    <td className="py-2.5 pr-3 whitespace-nowrap">
                      <MonthCell charge={charge} hasPayments={expandable} open={open} />
                    </td>
                    <td className="py-2.5 pr-3">
                      <ModalityCell charge={charge} />
                    </td>
                    <td
                      className="py-2.5 pr-3"
                      title={formatDate(charge.due_date)}
                    >
                      {formatDayMonth(charge.due_date)}
                    </td>
                    <td className="py-2.5 pr-3 whitespace-nowrap">
                      {formatMoney(charge.amount)}
                    </td>
                    <td className="py-2.5 pr-3">
                      <PaidCell charge={charge} />
                    </td>
                    <td className="py-2.5 pr-3">
                      <PaymentCell payments={payments} />
                    </td>
                    <td className="py-2.5 pr-3">
                      <ChargeStatusChip
                        status={charge.status}
                        paid={Number(charge.paid)}
                      />
                    </td>
                    <td
                      className="py-2.5 text-right"
                      // O menu não abre/fecha a linha
                      onClick={(event) => event.stopPropagation()}
                    >
                      <ChargeMenu
                        charge={charge}
                        chargePayments={payments}
                        busy={props.busy}
                        onWaive={props.onWaive}
                        onEdit={props.onEdit}
                        onRemovePayment={props.onRemovePayment}
                      />
                    </td>
                  </tr>
                  {open && (
                    <tr className="border-b">
                      <td />
                      <td colSpan={7} className="pb-3">
                        <PaymentList payments={payments} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Celular: um bloco por mensalidade */}
      <ul className="divide-y md:hidden">
        {props.charges.map((charge) => {
          const payments = byCharge.get(charge.id) ?? []
          const expandable = hasMoreToShow(payments)
          const open = expandable && expanded === charge.id
          return (
            <li key={charge.id} className="space-y-2 py-3">
              <div className="flex items-start justify-between gap-2">
                <button
                  type="button"
                  className="min-w-0 text-left text-sm"
                  disabled={!expandable}
                  onClick={() => toggle(charge.id)}
                >
                  <MonthCell charge={charge} hasPayments={expandable} open={open} />
                  <span className="block text-xs text-muted-foreground">
                    <ModalityCell charge={charge} inline /> · vence{' '}
                    {formatDayMonth(charge.due_date)}
                  </span>
                </button>
                <div className="flex items-center gap-1">
                  <ChargeStatusChip
                    status={charge.status}
                    paid={Number(charge.paid)}
                  />
                  <ChargeMenu
                        charge={charge}
                        chargePayments={payments}
                        busy={props.busy}
                        onWaive={props.onWaive}
                        onEdit={props.onEdit}
                        onRemovePayment={props.onRemovePayment}
                      />
                </div>
              </div>
              <div className="flex items-start justify-between gap-3 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground">
                    Mensalidade{' '}
                  </span>
                  {formatMoney(charge.amount)}
                </div>
                <PaidCell charge={charge} />
              </div>
              {payments.length > 0 && (
                <div className="text-xs text-muted-foreground">
                  <PaymentCell payments={payments} inline />
                </div>
              )}
              {open && <PaymentList payments={payments} />}
            </li>
          )
        })}
      </ul>
    </>
  )
}

// Abrir a linha só mostra algo novo com 2+ pagamentos, pagamento dividido
// com outra mensalidade ou observação; senão repetiria a própria linha
function hasMoreToShow(payments: ChargePayment[]) {
  return (
    payments.length > 1 ||
    payments.some(
      ({ payment, amount }) =>
        Number(payment.amount) > Number(amount) || Boolean(payment.notes),
    )
  )
}

function MonthCell({
  charge,
  hasPayments,
  open,
}: {
  charge: Charge
  hasPayments: boolean
  open: boolean
}) {
  const Icon = open ? ChevronDown : ChevronRight
  return (
    <span className="inline-flex items-center gap-1 font-medium">
      {/* A setinha só aparece quando há pagamentos para mostrar */}
      <Icon
        className={cn(
          'size-3.5 text-muted-foreground',
          !hasPayments && 'invisible',
        )}
      />
      {formatMonth(charge.reference_month)}
    </span>
  )
}

function ModalityCell({ charge, inline }: { charge: Charge; inline?: boolean }) {
  if (charge.kind !== 'enrollment_fee') return <>{charge.modality_name}</>
  if (inline) return <>Taxa de matrícula · {charge.modality_name}</>
  return (
    <>
      Taxa de matrícula
      <span className="block text-xs text-muted-foreground">
        {charge.modality_name}
      </span>
    </>
  )
}

// Total pago: o valor, ou "R$ 100 de R$ 140" + barrinha + "Falta R$ 40"
function PaidCell({ charge }: { charge: Charge }) {
  const amount = Number(charge.amount)
  const paid = Number(charge.paid)
  const missing = (amount - paid).toFixed(2)
  const late = charge.status === 'overdue'

  if (charge.status === 'waived') {
    return <span className="text-muted-foreground">—</span>
  }
  if (paid >= amount) return <span>{formatMoney(charge.paid)}</span>

  const falta = (
    <p
      className={cn(
        'text-xs font-semibold',
        late ? 'text-status-critical' : 'text-status-warning',
      )}
    >
      Falta {formatMoney(missing)}
    </p>
  )

  if (paid === 0) {
    return late ? (
      <div>
        <span className="text-muted-foreground">—</span>
        {falta}
      </div>
    ) : (
      <span className="text-muted-foreground">—</span>
    )
  }

  return (
    <div className="space-y-1">
      <p className="whitespace-nowrap">
        {formatMoney(charge.paid)}{' '}
        <span className="text-muted-foreground">
          de {formatMoney(charge.amount)}
        </span>
      </p>
      <div className="h-1.5 w-28 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            'h-full rounded-full',
            late ? 'bg-status-critical' : 'bg-status-warning',
          )}
          style={{ width: `${(paid / amount) * 100}%` }}
        />
      </div>
      {falta}
    </div>
  )
}

function methodLabel(payment: Payment) {
  return payment.method ? PAYMENT_METHOD_LABELS[payment.method] : null
}

// Data do último pagamento + forma (ou "N pagamentos")
function PaymentCell({
  payments,
  inline,
}: {
  payments: ChargePayment[]
  inline?: boolean
}) {
  if (payments.length === 0) {
    return inline ? null : <span className="text-muted-foreground">—</span>
  }

  const [last] = payments
  const sub =
    payments.length > 1 ? `${payments.length} pagamentos` : methodLabel(last.payment)

  if (inline) {
    return (
      <>
        Pago em {formatDate(last.payment.paid_on)}
        {sub && ` · ${sub}`}
      </>
    )
  }

  return (
    <div>
      <p className="whitespace-nowrap">{formatDate(last.payment.paid_on)}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}

// Lista aberta ao clicar: cada pagamento que caiu nesta mensalidade
function PaymentList({ payments }: { payments: ChargePayment[] }) {
  return (
    <ul className="max-w-xl space-y-1 rounded-xl bg-muted px-3 py-2 text-xs">
      {payments.map(({ payment, amount }) => (
        <li key={payment.id} className="space-y-0.5">
          <div className="flex justify-between gap-3">
            <span>
              {formatDate(payment.paid_on)}
              {methodLabel(payment) && ` · ${methodLabel(payment)}`}
            </span>
            <span className="font-semibold">{formatMoney(amount)}</span>
          </div>
          {Number(payment.amount) > Number(amount) && (
            <p className="text-muted-foreground">
              Parte de um pagamento de {formatMoney(payment.amount)}
            </p>
          )}
          {payment.notes && (
            <p className="text-muted-foreground">{payment.notes}</p>
          )}
        </li>
      ))}
    </ul>
  )
}

function ChargeMenu({
  charge,
  chargePayments: payments,
  busy,
  onWaive,
  onEdit,
  onRemovePayment,
}: Omit<StatementProps, 'charges' | 'payments'> & {
  charge: Charge
  chargePayments: ChargePayment[]
}) {
  // Com pagamento, a cobrança não muda (exclua o pagamento antes)
  const canChange = Number(charge.paid) === 0
  const items: ReactNode[] = []

  if (canChange && charge.status === 'waived') {
    items.push(
      <DropdownMenuItem key="unwaive" onSelect={() => onWaive(charge, false)}>
        Desfazer isenção
      </DropdownMenuItem>,
    )
  } else if (canChange) {
    items.push(
      <DropdownMenuItem key="edit" onSelect={() => onEdit(charge)}>
        Editar valor ou vencimento
      </DropdownMenuItem>,
      <DropdownMenuItem key="waive" onSelect={() => onWaive(charge, true)}>
        Isentar este mês
      </DropdownMenuItem>,
    )
  }

  if (payments.length > 0 && items.length > 0) {
    items.push(<DropdownMenuSeparator key="sep" />)
  }
  for (const { payment } of payments) {
    items.push(
      <DropdownMenuItem
        key={payment.id}
        variant="destructive"
        onSelect={() => onRemovePayment(payment)}
      >
        Excluir pagamento de {formatDate(payment.paid_on)}
      </DropdownMenuItem>,
    )
  }

  if (items.length === 0) return null

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          disabled={busy}
          aria-label={`Opções de ${chargeTitle(charge)}`}
          className="size-8 rounded-full"
        >
          <Ellipsis />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">{items}</DropdownMenuContent>
    </DropdownMenu>
  )
}
