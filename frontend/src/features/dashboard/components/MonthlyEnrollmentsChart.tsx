import { useState } from 'react'

import type { MonthlyEnrollments } from '@/features/dashboard/mock-data'
import { cn } from '@/lib/utils'

type Range = 6 | 12

const ALL = 'all'

type MonthlyEnrollmentsChartProps = {
  data: MonthlyEnrollments[]
}

// Colunas de uma só cor. O filtro escolhe o que é mostrado: o geral (soma de
// todas as modalidades) ou uma modalidade. Passe o mouse/toque para ver o valor.
export function MonthlyEnrollmentsChart({ data }: MonthlyEnrollmentsChartProps) {
  const [range, setRange] = useState<Range>(6)
  const [modality, setModality] = useState<string>(ALL)
  const [hovered, setHovered] = useState<number | null>(null)

  // As modalidades vêm dos próprios dados (não ficam fixas no código)
  const modalities = Object.keys(data[0]?.byModality ?? {})

  const visible = data.slice(-range).map((item) => ({
    month: item.month,
    count:
      modality === ALL
        ? Object.values(item.byModality).reduce((sum, value) => sum + value, 0)
        : (item.byModality[modality] ?? 0),
  }))
  const max = Math.max(...visible.map((item) => item.count), 1)
  const total = visible.reduce((sum, item) => sum + item.count, 0)

  return (
    <div className="space-y-3">
      {/* Filtros numa linha só, acima do gráfico */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {[ALL, ...modalities].map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setModality(option)}
              className={cn(
                'rounded-full border px-3 py-1 text-xs',
                modality === option
                  ? 'border-chip-active-border bg-chip-active font-medium text-chip-active-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {option === ALL ? 'Todas' : option}
            </button>
          ))}
        </div>
        <div className="flex rounded-full bg-muted p-0.5 text-xs">
          {([6, 12] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setRange(option)}
              className={cn(
                'rounded-full px-3 py-1',
                range === option
                  ? 'bg-card font-medium text-foreground shadow-sm'
                  : 'text-muted-foreground',
              )}
            >
              {option === 6 ? '6 meses' : '1 ano'}
            </button>
          ))}
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        <span className="text-lg font-semibold text-foreground">{total}</span>{' '}
        novas matrículas
        {modality === ALL ? '' : ` em ${modality}`}
      </p>

      <div className="flex h-44 items-end gap-0.5 border-b border-border">
        {visible.map((item, index) => (
          <div
            key={item.month}
            className="relative flex h-full flex-1 items-end justify-center"
            onMouseEnter={() => setHovered(index)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => setHovered(index)}
          >
            {hovered === index && (
              <div className="absolute -top-1 z-10 -translate-y-full rounded-lg bg-tooltip px-2 py-1 text-xs whitespace-nowrap text-tooltip-foreground">
                {item.month}: {item.count}
              </div>
            )}
            <div
              className={cn(
                'w-full max-w-6 rounded-t-[4px] bg-chart-1 transition-[height,opacity]',
                hovered !== null && hovered !== index && 'opacity-40',
              )}
              style={{ height: `${(item.count / max) * 100}%` }}
            />
          </div>
        ))}
      </div>

      <div className="flex gap-0.5 text-center text-[11px] text-muted-foreground">
        {visible.map((item) => (
          <span key={item.month} className="flex-1">
            {item.month}
          </span>
        ))}
      </div>

      {/* Versão em tabela para leitores de tela */}
      <table className="sr-only">
        <caption>
          Novas matrículas por mês{modality === ALL ? '' : ` em ${modality}`}
        </caption>
        <tbody>
          {visible.map((item) => (
            <tr key={item.month}>
              <th>{item.month}</th>
              <td>{item.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
