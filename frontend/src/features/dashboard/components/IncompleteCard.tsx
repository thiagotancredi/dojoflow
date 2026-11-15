import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'

import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { INCOMPLETE_ITEMS } from '@/features/dashboard/incomplete'
import type { Incomplete } from '@/features/dashboard/incomplete'

// Cadastro incompleto: tocar numa linha abre Alunos já filtrado
export function IncompleteCard({ data }: { data: Incomplete }) {
  return (
    <DashboardCard
      title="Cadastro incompleto"
      subtitle="Falta dado importante · toque para ver quem"
    >
      <ul className="space-y-1">
        {INCOMPLETE_ITEMS.map((item) => {
          const count = data[item.key]
          return (
            <li key={item.key}>
              <Link
                to={`/app/alunos?incompleto=${item.param}`}
                className="flex items-center justify-between gap-3 rounded-2xl p-2 text-sm hover:bg-accent"
              >
                <span>{item.label}</span>
                <span className="flex items-center gap-1 font-medium">
                  {count} {count === 1 ? 'aluno' : 'alunos'}
                  <ChevronRight className="size-3.5 text-muted-foreground" />
                </span>
              </Link>
            </li>
          )
        })}
      </ul>
    </DashboardCard>
  )
}
