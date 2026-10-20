import { AlertCircle, CalendarClock, Cake, Users } from 'lucide-react'

import { PageHeader } from '@/components/PageHeader'
import { useAuth } from '@/features/auth/useAuth'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { HorizontalBars } from '@/features/dashboard/components/HorizontalBars'
import { MonthlyEnrollmentsChart } from '@/features/dashboard/components/MonthlyEnrollmentsChart'
import { StatTile } from '@/features/dashboard/components/StatTile'
import { StudentRow } from '@/features/dashboard/components/StudentRow'
import {
  activeStudents,
  ageGroups,
  birthdaysThisMonth,
  dueSoonStudents,
  enrollmentsByMonth,
  overdueStudents,
  studentsByModality,
} from '@/features/dashboard/mock-data'

const iconProps = { className: 'size-5', strokeWidth: 1.6 }

export function DashboardPage() {
  const { master } = useAuth()
  // Primeiro nome do mestre logado (ex.: "Mestre Teste" → "Mestre")
  const firstName = master?.name.split(' ')[0]

  return (
    <div className="space-y-4">
      <PageHeader title={firstName ? `Olá, ${firstName}` : 'Dashboard'} />

      {/* Números do topo: 2 colunas no celular, 4 no desktop */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Alunos ativos" value={activeStudents} icon={<Users {...iconProps} />} />
        <StatTile
          label="Inadimplentes"
          value={overdueStudents.length}
          tone="critical"
          icon={<AlertCircle {...iconProps} />}
        />
        <StatTile
          label="Vencem em 7 dias"
          value={dueSoonStudents.length}
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
        <DashboardCard title="Inadimplentes" subtitle="Mensalidades vencidas e não pagas">
          <ul className="space-y-1">
            {overdueStudents.map((student) => (
              <StudentRow
                key={student.id}
                studentId={student.id}
                name={student.name}
                detail={student.modality}
                trailing={
                  <>
                    <p className="text-sm font-medium">R$ {student.amount}</p>
                    <p className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
                      <AlertCircle className="size-3.5 text-status-critical" />
                      {student.daysLate} dias em atraso
                    </p>
                  </>
                }
              />
            ))}
          </ul>
        </DashboardCard>

        <DashboardCard title="Vencimentos dos próximos 7 dias">
          <ul className="space-y-1">
            {dueSoonStudents.map((student) => (
              <StudentRow
                key={student.id}
                studentId={student.id}
                name={student.name}
                detail={student.modality}
                trailing={
                  <>
                    <p className="text-sm font-medium">R$ {student.amount}</p>
                    <p className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
                      <CalendarClock className="size-3.5 text-status-warning" />
                      vence {student.dueDate}
                    </p>
                  </>
                }
              />
            ))}
          </ul>
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
