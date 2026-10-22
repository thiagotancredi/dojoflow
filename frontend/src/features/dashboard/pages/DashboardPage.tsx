import { AlertCircle, CalendarClock } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { useAuth } from '@/features/auth/useAuth'
import { formatDayMonth } from '@/features/billing/labels'
import { useDashboardSummary } from '@/features/dashboard/api'
import type { DashboardSummary } from '@/features/dashboard/api'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { HorizontalBars } from '@/features/dashboard/components/HorizontalBars'
import { NewStudentsChart } from '@/features/dashboard/components/NewStudentsChart'
import { StudentRow } from '@/features/dashboard/components/StudentRow'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

type AgeGroup = DashboardSummary['age_groups']['all'][number]

const AGE_LABELS: Record<AgeGroup['group'], string> = {
  kids: 'Kids (até 12)',
  juvenile: 'Juvenil (13–17)',
  adult: 'Adulto (18–39)',
  master: 'Master (40+)',
  unknown: 'Sem data de nascimento',
}

// Dashboard em três blocos: Financeiro, Alunos e Crescimento.
export function DashboardPage() {
  const { master } = useAuth()
  // Primeiro nome do mestre logado (ex.: "Mestre Teste" → "Mestre")
  const firstName = master?.name.split(' ')[0]
  const summary = useDashboardSummary()
  const data = summary.data
  // Estado comum dos cartões enquanto o resumo não chega
  const pending = !data ? (
    <CardState loading={summary.isLoading} />
  ) : null
  const monthName = new Date().toLocaleDateString('pt-BR', { month: 'long' })

  return (
    <div className="space-y-4">
      <PageHeader title={firstName ? `Olá, ${firstName}` : 'Dashboard'} />

      <SectionTitle>Financeiro</SectionTitle>
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard
          title={
            <>
              Inadimplentes
              {data && <Count tone="critical">{data.overdue_students}</Count>}
            </>
          }
          subtitle={
            data && Number(data.overdue_total) > 0
              ? `Vencidas e não pagas · ${formatMoney(data.overdue_total)} em aberto`
              : 'Mensalidades vencidas e não pagas'
          }
          action={<SeeAll to="/app/mensalidades" />}
        >
          {pending ??
            (data!.overdue.length === 0 ? (
              <Empty>Ninguém em atraso 🎉</Empty>
            ) : (
              <ul className="space-y-1">
                {data!.overdue.map((student) => (
                  <StudentRow
                    key={student.student_id}
                    studentId={student.student_id}
                    tab="billing"
                    name={student.name}
                    detail={student.modality}
                    trailing={
                      <>
                        <p className="text-sm font-medium">
                          {formatMoney(student.amount)}
                        </p>
                        <p className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
                          <AlertCircle className="size-3.5 text-status-critical" />
                          {student.days_late}{' '}
                          {student.days_late === 1 ? 'dia' : 'dias'} em atraso
                        </p>
                      </>
                    }
                  />
                ))}
              </ul>
            ))}
        </DashboardCard>

        <DashboardCard
          title={
            <>
              Vencem em 7 dias
              {data && <Count tone="warning">{data.due_soon_students}</Count>}
            </>
          }
          subtitle="Para lembrar antes de atrasar"
          action={<SeeAll to="/app/mensalidades?filtro=a-vencer" />}
        >
          {pending ??
            (data!.due_soon.length === 0 ? (
              <Empty>Nenhum vencimento nos próximos 7 dias</Empty>
            ) : (
              <ul className="space-y-1">
                {data!.due_soon.map((charge, index) => (
                  <StudentRow
                    // O mesmo aluno pode ter duas cobranças (duas modalidades)
                    key={`${charge.student_id}-${index}`}
                    studentId={charge.student_id}
                    tab="billing"
                    name={charge.name}
                    detail={charge.modality}
                    trailing={
                      <>
                        <p className="text-sm font-medium">
                          {formatMoney(charge.amount)}
                        </p>
                        <p className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
                          <CalendarClock className="size-3.5 text-status-warning" />
                          vence {formatDayMonth(charge.due_date)}
                        </p>
                      </>
                    }
                  />
                ))}
              </ul>
            ))}
        </DashboardCard>
      </div>

      <SectionTitle>Alunos</SectionTitle>
      <div className="grid gap-4 lg:grid-cols-3">
        <DashboardCard
          title={
            data
              ? `${data.active_students} ${data.active_students === 1 ? 'aluno ativo' : 'alunos ativos'}`
              : 'Alunos ativos'
          }
          subtitle="Por modalidade"
        >
          {pending ??
            (data!.students_by_modality.length === 0 ? (
              <Empty>Nenhum aluno ativo ainda.</Empty>
            ) : (
              <HorizontalBars
                data={data!.students_by_modality.map((item) => ({
                  label: item.modality_name,
                  count: item.count,
                }))}
              />
            ))}
        </DashboardCard>

        <AgeGroupsCard data={data} pending={pending} />

        <DashboardCard
          title={
            <>
              Aniversariantes
              {data && <Count>{data.birthdays.length}</Count>}
            </>
          }
          subtitle={`Em ${monthName}`}
        >
          {pending ??
            (data!.birthdays.length === 0 ? (
              <Empty>Nenhum aniversariante em {monthName}.</Empty>
            ) : (
              <ul className="space-y-1">
                {data!.birthdays.map((person) => (
                  <StudentRow
                    key={person.student_id}
                    studentId={person.student_id}
                    name={person.name}
                    detail={`Faz ${person.turning_age} anos`}
                    trailing={
                      <span className="flex items-center gap-2">
                        {person.is_today && (
                          <span className="rounded-full bg-status-exempt-soft px-2 py-0.5 text-[11px] font-bold text-status-exempt">
                            hoje
                          </span>
                        )}
                        <span className="rounded-lg bg-chip-active px-2 py-1 text-sm font-semibold text-chip-active-foreground">
                          {String(person.day).padStart(2, '0')}
                        </span>
                      </span>
                    }
                  />
                ))}
              </ul>
            ))}
        </DashboardCard>
      </div>

      <SectionTitle>Crescimento</SectionTitle>
      <DashboardCard
        title="Novos alunos por mês"
        subtitle="Últimos 6 meses"
      >
        {pending ??
          (data!.new_students_by_month.every((item) => item.count === 0) ? (
            <Empty>Nenhum aluno novo nos últimos 6 meses.</Empty>
          ) : (
            <NewStudentsChart data={data!.new_students_by_month} />
          ))}
      </DashboardCard>
    </div>
  )
}

