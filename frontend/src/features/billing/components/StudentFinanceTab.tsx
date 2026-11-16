import { ChevronRight, Copy, Ellipsis, History, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import type { Charge, CheckoutReview, StudentBilling } from '@/features/billing/api'
import { ChargeStatusChip } from '@/features/billing/components/ChargeStatusChip'
import { CheckoutReviews } from '@/features/billing/components/InfinitePayBits'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import {
  useCreatePayLink,
  useResolveReview,
  useStudentBilling,
} from '@/features/billing/hooks'
import {
  PAYMENT_METHOD_LABELS,
  chargeLabel,
  currentMonth,
  formatDayMonth,
} from '@/features/billing/labels'
import { paymentsByCharge } from '@/features/billing/statement'
import { parseWhatsAppUrl } from '@/features/billing/whatsapp'
import type { StudentDetail } from '@/features/students/api'
import { showApiError } from '@/lib/api/errors'
import { formatMoney } from '@/lib/money'

const OPEN = (charge: Charge) => charge.status !== 'paid' && charge.status !== 'waived'
const LABEL =
  'text-[11px] font-semibold tracking-wider text-muted-foreground uppercase'

// Aba "Financeiro" da ficha: só o que está em aberto agora (mensalidade e
// graduação). O histórico fica no Financeiro ("Histórico de pagamentos").
export function StudentFinanceTab({ student: detail }: { student: StudentDetail }) {
  const studentId = detail.student.id
  const { data, isLoading, error, refetch } = useStudentBilling(studentId)
  const renewLink = useCreatePayLink(studentId)
  const resolveReview = useResolveReview(studentId)
  const [paying, setPaying] = useState<{ group: 'monthly' | 'graduation'; chargeId: string | null } | null>(null)
  const [renewing, setRenewing] = useState(false)

  if (isLoading && !data) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">Carregando…</p>
    )
  }

  if (!data) {
    return (
      <div className="space-y-3 py-6 text-center text-sm">
        <p role="alert" className="text-destructive">
          {error ? 'Não foi possível carregar o financeiro.' : ''}
        </p>
        <Button variant="outline" className="rounded-full" onClick={refetch}>
          Tentar de novo
        </Button>
      </div>
    )
  }

  const graduations = data.charges.filter(
    (charge) => charge.kind === 'graduation' && OPEN(charge),
  )

  async function confirmRenew() {
    try {
      await renewLink.mutate(data!.open_total)
      toast.success('Link novo gerado')
      refetch()
    } catch (caught) {
      showApiError(caught)
    } finally {
      setRenewing(false)
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
    <div className="space-y-4">
      <CheckoutReviews
        reviews={data.reviews}
        busy={resolveReview.isPending}
        onResolve={(review) => void markResolved(review)}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MonthlyCard
          data={data}
          detail={detail}
          onPay={() => setPaying({ group: 'monthly', chargeId: null })}
          onRenew={() => setRenewing(true)}
        />
        {graduations.map((charge) => (
          <GraduationCard
            key={charge.id}
            charge={charge}
            detail={detail}
            onPay={() => setPaying({ group: 'graduation', chargeId: charge.id })}
          />
        ))}
      </div>

      {/* Cartão-botão: o histórico (todos os meses e graduações) fica no
          Financeiro */}
      <Link
        to={`/app/financeiro/alunos/${studentId}`}
        className="flex w-full items-center gap-3 rounded-2xl border bg-popover px-4 py-3.5 transition-colors hover:bg-accent"
      >
        <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-accent text-primary">
          <History className="size-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-medium">Histórico de pagamentos</span>
          <span className="block truncate text-xs text-muted-foreground">
            Mensalidades e graduações
          </span>
        </span>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
      </Link>

      <PaymentDialog
        studentId={studentId}
        studentName={detail.student.name}
        open={paying !== null}
        onOpenChange={(open) => !open && setPaying(null)}
        onDone={refetch}
        group={paying?.group ?? 'monthly'}
        chargeId={paying?.chargeId ?? null}
      />
      <ConfirmDialog
        open={renewing}
        onOpenChange={setRenewing}
        title="Gerar um link de pagamento novo?"
        description="O link antigo para de funcionar. Quem já recebeu precisa receber o novo."
        confirmLabel="Gerar link novo"
        onConfirm={() => void confirmRenew()}
      />
    </div>
  )
}

