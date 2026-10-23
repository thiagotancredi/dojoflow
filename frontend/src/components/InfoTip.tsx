import type { ReactNode } from 'react'
import { Info } from 'lucide-react'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

// O "i" ao lado de um título: tocando, abre um balão com a explicação.
// Funciona no toque (celular), não só passando o mouse.
export function InfoTip({
  label,
  children,
}: {
  // Para leitores de tela: "Sobre a situação"
  label: string
  children: ReactNode
}) {
  return (
    <Popover>
      <PopoverTrigger
        aria-label={label}
        className="inline-grid size-5 shrink-0 place-items-center rounded-full align-middle text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/40"
      >
        <Info className="size-3.5" />
      </PopoverTrigger>
      <PopoverContent className="w-80 max-w-[calc(100vw-2rem)] text-sm">
        {children}
      </PopoverContent>
    </Popover>
  )
}
