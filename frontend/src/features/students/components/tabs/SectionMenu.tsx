import { ChevronDown } from 'lucide-react'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  STUDENT_SECTIONS,
  useSectionMenu,
} from '@/features/students/components/tabs/sections'
import { cn } from '@/lib/utils'

// Barra bege "Matrículas · trocar seção ⌄" que abre a lista de seções.
// Na largura toda, para ficar claro que é um botão (e não só um título)
export function SectionMenu({ className }: { className?: string }) {
  const menu = useSectionMenu()
  if (!menu) return null

  const current =
    STUDENT_SECTIONS.find((section) => section.value === menu.value) ??
    STUDENT_SECTIONS[0]
  const Icon = current.icon

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex h-11 w-full items-center gap-2.5 rounded-full bg-accent px-4 text-left outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/40',
          className,
        )}
      >
        <Icon className="size-4 shrink-0" />
        <span className="flex-1 truncate font-semibold">{current.label}</span>
        <span className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
          trocar seção
          <ChevronDown className="size-3.5" />
        </span>
      </DropdownMenuTrigger>
      {/* Lista na largura da barra (a variável vem do Radix) */}
      <DropdownMenuContent
        align="start"
        className="w-(--radix-dropdown-menu-trigger-width) rounded-2xl p-1.5"
      >
        {STUDENT_SECTIONS.map(({ value, label, icon: Icon }) => (
          <DropdownMenuItem
            key={value}
            onSelect={() => menu.onChange(value)}
            className={cn(
              'gap-3 rounded-xl px-3 py-2.5',
              // Seção aberta: verde, inclusive quando o dedo/teclado passa
              value === menu.value &&
                'bg-sidebar-primary text-sidebar-primary-foreground focus:bg-sidebar-primary focus:text-sidebar-primary-foreground not-data-[variant=destructive]:focus:**:text-sidebar-primary-foreground',
            )}
          >
            <Icon />
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
