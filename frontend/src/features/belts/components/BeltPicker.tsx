import type { Belt } from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { cn } from '@/lib/utils'

type BeltPickerProps = {
  belts: Belt[]
  // id da faixa escolhida
  value: string | null
  onChange: (beltId: string) => void
  // Etiqueta pequena em alguma faixa, por id (ex.: "atual", "próxima")
  tags?: Record<string, string>
}

// Escolha de faixa pelo desenho (cadastro, nova matrícula, graduação)
export function BeltPicker({ belts, value, onChange, tags = {} }: BeltPickerProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Faixa"
      className="grid max-h-64 grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-2 overflow-y-auto p-0.5"
    >
      {belts.map((belt) => (
        <button
          key={belt.id}
          type="button"
          role="radio"
          aria-checked={value === belt.id}
          onClick={() => onChange(belt.id)}
          className={cn(
            'grid gap-1 rounded-xl border bg-card p-2 text-left text-xs',
            value === belt.id && 'border-primary ring-2 ring-primary',
          )}
        >
          <BeltDrawing belt={belt} width={120} height={18} />
          <span>{belt.name}</span>
          {tags[belt.id] && (
            <span className="text-[10px] text-primary">{tags[belt.id]}</span>
          )}
        </button>
      ))}
    </div>
  )
}

