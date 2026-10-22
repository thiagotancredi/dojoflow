import { Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import type { Charge, Payment } from '@/features/billing/api'
import { ChargeStatement } from '@/features/billing/components/ChargeStatement'
import { EditChargeDialog } from '@/features/billing/components/EditChargeDialog'
import { LaunchPastChargeDialog } from '@/features/billing/components/LaunchPastChargeDialog'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import {
  useDeletePayment,
  useSetChargeWaived,
  useStudentBilling,
} from '@/features/billing/hooks'
import { chargeTitle } from '@/features/billing/statement'
import { parseWhatsAppUrl } from '@/features/billing/whatsapp'
import type { StudentDetail } from '@/features/students/api'
import { showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'

// Quantas cobranças em aberto o topo lista antes do "e mais N"
const OPEN_LIST_LIMIT = 4

// Aba "Mensalidades" da ficha: o que está em aberto e o extrato mês a mês
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
  // O que forma o "em aberto" (mesma regra do sistema: tudo que não está
  // pago nem isento), do mais antigo para o mais novo. A soma bate o total.
  const openCharges = data.charges
    .filter((charge) => charge.status !== 'paid' && charge.status !== 'waived')
    .reverse()

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
      toast.success('Pagamento excluído')
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
          {hasOpen ? (
            <ul className="text-xs text-muted-foreground">
              {openCharges.slice(0, OPEN_LIST_LIMIT).map((charge) => (
                <li key={charge.id}>
                  {chargeTitle(charge)}:{' '}
                  {Number(charge.paid) > 0 && 'falta '}
                  {formatMoney(
                    (Number(charge.amount) - Number(charge.paid)).toFixed(2),
                  )}
                </li>
              ))}
              {openCharges.length > OPEN_LIST_LIMIT && (
                <li>e mais {openCharges.length - OPEN_LIST_LIMIT}</li>
              )}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">Nada em aberto 🎉</p>
          )}
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

      {/* Extrato: uma linha por mensalidade (mais nova em cima) */}
      <section className="space-y-2">
        {data.charges.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma cobrança ainda. A primeira mensalidade aparece no mês
            seguinte à matrícula.
          </p>
        ) : (
          <ChargeStatement
            charges={data.charges}
            payments={data.payments}
            busy={waive.isPending}
            onWaive={(charge, waived) => void setWaived(charge, waived)}
            onEdit={setEditing}
            onRemovePayment={setRemoving}
          />
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

// Quando um pagamento quitou mais de uma mensalidade, avisa todas
function removeDescription(payment: Payment, charges: Charge[]) {
  const back = 'As mensalidades voltam ao saldo que tinham antes dele.'
  if (payment.allocations.length < 2) return back

  const parts = payment.allocations.map((allocation) => {
    const charge = charges.find((item) => item.id === allocation.charge_id)
    const title = charge ? chargeTitle(charge) : allocation.label
    return `${title} (${formatMoney(allocation.amount)})`
  })
  return `Este pagamento foi dividido entre: ${parts.join(', ')}. ${back}`
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
