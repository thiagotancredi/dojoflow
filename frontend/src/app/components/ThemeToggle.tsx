import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'

import { currentMode, saveMode } from '@/app/theme'

// Botão sol/lua da barra lateral: alterna entre tema claro e escuro
export function ThemeToggle() {
  const [mode, setMode] = useState(currentMode)
  const next = mode === 'dark' ? 'light' : 'dark'
  const label = next === 'dark' ? 'Usar tema escuro' : 'Usar tema claro'

  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={() => {
        saveMode(next)
        setMode(next)
      }}
      className="grid size-10 place-items-center rounded-full border border-sidebar-border bg-card text-sidebar-foreground transition-colors hover:text-sidebar-primary"
    >
      {mode === 'dark' ? (
        <Sun className="size-[18px]" strokeWidth={1.6} />
      ) : (
        <Moon className="size-[18px]" strokeWidth={1.6} />
      )}
    </button>
  )
}
