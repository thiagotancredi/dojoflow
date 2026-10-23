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

// O título da seção vira um botão ("Matrículas ▾") que abre a lista
export function SectionMenu({ className }: { className?: string }) {
  const menu = useSectionMenu()
  if (!menu) return null

  const current =
    STUDENT_SECTIONS.find((section) => section.value === menu.value) ??
    STUDENT_SECTIONS[0]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'flex items-center gap-1 rounded-lg text-lg font-semibold tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
          className,
        )}
      >
        {current.label}
        <ChevronDown className="size-4 text-sidebar-primary" strokeWidth={2.5} />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56 rounded-2xl p-1.5">
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
