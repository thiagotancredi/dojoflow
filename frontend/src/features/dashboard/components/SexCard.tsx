import type { DashboardSummary } from '@/features/dashboard/api'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { HorizontalBars } from '@/features/dashboard/components/HorizontalBars'

type SexCount = DashboardSummary['by_sex'][number]

const SEX_LABELS: Record<NonNullable<SexCount['sex']>, string> = {
  female: 'Feminino',
  male: 'Masculino',
  other: 'Outro',
}

export function SexCard({ data }: { data: SexCount[] }) {
  return (
    <DashboardCard title="Sexo" subtitle="Alunos ativos">
      {data.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum aluno ativo ainda.</p>
      ) : (
        <HorizontalBars
          data={data.map((item) => ({
            label: item.sex ? SEX_LABELS[item.sex] : 'Não informado',
            count: item.count,
          }))}
        />
      )}
    </DashboardCard>
  )
}
