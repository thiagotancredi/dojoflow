import type { ColorMode } from '@/app/theme'
import { useColorMode } from '@/app/theme'
import { cn } from '@/lib/utils'

const OPTIONS: { mode: ColorMode; label: string }[] = [
  { mode: 'light', label: 'Claro' },
  { mode: 'dark', label: 'Escuro' },
]

// Aparência: claro ou escuro. Fica igual ao botão sol/lua da barra lateral
// (os dois leem o mesmo useColorMode) e funciona no celular.
export function AppearanceSetting() {
  const [mode, setMode] = useColorMode()

  return (
    <div className="max-w-xl space-y-2">
      <h3 className="text-sm font-medium">Aparência</h3>
      <div className="flex gap-1.5">
        {OPTIONS.map((option) => (
          <button
            key={option.mode}
            type="button"
            aria-pressed={mode === option.mode}
            onClick={() => setMode(option.mode)}
            className={cn(
              'rounded-full border px-4 py-1.5 text-sm',
              mode === option.mode
                ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                : 'text-muted-foreground',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
