import { Ellipsis, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { Charge, Payment } from '@/features/billing/api'
import { ChargeStatusChip } from '@/features/billing/components/ChargeStatusChip'
import { EditChargeDialog } from '@/features/billing/components/EditChargeDialog'
import { LaunchPastChargeDialog } from '@/features/billing/components/LaunchPastChargeDialog'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import {
  useDeletePayment,
  useSetChargeWaived,
  useStudentBilling,
} from '@/features/billing/hooks'
import {
  PAYMENT_METHOD_LABELS,
  capitalize,
  formatDayMonth,
  formatMonth,
} from '@/features/billing/labels'
import { parseWhatsAppUrl } from '@/features/billing/whatsapp'
import type { StudentDetail } from '@/features/students/api'
import { showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'

// Aba "Mensalidades" da ficha: o que está em aberto, mês a mês, e as baixas
export function StudentBillingTab({ student: detail }: { student: StudentDetail }) {
  const studentId = detail.student.id
  const { data, isLoading, error, refetch } = useStudentBilling(studentId)
  const [paying, setPaying] = useState(false)
  const [launching, setLaunching] = useState(false)
  const [editing, setEditing] = useState<Charge | null>(null)
  const [removing, setRemoving] = useState<Payment | null>(null)
  const waive = useSetChargeWaived(studentId)
  const removePayment = useDeletePayment(studentId)

  if (isLoading && !data) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        Carregando mensalidades…
      </p>
    )
  }

  if (!data) {
    return (
      <div className="space-y-3 py-6 text-center text-sm">
        <p role="alert" className="text-destructive">
          {error ? 'Não foi possível carregar as mensalidades.' : ''}
        </p>
        <Button variant="outline" className="rounded-full" onClick={refetch}>
          Tentar de novo
        </Button>
      </div>
    )
  }

  const hasOpen = Number(data.open_total) > 0

  async function setWaived(charge: Charge, waived: boolean) {
    try {
      await waive.mutate(charge.id, waived)
      toast.success(waived ? 'Cobrança isenta' : 'Isenção desfeita')
      refetch()
    } catch (caught) {
      showApiError(caught)
    }
  }

  async function confirmRemove() {
    if (!removing) return
    try {
      await removePayment.mutate(removing.id)
      toast.success('Baixa excluída')
      refetch()
    } catch (caught) {
      showApiError(caught)
    } finally {
      setRemoving(null)
    }
  }

  return (
    <div className="space-y-5">
      {/* Topo: total em aberto + ações principais */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-muted p-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
            Em aberto
          </p>
          <p className="text-2xl font-semibold">
            {formatMoney(data.open_total)}
          </p>
          <p className="text-xs text-muted-foreground">
            {hasOpen ? capitalize(data.open_months) : 'Nada em aberto 🎉'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <WhatsAppButton
            url={data.whatsapp_url}
            studentName={detail.student.name}
            responsibleName={responsibleReceiving(detail, data.whatsapp_url)}
          />
          <Button
            className="rounded-full"
            disabled={!hasOpen}
            onClick={() => setPaying(true)}
          >
            Dar baixa
          </Button>
        </div>
      </div>

      {/* Mês a mês (mais novo em cima) */}
      <section className="space-y-2">
        {data.charges.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma cobrança ainda. A primeira mensalidade aparece no mês
            seguinte à matrícula.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">Mês</th>
                  <th className="py-2 pr-3 font-medium">Modalidade</th>
                  <th className="py-2 pr-3 font-medium">Vence</th>
                  <th className="py-2 pr-3 font-medium">Valor</th>
                  <th className="py-2 pr-3 font-medium">Pago</th>
                  <th className="py-2 pr-3 font-medium">Situação</th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {data.charges.map((charge) => (
                  <ChargeRow
                    key={charge.id}
                    charge={charge}
                    busy={waive.isPending}
                    onWaive={(waived) => void setWaived(charge, waived)}
                    onEdit={() => setEditing(charge)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
        {detail.enrollments.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="rounded-full"
            onClick={() => setLaunching(true)}
          >
            <Plus /> Lançar mês anterior
          </Button>
        )}
      </section>

      {/* Histórico de baixas */}
      <section className="space-y-2">
        <h3 className="font-semibold">Histórico de pagamentos</h3>
        {data.payments.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma baixa registrada.
          </p>
        ) : (
          <ul className="divide-y rounded-2xl border">
            {data.payments.map((payment) => (
              <PaymentItem
                key={payment.id}
                payment={payment}
                onRemove={() => setRemoving(payment)}
              />
            ))}
          </ul>
        )}
      </section>

      <PaymentDialog
        studentId={studentId}
        studentName={detail.student.name}
        open={paying}
        onOpenChange={setPaying}
        onDone={refetch}
      />
      <LaunchPastChargeDialog
        studentId={studentId}
        enrollments={detail.enrollments}
        open={launching}
        onOpenChange={setLaunching}
        onDone={refetch}
      />
      <EditChargeDialog
        studentId={studentId}
        charge={editing}
        title={editing ? chargeTitle(editing) : ''}
        onClose={() => setEditing(null)}
        onDone={refetch}
      />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title="Excluir esta baixa?"
        description="As cobranças voltam ao saldo que tinham antes dela."
        confirmLabel="Excluir baixa"
        onConfirm={() => void confirmRemove()}
      />
    </div>
  )
}

// A mensagem vai para um responsável? (o número do link é o dele)
function responsibleReceiving(detail: StudentDetail, url: string | null) {
  if (!url) return null
  const { phone } = parseWhatsAppUrl(url)
  const digits = (value: string | null) => (value ?? '').replace(/\D/g, '')

  return (
    detail.responsibles.find((item) => digits(item.phone) === phone)?.name ??
    null
  )
}

function chargeTitle(charge: Charge) {
  const what =
    charge.kind === 'enrollment_fee' ? 'Taxa de matrícula' : charge.modality_name
  return `${formatMonth(charge.reference_month)} · ${what}`
}

function ChargeRow({
  charge,
  busy,
  onWaive,
  onEdit,
}: {
  charge: Charge
  busy: boolean
  onWaive: (waived: boolean) => void
  onEdit: () => void
}) {
  const paid = Number(charge.paid)
  const open = Number(charge.amount) - paid
  const isFee = charge.kind === 'enrollment_fee'
  // Com pagamento, a cobrança não muda (exclua a baixa antes)
  const canChange = paid === 0

  return (
    <tr className="border-b last:border-0">
      <td className="py-2 pr-3 whitespace-nowrap">
        {formatMonth(charge.reference_month)}
      </td>
      <td className="py-2 pr-3">
        {isFee ? (
          <>
            Taxa de matrícula
            <span className="block text-xs text-muted-foreground">
              {charge.modality_name}
            </span>
          </>
        ) : (
          charge.modality_name
        )}
      </td>
      <td className="py-2 pr-3" title={formatDate(charge.due_date)}>
        {formatDayMonth(charge.due_date)}
      </td>
      <td className="py-2 pr-3 whitespace-nowrap">
        {formatMoney(charge.amount)}
      </td>
      <td className="py-2 pr-3 whitespace-nowrap">
        {paid > 0 ? formatMoney(charge.paid) : '—'}
      </td>
      <td className="py-2 pr-3">
        <ChargeStatusChip status={charge.status} open={open} />
      </td>
      <td className="py-2 text-right">
        {canChange && (
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
            <DropdownMenuContent align="end">
              {charge.status === 'waived' ? (
                <DropdownMenuItem onSelect={() => onWaive(false)}>
                  Desfazer isenção
                </DropdownMenuItem>
              ) : (
                <>
                  <DropdownMenuItem onSelect={() => onWaive(true)}>
                    Isentar
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={onEdit}>Editar</DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </td>
    </tr>
  )
}

function PaymentItem({
  payment,
  onRemove,
}: {
  payment: Payment
  onRemove: () => void
}) {
  const details = [
    `em ${formatDate(payment.paid_on)}`,
    payment.method ? PAYMENT_METHOD_LABELS[payment.method] : null,
  ].filter(Boolean)

  return (
    <li className="flex items-start justify-between gap-3 p-3">
      <div className="min-w-0 space-y-0.5 text-sm">
        <p>
          <span className="font-semibold">{formatMoney(payment.amount)}</span>{' '}
          <span className="text-muted-foreground">{details.join(' · ')}</span>
        </p>
        <p className="text-xs text-muted-foreground">
          →{' '}
          {payment.allocations
            .map((item) => `${item.label} ${formatMoney(item.amount)}`)
            .join(' · ')}
        </p>
        {payment.notes && (
          <p className="text-xs text-muted-foreground">{payment.notes}</p>
        )}
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Excluir baixa"
        className="size-8 shrink-0 rounded-full text-destructive"
        onClick={onRemove}
      >
        <Trash2 />
      </Button>
    </li>
  )
}
