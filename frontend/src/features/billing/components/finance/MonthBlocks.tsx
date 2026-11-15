import { AlertCircle } from 'lucide-react'

import type { BillingOverview } from '@/features/billing/api'
import { PAYMENT_METHOD_LABELS, formatMoneyShort } from '@/features/billing/labels'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { HorizontalBars } from '@/features/dashboard/components/HorizontalBars'
import { StudentRow } from '@/features/dashboard/components/StudentRow'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

// Os 3 blocos do mês: como pagaram, por modalidade e quem deve há mais
// tempo. No computador ficam lado a lado; no celular, um embaixo do outro
// (no painel "Ver resumo do mês").
export function MonthBlocks({
  data,
  onSeeAll,
  className,
}: {
  data: BillingOverview
  onSeeAll: () => void
  className?: string
}) {
  return (
    <div className={cn('grid gap-4 lg:grid-cols-3', className)}>
      <DashboardCard title="Como pagaram" subtitle="Recebido no mês">
        {data.by_method.length === 0 ? (
          <Empty>Nada recebido neste mês ainda.</Empty>
        ) : (
          <HorizontalBars
            data={data.by_method.map((item) => ({
              label: item.method ? PAYMENT_METHOD_LABELS[item.method] : 'Sem forma',
              count: Number(item.amount),
              display: formatMoneyShort(item.amount),
              total: Number(data.month_received),
            }))}
          />
        )}
      </DashboardCard>

      <DashboardCard title="Por modalidade" subtitle="Recebido de previsto">
        {data.by_modality.length === 0 ? (
          <Empty>Nenhuma mensalidade neste mês.</Empty>
        ) : (
          <HorizontalBars
            data={data.by_modality.map((item) => ({
              label: item.modality_name,
              count: Number(item.received),
              display: `${formatMoneyShort(item.received)} de ${Number(
                item.expected,
              ).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`,
              total: Number(item.expected),
            }))}
          />
        )}
      </DashboardCard>

      <DashboardCard
        title="Quem deve há mais tempo"
        action={
          data.longest_overdue.length > 0 && (
            <button
              type="button"
              onClick={onSeeAll}
              className="shrink-0 text-xs font-medium text-sidebar-primary hover:underline"
            >
              Ver todos
            </button>
          )
        }
      >
        {data.longest_overdue.length === 0 ? (
          <Empty>Ninguém em atraso 🎉</Empty>
        ) : (
          <ul className="space-y-1">
            {data.longest_overdue.map((student) => (
              <StudentRow
                key={student.student_id}
                studentId={student.student_id}
                name={student.name}
                detail={student.modality}
                trailing={
                  <>
                    <p className="text-sm font-medium">{formatMoney(student.amount)}</p>
                    <p className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
                      <AlertCircle className="size-3.5 text-status-critical" />
                      {student.days_late} {student.days_late === 1 ? 'dia' : 'dias'} em
                      atraso
                    </p>
                  </>
                }
              />
            ))}
          </ul>
        )}
      </DashboardCard>
    </div>
  )
}

function Empty({ children }: { children: string }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}