// Mensalidade: o que está em aberto (um ou mais meses) ou, com tudo pago,
// a do mês atual com "✓ Paga em …"
function MonthlyCard({
  data,
  detail,
  onPay,
  onRenew,
}: {
  data: StudentBilling
  detail: StudentDetail
  onPay: () => void
  onRenew: () => void
}) {
  const monthly = data.charges.filter((charge) => charge.kind !== 'graduation')
  // Do mais antigo ao mais novo
  const open = monthly.filter(OPEN).sort((a, b) => a.due_date.localeCompare(b.due_date))
  // Mensalidades do mês atual (uma por modalidade)
  const current = monthly.filter(
    (charge) =>
      charge.kind === 'monthly' && charge.reference_month.slice(0, 7) === currentMonth(),
  )

  if (open.length === 0) {
    const paid = current.filter((charge) => charge.status === 'paid')
    // A baixa mais recente entre as mensalidades do mês
    const payment = paid
      .flatMap((charge) => paymentsByCharge(data.payments).get(charge.id) ?? [])
      .map((item) => item.payment)
      .sort((a, b) => b.paid_on.localeCompare(a.paid_on))[0]
    const total = current.reduce((sum, charge) => sum + Number(charge.amount), 0)
    const allWaived =
      current.length > 0 && current.every((charge) => charge.status === 'waived')

    return (
      <ChargeCard
        title={current[0] ? monthlyTitle(current[0]) : 'Mensalidade'}
        status={paid.length > 0 ? 'paid' : allWaived ? 'waived' : undefined}
        value={current.length > 0 ? formatMoney(total.toFixed(2)) : undefined}
        detail={[...new Set(current.map((charge) => charge.modality_name))].join(' · ')}
      >
        {paid.length > 0 && (
          <p className="text-sm font-semibold text-sidebar-primary">
            ✓ Paga
            {payment && ` em ${formatDayMonth(payment.paid_on)}`}
            {payment?.method && ` · ${PAYMENT_METHOD_LABELS[payment.method]}`}
          </p>
        )}
        {allWaived && <p className="text-sm text-muted-foreground">Isenta neste mês</p>}
        {current.length === 0 && (
          <p className="text-sm text-muted-foreground">Nada em aberto 🎉</p>
        )}
      </ChargeCard>
    )
  }

  const oldest = open[0]
  const status = open.some((charge) => charge.status === 'overdue')
    ? 'overdue'
    : oldest.status
  const modalities = [...new Set(open.map((charge) => charge.modality_name))].join(' · ')

  return (
    <ChargeCard
      title={open.length === 1 ? monthlyTitle(oldest) : 'Mensalidade'}
      status={status}
      value={formatMoney(data.open_total)}
      detail={
        open.length === 1
          ? `${modalities} · vence ${formatDayMonth(oldest.due_date)}`
          : `${data.open_months} · ${modalities}`
      }
    >
      <Actions
        whatsapp={
          <WhatsAppButton
            url={data.whatsapp_url}
            studentName={detail.student.name}
            responsibleName={responsibleReceiving(detail, data.whatsapp_url)}
            size="sm"
          />
        }
        onPay={onPay}
        payUrl={data.pay_url}
        onRenew={onRenew}
      />
    </ChargeCard>
  )
}

function GraduationCard({
  charge,
  detail,
  onPay,
}: {
  charge: Charge
  detail: StudentDetail
  onPay: () => void
}) {
  const graduation = charge.graduation
  const open = Number(charge.amount) - Number(charge.paid)

  return (
    <ChargeCard
      title="Graduação"
      status={charge.status}
      value={formatMoney(open.toFixed(2))}
      detail={
        <span className="inline-flex flex-wrap items-center gap-1.5">
          {graduation && (
            <BeltDrawing belt={graduation.belt} width={26} height={9} className="shrink-0" />
          )}
          {charge.description}
          {graduation && ` · exame ${formatDayMonth(graduation.exam_date)}`}
          {` · pagar até ${formatDayMonth(charge.due_date)}`}
        </span>
      }
    >
      <Actions
        whatsapp={
          <WhatsAppButton
            url={graduation?.whatsapp_url}
            studentName={detail.student.name}
            responsibleName={responsibleReceiving(detail, graduation?.whatsapp_url ?? null)}
            size="sm"
          />
        }
        onPay={onPay}
        payUrl={graduation?.pay_url ?? null}
      />
    </ChargeCard>
  )
}

function ChargeCard({
  title,
  status,
  value,
  detail,
  children,
}: {
  title: string
  status?: Charge['status']
  value?: string
  detail?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-muted p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className={LABEL}>{title}</p>
        {status && <ChargeStatusChip status={status} />}
      </div>
      {value && (
        <div>
          <p className="text-2xl font-semibold tracking-tight md:text-3xl">{value}</p>
          {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
        </div>
      )}
      {children}
    </section>
  )
}

// WhatsApp · Dar baixa · "⋯" (Copiar link e, na mensalidade, Gerar novo)
function Actions({
  whatsapp,
  onPay,
  payUrl,
  onRenew,
}: {
  whatsapp: ReactNode
  onPay: () => void
  payUrl: string | null
  onRenew?: () => void
}) {
  async function copy() {
    if (!payUrl) return
    try {
      await navigator.clipboard.writeText(payUrl)
      toast.success('Link copiado')
    } catch {
      toast.error('Não foi possível copiar. Copie o link à mão.')
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {whatsapp}
      <Button size="sm" className="rounded-full" onClick={onPay}>
        Dar baixa
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="icon-sm"
            className="rounded-full"
            aria-label="Mais opções do link"
          >
            <Ellipsis />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="rounded-2xl">
          <DropdownMenuItem disabled={!payUrl} onSelect={() => void copy()}>
            <Copy /> Copiar link
          </DropdownMenuItem>
          {onRenew && (
            <DropdownMenuItem onSelect={onRenew}>
              <RefreshCw /> Gerar novo link
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

// "Mensalidade de novembro", "Taxa de matrícula" ou a categoria
const monthlyTitle = chargeLabel

// A mensagem vai para um responsável? (o número do link é o dele)
function responsibleReceiving(detail: StudentDetail, url: string | null | undefined) {
  if (!url) return null
  const { phone } = parseWhatsAppUrl(url)
  const digits = (value: string | null) => (value ?? '').replace(/\D/g, '')

  return (
    detail.responsibles.find((item) => digits(item.phone) === phone)?.name ?? null
  )
}
