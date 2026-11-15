import { ChartLine, GraduationCap, SlidersHorizontal, Users } from 'lucide-react'
import type { ComponentType } from 'react'

import { RealIcon } from '@/app/components/RealIcon'

// Ícone do menu: os do lucide e o "R$" desenhado à mão aceitam as mesmas
// props (className e strokeWidth)
export type NavIcon = ComponentType<{
  className?: string
  strokeWidth?: number
}>

export type NavItem = {
  to: string
  label: string
  icon: NavIcon
  // "end": só fica ativo na URL exata
  end?: boolean
}

// Uma única lista alimenta a sidebar (desktop) e a barra inferior (celular).
// O app abre no Financeiro, mesmo ele não sendo o primeiro da lista.
export const mainNavItems: NavItem[] = [
  { to: '/app/estatisticas', label: 'Estatísticas', icon: ChartLine },
  { to: '/app/alunos', label: 'Alunos', icon: Users },
  { to: '/app/financeiro', label: 'Financeiro', icon: RealIcon },
  { to: '/app/graduacoes', label: 'Graduações', icon: GraduationCap },
]

export const settingsNavItem: NavItem = {
  to: '/app/configuracoes',
  label: 'Configurações',
  icon: SlidersHorizontal,
}
