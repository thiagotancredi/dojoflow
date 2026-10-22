import { cn } from '@/lib/utils'

type MonthCount = { month: string; count: number }

// "2026-10-01" → "out"
function monthLabel(isoMonth: string) {
  return new Date(`${isoMonth}T12:00:00`)
    .toLocaleDateString('pt-BR', { month: 'short' })
    .replace('.', '')
}

// Barras verticais de uma cor, com o número em cima de cada uma e o mês
// embaixo (o mês atual com o nome em negrito).
export function NewStudentsChart({ data }: { data: MonthCount[] }) {
  const max = Math.max(...data.map((item) => item.count), 1)
  const lastIndex = data.length - 1

  return (
    <ul className="flex h-44 items-end gap-3 pt-2">
      {data.map((item, index) => {
        const current = index === lastIndex
        return (
          <li
            key={item.month}
            className="flex h-full flex-1 flex-col items-center justify-end gap-1.5"
          >
            <span
              className={cn(
                'text-sm font-semibold',
                item.count === 0 && 'text-muted-foreground',
              )}
            >
              {item.count}
            </span>
            {/* Área da barra: a altura em % é relativa a ela */}
            <div className="flex w-full flex-1 items-end justify-center">
              <div
                className="w-full max-w-10 bg-chart-1"
                // Mesmo sem alunos, uma lasquinha mostra que o mês existe
                style={{ height: `${Math.max((item.count / max) * 100, 3)}%` }}
              />
            </div>
            <span
              className={cn(
                'text-xs',
                current ? 'font-semibold' : 'text-muted-foreground',
              )}
            >
              {monthLabel(item.month)}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
