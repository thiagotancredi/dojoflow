import { useState } from 'react'
import type { ReactNode } from 'react'

import { PageHeader } from '@/components/PageHeader'
import { useDashboardSummary } from '@/features/dashboard/api'
import type { DashboardSummary } from '@/features/dashboard/api'
import { BeltCountsCard } from '@/features/dashboard/components/BeltCountsCard'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { HorizontalBars } from '@/features/dashboard/components/HorizontalBars'
import { IncompleteCard } from '@/features/dashboard/components/IncompleteCard'
import { NewStudentsChart } from '@/features/dashboard/components/NewStudentsChart'
import { SexCard } from '@/features/dashboard/components/SexCard'
import { StudentRow } from '@/features/dashboard/components/StudentRow'
import { useMediaQuery } from '@/lib/hooks/useMediaQuery'
import { cn } from '@/lib/utils'

type AgeGroup = DashboardSummary['age_groups']['all'][number]

const AGE_LABELS: Record<AgeGroup['group'], string> = {
  kids: 'Kids (até 12)',
  juvenile: 'Juvenil (13–17)',
  adult: 'Adulto (18–39)',
  master: 'Master (40+)',
  unknown: 'Sem data de nascimento',
}

// Estatísticas dos alunos (o dinheiro fica no Financeiro), versão "sem
// títulos": três linhas de cartões, sem números no topo.
export function StatisticsPage() {
  const summary = useDashboardSummary()
  const data = summary.data
  // Estado comum dos cartões enquanto o resumo não chega
  const pending = !data ? (
    <CardState loading={summary.isLoading} />
  ) : null
  const monthName = new Date().toLocaleDateString('pt-BR', { month: 'long' })
  const isMobile = useMediaQuery('(max-width: 767px)')

  const newStudents = data?.new_students_by_month ?? []
  const noNewStudents = newStudents.every((item) => item.count === 0)

  return (
    <div className="space-y-4">
      <PageHeader title="Estatísticas" />

      {/* Linha 1: aniversariantes, faixa etária, por modalidade */}
      <div className="grid gap-4 lg:grid-cols-3">
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

        <AgeGroupsCard data={data} pending={pending} />

        <DashboardCard
          title="Por modalidade"
          subtitle={
            data
              ? `${data.active_students} ${data.active_students === 1 ? 'aluno ativo' : 'alunos ativos'}`
              : 'Alunos ativos'
          }
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
      </div>

      {/* Linha 2: alunos por faixa e, ao lado, sexo e cadastro incompleto */}
      {data ? (
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <BeltCountsCard data={data.by_belt} />
          <div className="min-w-0 space-y-4">
            <SexCard data={data.by_sex} />
            <IncompleteCard data={data.incomplete} />
          </div>
        </div>
      ) : (
        <DashboardCard title="Alunos por faixa">{pending}</DashboardCard>
      )}

      {/* Linha 3: novos alunos (12 meses; no celular, os 6 últimos) */}
      <DashboardCard
        title="Novos alunos por mês"
        subtitle={isMobile ? 'Últimos 6 meses' : 'Últimos 12 meses'}
      >
        {pending ??
          (noNewStudents ? (
            <Empty>Nenhum aluno novo no período.</Empty>
          ) : (
            <NewStudentsChart
              data={isMobile ? newStudents.slice(-6) : newStudents}
            />
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
