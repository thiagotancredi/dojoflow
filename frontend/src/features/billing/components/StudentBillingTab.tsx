import { Copy, Plus, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import type { Charge, CheckoutReview, Payment } from '@/features/billing/api'
import { ChargeStatement } from '@/features/billing/components/ChargeStatement'
import { EditChargeDialog } from '@/features/billing/components/EditChargeDialog'
import { CheckoutReviews } from '@/features/billing/components/InfinitePayBits'
import { LaunchPastChargeDialog } from '@/features/billing/components/LaunchPastChargeDialog'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import {
  useDeletePayment,
  useRenewPayLink,
  useResolveReview,
  useSetChargeWaived,
  useStudentBilling,
} from '@/features/billing/hooks'
import { chargeTitle } from '@/features/billing/statement'
import { parseWhatsAppUrl } from '@/features/billing/whatsapp'
import type { StudentDetail } from '@/features/students/api'
import { showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'

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
  const renewLink = useRenewPayLink(studentId)
  const resolveReview = useResolveReview(studentId)
  const [renewing, setRenewing] = useState(false)

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
  // O que forma o "em aberto": tudo que não está pago nem isento
  const openCharges = data.charges.filter(
    (charge) => charge.status !== 'paid' && charge.status !== 'waived',
  )

  async function setWaived(charge: Charge, waived: boolean) {
    try {
      await waive.mutate(charge.id, waived)
      toast.success(waived ? 'Cobrança isenta' : 'Isenção desfeita')
      refetch()
    } catch (caught) {
      showApiError(caught)
    }
  }

  async function copyPayLink(url: string) {
    try {
      await navigator.clipboard.writeText(url)
      toast.success('Link copiado')
    } catch {
      toast.error('Não foi possível copiar. Copie o link à mão.')
    }
  }

  async function confirmRenew() {
    try {
      await renewLink.mutate()
      toast.success('Link novo gerado')
      refetch()
    } catch (caught) {
      showApiError(caught)
    } finally {
      setRenewing(false)
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

  async function markResolved(review: CheckoutReview) {
    try {
      await resolveReview.mutate(review.id)
      toast.success('Marcado como resolvido')
      refetch()
    } catch (caught) {
      showApiError(caught)
    }
  }

  return (
    <div className="space-y-7">
      <CheckoutReviews
        reviews={data.reviews}
        busy={resolveReview.isPending}
        onResolve={(review) => void markResolved(review)}
      />
      {/* Topo: quanto deve (esquerda) e como cobrar (direita); no celular,
          um cartão embaixo do outro */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.25fr]">
        <section className="flex flex-col justify-between gap-4 rounded-2xl bg-muted p-5">
          <div>
            <p className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
              Em aberto
            </p>
            <p className="text-3xl font-semibold tracking-tight">
              {formatMoney(data.open_total)}
            </p>
            <p className="text-xs text-muted-foreground">
              {hasOpen ? openCountLabel(openCharges) : 'Nada em aberto 🎉'}
            </p>
          </div>
          <div>
            <Button
              className="rounded-full"
              disabled={!hasOpen}
              onClick={() => setPaying(true)}
            >
              Dar baixa
            </Button>
          </div>
        </section>

        <section className="space-y-3 rounded-2xl border bg-popover p-5">
          <p className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
            Cobrar
          </p>
          <div className="flex flex-wrap gap-2">
            <WhatsAppButton
              url={data.whatsapp_url}
              studentName={detail.student.name}
              responsibleName={responsibleReceiving(detail, data.whatsapp_url)}
              label="Enviar no WhatsApp"
            />
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => void copyPayLink(data.pay_url)}
            >
              <Copy /> Copiar link
            </Button>
          </div>
          {/* Link da página de pagamento (vai na mensagem do WhatsApp) */}
          <div className="flex items-center gap-2">
            <span
              title={data.pay_url}
              className="min-w-0 flex-1 truncate rounded-xl border bg-background px-3 py-2 font-mono text-xs text-muted-foreground"
            >
              {data.pay_url.replace(/^https?:\/\//, '')}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0 rounded-full text-muted-foreground"
              disabled={renewLink.isPending}
              onClick={() => setRenewing(true)}
            >
              <RefreshCw /> Gerar novo
            </Button>
          </div>
        </section>
      </div>

      {/* Extrato: uma linha por mensalidade (mais nova em cima) */}
      <section className="space-y-4">
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
        open={renewing}
        onOpenChange={setRenewing}
        title="Gerar um link de pagamento novo?"
        description="O link antigo para de funcionar. Quem já recebeu precisa receber o novo."
        confirmLabel="Gerar link novo"
        onConfirm={() => void confirmRenew()}
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

// "2 mensalidades em aberto" (ou "cobranças", se tiver taxa de matrícula)
function openCountLabel(open: Charge[]) {
  const onlyMonthly = open.every((charge) => charge.kind !== 'enrollment_fee')
  const noun = onlyMonthly ? 'mensalidade' : 'cobrança'
  return `${open.length} ${noun}${open.length === 1 ? '' : 's'} em aberto`
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
