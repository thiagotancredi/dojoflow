import { Ellipsis } from 'lucide-react'
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
  AutomaticBadge,
  ReceiptLink,
} from '@/features/billing/components/InfinitePayBits'
import { formatMonth } from '@/features/billing/labels'
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

// Extrato da aba Mensalidades, como uma planilha: uma linha por cobrança
// (mais nova em cima) com Mensalidade, Pago, Falta e quando foi pago.
export function ChargeStatement(props: StatementProps) {
  const byCharge = paymentsByCharge(props.payments)

  const menu = (charge: Charge) => (
    <ChargeMenu
      charge={charge}
      chargePayments={byCharge.get(charge.id) ?? []}
      busy={props.busy}
      onWaive={props.onWaive}
      onEdit={props.onEdit}
      onRemovePayment={props.onRemovePayment}
    />
  )

  return (
    <>
      {/* Computador: tabela */}
      <table className="hidden w-full text-sm md:table">
        <thead>
          <tr className="border-b text-left text-[11px] tracking-wider text-muted-foreground uppercase">
            <th className="pb-3 pr-4 font-semibold">Mês</th>
            <th className="pb-3 pr-4 font-semibold">Modalidade</th>
            <th className="pb-3 pr-6 text-right font-semibold">Mensalidade</th>
            <th className="pb-3 pr-6 text-right font-semibold">Pago</th>
            <th className="pb-3 pr-6 text-right font-semibold">Falta</th>
            <th className="pb-3 pr-4 font-semibold">Pago em</th>
            <th className="pb-3 pr-4 font-semibold">Situação</th>
            <th className="w-8" />
          </tr>
        </thead>
        <tbody>
          {props.charges.map((charge) => (
            <tr key={charge.id} className="border-b last:border-0">
              <td
                className="py-3.5 pr-4 font-medium whitespace-nowrap"
                title={`Vence em ${formatDate(charge.due_date)}`}
              >
                {formatMonth(charge.reference_month)}
              </td>
              <td className="py-3.5 pr-4">
                <What charge={charge} />
              </td>
              <td className="py-3.5 pr-6 text-right whitespace-nowrap tabular-nums">
                {formatMoney(charge.amount)}
              </td>
              <td className="py-3.5 pr-6 text-right whitespace-nowrap tabular-nums">
                <Paid charge={charge} />
              </td>
              <td className="py-3.5 pr-6 text-right whitespace-nowrap tabular-nums">
                <Missing charge={charge} />
              </td>
              <td className="py-3.5 pr-4 whitespace-nowrap">
                <PaidOn payments={byCharge.get(charge.id) ?? []} />
              </td>
              <td className="py-3.5 pr-4">
                <ChargeStatusChip status={charge.status} />
              </td>
              <td className="py-3.5 text-right">{menu(charge)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Celular: um bloco por cobrança */}
      <ul className="divide-y md:hidden">
        {props.charges.map((charge) => (
          <li key={charge.id} className="space-y-1.5 py-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium">
                  {formatMonth(charge.reference_month)}
                </p>
                <p className="text-xs text-muted-foreground">
                  <What charge={charge} inline />
                </p>
              </div>
              <div className="flex items-center gap-1">
                <ChargeStatusChip status={charge.status} />
                {menu(charge)}
              </div>
            </div>
            <dl className="grid grid-cols-3 gap-2 text-xs">
              <Cell label="Mensalidade">{formatMoney(charge.amount)}</Cell>
              <Cell label="Pago">
                <Paid charge={charge} />
              </Cell>
              <Cell label="Falta">
                <Missing charge={charge} />
              </Cell>
            </dl>
            {/* No celular a coluna "Pago em" não aparece: o selo vem aqui */}
            {byCharge.get(charge.id)?.[0] && (
              <AutomaticInfo payment={byCharge.get(charge.id)![0].payment} />
            )}
          </li>
        ))}
      </ul>
    </>
  )
}

function Cell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

function What({ charge, inline }: { charge: Charge; inline?: boolean }) {
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

function Paid({ charge }: { charge: Charge }) {
  return Number(charge.paid) > 0 ? (
    <>{formatMoney(charge.paid)}</>
  ) : (
    <span className="text-muted-foreground">—</span>
  )
}

// O que falta pagar: vermelho se já venceu, âmbar se ainda vai vencer
function Missing({ charge }: { charge: Charge }) {
  const missing = Number(charge.amount) - Number(charge.paid)

  if (charge.status === 'waived' || missing <= 0) {
    return <span className="text-muted-foreground">—</span>
  }

  return (
    <span
      className={cn(
        'font-semibold',
        charge.status === 'overdue'
          ? 'text-status-critical'
          : 'text-status-warning',
      )}
    >
      {formatMoney(missing.toFixed(2))}
    </span>
  )
}

// Data do pagamento mais recente desta cobrança; baixa automática ganha o
// selo da InfinitePay e o recibo
function PaidOn({ payments }: { payments: ChargePayment[] }) {
  const [last] = payments
  if (!last) return <span className="text-muted-foreground">—</span>

  return (
    <span className="flex flex-col items-start gap-1">
      {formatDate(last.payment.paid_on)}
      <AutomaticInfo payment={last.payment} />
    </span>
  )
}

function AutomaticInfo({ payment }: { payment: Payment }) {
  if (payment.source !== 'infinitepay') return null

  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <AutomaticBadge />
      <ReceiptLink url={payment.receipt_url} />
    </span>
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
