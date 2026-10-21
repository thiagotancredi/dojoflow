import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import type { MockBelt } from '@/features/belts/mock'
import { cn } from '@/lib/utils'

type BeltPickerProps = {
  belts: MockBelt[]
  value: string | null
  onChange: (beltName: string) => void
  // Etiqueta pequena em alguma faixa (ex.: "atual", "próxima")
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
          key={belt.name}
          type="button"
          role="radio"
          aria-checked={value === belt.name}
          onClick={() => onChange(belt.name)}
          className={cn(
            'grid gap-1 rounded-xl border bg-card p-2 text-left text-xs',
            value === belt.name && 'border-primary ring-2 ring-primary',
          )}
        >
          <BeltDrawing belt={belt} width={120} height={18} />
          <span>{belt.name}</span>
          {tags[belt.name] && (
            <span className="text-[10px] text-primary">{tags[belt.name]}</span>
          )}
        </button>
      ))}
    </div>
  )
}
