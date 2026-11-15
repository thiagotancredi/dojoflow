import { useState } from 'react'

import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import type { DashboardSummary } from '@/features/dashboard/api'
import { DashboardCard } from '@/features/dashboard/components/DashboardCard'
import { cn } from '@/lib/utils'

type ModalityBelts = DashboardSummary['by_belt'][number]

// Alunos por faixa: o desenho da faixa, a barra e quantos estão nela.
// Uma modalidade de cada vez (escolha no próprio cartão).
export function BeltCountsCard({ data }: { data: ModalityBelts[] }) {
  const [modalityId, setModalityId] = useState<string | null>(null)
  // Abre na modalidade com mais alunos
  const biggest = [...data].sort((a, b) => totalOf(b) - totalOf(a))[0] ?? null
  const selected = data.find((item) => item.modality_id === modalityId) ?? biggest
  const total = selected ? totalOf(selected) : 0
  const max = Math.max(
    ...(selected?.belts.map((belt) => belt.count) ?? []),
    selected?.without_belt ?? 0,
    1,
  )

  return (
    <DashboardCard
      title="Alunos por faixa"
      subtitle={
        selected
          ? `${selected.modality_name} · ${total} ${total === 1 ? 'aluno' : 'alunos'}`
          : undefined
      }
      action={
        data.length > 1 && (
          <div className="flex flex-wrap justify-end gap-1.5">
            {data.map((item) => (
              <button
                key={item.modality_id}
                type="button"
                aria-pressed={item === selected}
                onClick={() => setModalityId(item.modality_id)}
                className={cn(
                  'shrink-0 rounded-full border px-3 py-1 text-xs',
                  item === selected
                    ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                    : 'text-muted-foreground',
                )}
              >
                {item.modality_name}
              </button>
            ))}
          </div>
        )
      }
    >
      {!selected || total === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum aluno ativo ainda.</p>
      ) : (
        <ul className="space-y-2.5">
          {selected.belts.map((belt) => (
            <Row key={belt.id} label={belt.name} count={belt.count} max={max}>
              <BeltDrawing belt={belt} width={44} height={12} className="shrink-0" />
            </Row>
          ))}
          {selected.without_belt > 0 && (
            <Row label="Sem faixa" count={selected.without_belt} max={max}>
              <span className="w-11 shrink-0" />
            </Row>
          )}
        </ul>
      )}
    </DashboardCard>
  )
}

function totalOf(item: ModalityBelts) {
  return item.belts.reduce((sum, belt) => sum + belt.count, 0) + item.without_belt
}

function Row({
  label,
  count,
  max,
  children,
}: {
  label: string
  count: number
  max: number
  children: React.ReactNode
}) {
  return (
    <li className="flex items-center gap-3 text-sm">
      {children}
      <span className="w-24 truncate">{label}</span>
      <div className="h-2.5 flex-1 rounded-full bg-muted">
        <div
          className="h-2.5 rounded-full bg-chart-1"
          style={{ width: `${(count / max) * 100}%` }}
        />
      </div>
      <span className="w-6 text-right font-medium">{count}</span>
    </li>
  )
}
