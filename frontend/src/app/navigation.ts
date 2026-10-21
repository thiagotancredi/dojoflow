import {
  LayoutGrid,
  Medal,
  SlidersHorizontal,
  Users,
  Wallet,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  // "end": só fica ativo na URL exata (senão "/app" ficaria ativo em todas)
  end?: boolean
}

// Uma única lista alimenta a sidebar (desktop) e a barra inferior (celular).
export const mainNavItems: NavItem[] = [
  { to: '/app', label: 'Dashboard', icon: LayoutGrid, end: true },
  { to: '/app/alunos', label: 'Alunos', icon: Users },
  { to: '/app/mensalidades', label: 'Mensalidades', icon: Wallet },
  { to: '/app/graduacoes', label: 'Graduações', icon: Medal },
]

export const settingsNavItem: NavItem = {
  to: '/app/configuracoes',
  label: 'Configurações',
  icon: SlidersHorizontal,
}
