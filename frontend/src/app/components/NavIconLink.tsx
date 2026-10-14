import { NavLink } from 'react-router'

import type { NavItem } from '@/app/navigation'
import { cn } from '@/lib/utils'

type NavIconLinkProps = {
  item: NavItem
}

// Botão redondo de ícone vazado. O NavLink sabe se a URL atual é a dele
// e entrega "isActive" para trocarmos o estilo (círculo índigo preenchido).
export function NavIconLink({ item }: NavIconLinkProps) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={item.label}
      aria-label={item.label}
      className={({ isActive }) =>
        cn(
          'grid size-10 place-items-center rounded-full border transition-colors',
          isActive
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-sidebar-border bg-card text-sidebar-foreground hover:text-primary',
        )
      }
    >
      <Icon className="size-[18px]" strokeWidth={1.6} />
    </NavLink>
  )
}