// Faixa etária com filtro: "Todos" ou uma modalidade da academia
function AgeGroupsCard({
  data,
  pending,
}: {
  data: DashboardSummary | null
  pending: ReactNode
}) {
  // null = Todos; senão o id da modalidade escolhida
  const [modalityId, setModalityId] = useState<string | null>(null)
  const modalities = data?.age_groups.by_modality ?? []
  const selected = modalities.find((item) => item.modality_id === modalityId)
  const groups = selected?.groups ?? data?.age_groups.all ?? []
  // "Sem data de nascimento" só aparece se tiver alguém
  const visible = groups.filter(
    (item) => item.group !== 'unknown' || item.count > 0,
  )
  const empty = groups.every((item) => item.count === 0)

  return (
    <DashboardCard
      title="Faixa etária"
      subtitle="Alunos ativos"
      action={
        modalities.length > 1 && (
          <div className="flex flex-wrap justify-end gap-1.5">
            <FilterChip
              active={selected === undefined}
              onClick={() => setModalityId(null)}
            >
              Todos
            </FilterChip>
            {modalities.map((item) => (
              <FilterChip
                key={item.modality_id}
                active={item.modality_id === selected?.modality_id}
                onClick={() => setModalityId(item.modality_id)}
              >
                {item.modality_name}
              </FilterChip>
            ))}
          </div>
        )
      }
    >
      {pending ??
        (empty ? (
          <Empty>Nenhum aluno ativo ainda.</Empty>
        ) : (
          <HorizontalBars
            data={visible.map((item) => ({
              label: AGE_LABELS[item.group],
              count: item.count,
            }))}
          />
        ))}
    </DashboardCard>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'rounded-full border px-2.5 py-0.5 text-xs transition-colors',
        active
          ? 'border-chip-active-border bg-chip-active font-semibold text-chip-active-foreground'
          : 'border-border text-muted-foreground hover:text-foreground',
      )}
    >
      {children}
    </button>
  )
}

// Título de bloco: "FINANCEIRO ———"
function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 px-1 pt-2">
      <h2 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        {children}
      </h2>
      <hr className="flex-1 border-border" />
    </div>
  )
}

// Número ao lado do título do cartão ("Inadimplentes · 5")
function Count({
  children,
  tone,
}: {
  children: ReactNode
  tone?: 'critical' | 'warning'
}) {
  return (
    <span
      className={cn(
        'ml-1.5',
        tone === 'critical' && 'text-status-critical',
        tone === 'warning' && 'text-status-warning',
      )}
    >
      · {children}
    </span>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}

function CardState({ loading }: { loading: boolean }) {
  return loading ? (
    <p className="text-sm text-muted-foreground">Carregando…</p>
  ) : (
    <p role="alert" className="text-sm text-destructive">
      Não foi possível carregar.
    </p>
  )
}

function SeeAll({ to }: { to: string }) {
  return (
    <Link
      to={to}
      className="shrink-0 text-xs font-medium text-sidebar-primary hover:underline"
    >
      Ver todos
    </Link>
  )
}
