import { AlertCircle, CalendarClock, Cake, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { useAuth } from '@/features/auth/useAuth'
import { formatDayMonth } from '@/features/billing/labels'
import { useDashboardSummary } from '@/features/dashboard/api'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { HorizontalBars } from '@/features/dashboard/components/HorizontalBars'
import { MonthlyEnrollmentsChart } from '@/features/dashboard/components/MonthlyEnrollmentsChart'
import { StatTile } from '@/features/dashboard/components/StatTile'
import { StudentRow } from '@/features/dashboard/components/StudentRow'
import {
  activeStudents,
  ageGroups,
  birthdaysThisMonth,
  enrollmentsByMonth,
  studentsByModality,
} from '@/features/dashboard/mock-data'
import { formatMoney } from '@/lib/money'

const iconProps = { className: 'size-5', strokeWidth: 1.6 }

export function DashboardPage() {
  const { master } = useAuth()
  // Primeiro nome do mestre logado (ex.: "Mestre Teste" → "Mestre")
  const firstName = master?.name.split(' ')[0]
  // Inadimplentes e vencimentos: dados reais da API
  const summary = useDashboardSummary()
  const billing = summary.data

  return (
    <div className="space-y-4">
      <PageHeader title={firstName ? `Olá, ${firstName}` : 'Dashboard'} />

      {/* Números do topo: 2 colunas no celular, 4 no desktop */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Alunos ativos" value={activeStudents} icon={<Users {...iconProps} />} />
        <StatTile
          label="Inadimplentes"
          value={billing?.overdue_students ?? '—'}
          tone="critical"
          icon={<AlertCircle {...iconProps} />}
        />
        <StatTile
          label="Vencem em 7 dias"
          value={billing?.due_soon_students ?? '—'}
          tone="warning"
          icon={<CalendarClock {...iconProps} />}
        />
        <StatTile
          label="Aniversariantes do mês"
          value={birthdaysThisMonth.length}
          icon={<Cake {...iconProps} />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard
          title="Inadimplentes"
          subtitle="Mensalidades vencidas e não pagas"
          action={<SeeAll to="/app/mensalidades" />}
        >
          <BillingList
            loading={summary.isLoading && !billing}
            failed={!billing && Boolean(summary.error)}
            empty="Ninguém em atraso 🎉"
          >
            {billing?.overdue.map((student) => (
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
          </BillingList>
        </DashboardCard>

        <DashboardCard
          title="Vencimentos dos próximos 7 dias"
          action={<SeeAll to="/app/mensalidades?filtro=a-vencer" />}
        >
          <BillingList
            loading={summary.isLoading && !billing}
            failed={!billing && Boolean(summary.error)}
            empty="Nenhum vencimento nos próximos 7 dias"
          >
            {billing?.due_soon.map((charge, index) => (
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
          </BillingList>
        </DashboardCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <DashboardCard title="Novas matrículas por mês" className="lg:col-span-3">
          <MonthlyEnrollmentsChart data={enrollmentsByMonth} />
        </DashboardCard>
        <DashboardCard
          title="Alunos por modalidade"
          subtitle="Matrículas ativas"
          className="lg:col-span-2"
        >
          <HorizontalBars data={studentsByModality} />
        </DashboardCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard title="Faixa etária" subtitle="Alunos ativos">
          <HorizontalBars data={ageGroups} />
        </DashboardCard>

        <DashboardCard title="Aniversariantes de outubro">
          <ul className="space-y-1">
            {birthdaysThisMonth.map((person) => (
              <StudentRow
                key={person.id}
                studentId={person.id}
                name={person.name}
                detail={`Faz ${person.turningAge} anos`}
                trailing={
                  <p className="text-sm font-medium">
                    {String(person.day).padStart(2, '0')}/10
                  </p>
                }
              />
            ))}
          </ul>
        </DashboardCard>
      </div>
    </div>
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

// Lista do dashboard com os estados "carregando", "falhou" e "vazia"
function BillingList({
  loading,
  failed,
  empty,
  children,
}: {
  loading: boolean
  failed: boolean
  empty: string
  children: ReactNode[] | undefined
}) {
  if (loading) {
    return <p className="text-sm text-muted-foreground">Carregando…</p>
  }
  if (failed) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Não foi possível carregar.
      </p>
    )
  }
  if (!children || children.length === 0) {
    return <p className="text-sm text-muted-foreground">{empty}</p>
  }
  return <ul className="space-y-1">{children}</ul>
}
