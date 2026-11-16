import { ChevronRight, Copy, Ellipsis, History, MessageCircle, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import type { Charge, CheckoutReview, StudentBilling } from '@/features/billing/api'
import { ChargeDialog } from '@/features/billing/components/ChargeDialog'
import { ChargeStatusChip } from '@/features/billing/components/ChargeStatusChip'
import { LaunchChargeDialog } from '@/features/billing/components/LaunchChargeDialog'
import { CheckoutReviews } from '@/features/billing/components/InfinitePayBits'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import {
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
import { AddCard } from '@/features/students/components/tabs/TabParts'
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
  const resolveReview = useResolveReview(studentId)
  const [paying, setPaying] = useState<{ group: 'monthly' | 'graduation'; chargeId: string | null } | null>(null)
  const [charging, setCharging] = useState(false)
  const [launching, setLaunching] = useState(false)

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
        {/* "Lançar cobrança" logo abaixo do cartão, sempre (até sem nada
            em aberto): cria algo novo; o cartão cuida do que já existe */}
        <div className="space-y-2">
          <MonthlyCard
            data={data}
            onPay={() => setPaying({ group: 'monthly', chargeId: null })}
            onCharge={() => setCharging(true)}
          />
          {detail.enrollments.length > 0 && (
            <AddCard
              label="Lançar cobrança"
              onClick={() => setLaunching(true)}
              className="h-14 flex-row"
            />
          )}
        </div>
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
      <LaunchChargeDialog
        studentId={studentId}
        enrollments={detail.enrollments}
        charges={data.charges}
        open={launching}
        onOpenChange={setLaunching}
        onDone={refetch}
      />
      <ChargeDialog
        studentId={studentId}
        studentName={detail.student.name}
        responsibleName={responsibleReceiving(detail, data.whatsapp_url)}
        charges={data.charges}
        openTotal={data.open_total}
        open={charging}
        onOpenChange={setCharging}
        onDone={refetch}
      />
    </div>
  )
}

// "Em aberto": mensalidades, taxa e avulsas (um ou mais itens) com Cobrar e
// Dar baixa; sem nada em aberto, R$ 0,00 (e a baixa do mês, se teve)
function MonthlyCard({
  data,
  onPay,
  onCharge,
}: {
  data: StudentBilling
  onPay: () => void
  onCharge: () => void
}) {
  const monthly = data.charges.filter((charge) => charge.kind !== 'graduation')
  // Do mais antigo ao mais novo
  const open = monthly.filter(OPEN).sort((a, b) => a.due_date.localeCompare(b.due_date))

  if (open.length === 0) {
    // Mensalidades do mês atual (uma por modalidade): a baixa mais recente
    const current = monthly.filter(
      (charge) =>
        charge.kind === 'monthly' && charge.reference_month.slice(0, 7) === currentMonth(),
    )
    const paid = current.filter((charge) => charge.status === 'paid')
    const payment = paid
      .flatMap((charge) => paymentsByCharge(data.payments).get(charge.id) ?? [])
      .map((item) => item.payment)
      .sort((a, b) => b.paid_on.localeCompare(a.paid_on))[0]

    return (
      <ChargeCard title="Em aberto" value={formatMoney('0')} detail="Nada em aberto">
        {paid.length > 0 && (
          <p className="text-sm font-semibold text-sidebar-primary">
            ✓ {monthlyTitle(paid[0])} paga
            {payment && ` em ${formatDayMonth(payment.paid_on)}`}
            {payment?.method && ` · ${PAYMENT_METHOD_LABELS[payment.method]}`}
          </p>
        )}
      </ChargeCard>
    )
  }

  const status = open.some((charge) => charge.status === 'overdue')
    ? 'overdue'
    : open[0].status
  const modalities = [...new Set(open.map((charge) => charge.modality_name))].join(' · ')

  return (
    <ChargeCard
      title="Em aberto"
      status={status}
      value={formatMoney(data.open_total)}
      detail={`${data.open_months} · ${modalities}`}
    >
      <div className="grid grid-cols-2 gap-2">
        <Button variant="outline" className="h-10 rounded-full" onClick={onCharge}>
          <MessageCircle /> Cobrar
        </Button>
        <Button className="h-10 rounded-full" onClick={onPay}>
          Dar baixa
        </Button>
      </div>
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
