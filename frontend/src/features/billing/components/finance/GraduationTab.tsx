import { AlertCircle, ChevronRight, HandCoins, Users } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import type { ExamBilling } from '@/features/billing/api'
import { MoneyTile } from '@/features/billing/components/finance/MoneyTile'
import type { useGraduationOverview } from '@/features/billing/hooks'
import { formatDayMonth, formatMoneyShort } from '@/features/billing/labels'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type GraduationState = ReturnType<typeof useGraduationOverview>

// Aba "Graduação" do Financeiro: 3 números e os exames. A cobrança em si
// continua na lista de cada exame ("Ver lista"), onde ficam WhatsApp e
// Dar baixa.
export function GraduationTab({ overview }: { overview: GraduationState }) {
  const data = overview.data

  if (!data) {
    return overview.isLoading ? (
      <p className="py-6 text-center text-sm text-muted-foreground">Carregando…</p>
    ) : (
      <div className="space-y-3 py-6 text-center text-sm">
        <p role="alert" className="text-destructive">
          Não foi possível carregar a graduação.
        </p>
        <Button variant="outline" className="rounded-full" onClick={overview.refetch}>
          Tentar de novo
        </Button>
      </div>
    )
  }

  const unpaid = `${data.unpaid_students} ${data.unpaid_students === 1 ? 'aluno' : 'alunos'}`

  return (
    <div className="space-y-4">
      {/* Celular: lista de valores */}
      <section className="flex flex-col divide-y rounded-3xl bg-card px-4 py-2 md:hidden">
        <Row label={`Recebido · de ${formatMoney(data.expected)}`}>
          {formatMoney(data.received)}
        </Row>
        <Row label="Falta receber" className="text-status-pending">
          {formatMoney(data.open_total)}
        </Row>
        <Row label="Ainda não pagaram" className="text-status-critical">
          {unpaid}
        </Row>
      </section>

      {/* Computador: 3 números */}
      <div className="hidden gap-3 md:grid md:grid-cols-3">
        <MoneyTile
          label="Recebido"
          detail={`de ${formatMoney(data.expected)}`}
          value={data.received}
          icon={<HandCoins className="size-5" />}
        />
        <MoneyTile
          label="Falta receber"
          value={data.open_total}
          tone="warning"
          icon={<AlertCircle className="size-5" />}
        />
        <MoneyTile
          label="Ainda não pagaram"
          text={unpaid}
          tone="critical"
          valueClassName="text-status-critical"
          icon={<Users className="size-5" />}
        />
      </div>

      <DashboardCard
        title="Exames"
        subtitle="Com dinheiro em aberto ou com data limite neste mês"
      >
        {data.exams.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhum exame cobrando neste mês.
          </p>
        ) : (
          <>
            {/* Computador: tabela */}
            <table className="hidden w-full text-sm md:table">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">Exame</th>
                  <th className="py-2 pr-3 font-medium">Recebido</th>
                  <th className="py-2 pr-3 font-medium">Quem deve</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.exams.map((exam) => (
                  <tr key={exam.list_id} className="border-b last:border-0">
                    <td className="py-2.5 pr-3">
                      <ExamName exam={exam} />
                    </td>
                    <td className="w-60 py-2.5 pr-3">
                      <p className="text-sm">
                        <span className="font-medium">{formatMoneyShort(exam.received)}</span>{' '}
                        <span className="text-xs text-muted-foreground">
                          de {formatMoneyShort(exam.total)}
                        </span>
                      </p>
                      <div className="mt-1 h-2.5 rounded-full bg-muted">
                        <div
                          className="h-2.5 rounded-full bg-chart-1"
                          style={{ width: `${ratio(exam) * 100}%` }}
                        />
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <Owing exam={exam} />
                    </td>
                    <td className="py-2.5 text-right">
                      <Link
                        to={`/app/graduacoes/${exam.list_id}`}
                        className="inline-flex items-center gap-0.5 text-xs font-medium whitespace-nowrap text-sidebar-primary"
                      >
                        Ver lista <ChevronRight className="size-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Celular: tocar no exame abre a lista dele */}
            <ul className="md:hidden">
              {data.exams.map((exam) => (
                <li key={exam.list_id} className="border-b last:border-0">
                  <Link
                    to={`/app/graduacoes/${exam.list_id}`}
                    className="flex items-center gap-3 py-3"
                  >
                    <span className="min-w-0 flex-1">
                      <ExamName exam={exam} />
                      <Owing exam={exam} className="text-xs" />
                    </span>
                    <span className="shrink-0 text-right text-sm">
                      <span className="block font-semibold">
                        {formatMoneyShort(exam.received)}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        de {formatMoneyShort(exam.total)}
                      </span>
                    </span>
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </DashboardCard>
    </div>
  )
}

function ratio(exam: ExamBilling) {
  const total = Number(exam.total)
  return total > 0 ? Math.min(Number(exam.received) / total, 1) : 0
}

function ExamName({ exam }: { exam: ExamBilling }) {
  return (
    <>
      <p className="truncate font-medium">
        {exam.modality_name} · {exam.name}
      </p>
      <p className="text-xs text-muted-foreground">
        exame {formatDayMonth(exam.exam_date)} · pagar até{' '}
        {formatDayMonth(exam.payment_due_date)}
      </p>
    </>
  )
}

// "5 devem · vence em 10 dias" (amarelo), "1 deve · 9 dias de atraso"
// (vermelho) ou "Todos pagaram" (verde)
function Owing({ exam, className }: { exam: ExamBilling; className?: string }) {
  if (exam.owing === 0) {
    return (
      <p className={cn('text-sm font-medium text-sidebar-primary', className)}>
        Todos pagaram
      </p>
    )
  }
  const who = `${exam.owing} ${exam.owing === 1 ? 'deve' : 'devem'}`
  const days = (count: number) => `${count} ${count === 1 ? 'dia' : 'dias'}`

  if (exam.days_late !== null) {
    return (
      <p className={cn('text-sm font-medium text-status-critical', className)}>
        {who} · {days(exam.days_late)} de atraso
      </p>
    )
  }
  return (
    <p className={cn('text-sm font-medium text-status-pending', className)}>
      {who} ·{' '}
      {exam.days_to_due === 0 ? 'vence hoje' : `vence em ${days(exam.days_to_due ?? 0)}`}
    </p>
  )
}

function Row({
  label,
  className,
  children,
}: {
  label: string
  className?: string
  children: string
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn('font-semibold', className)}>{children}</span>
    </div>
  )
}
