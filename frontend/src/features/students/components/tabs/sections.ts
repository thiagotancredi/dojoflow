import { createContext, useContext } from 'react'
import { ClipboardList, MapPin, UserRound, Users } from 'lucide-react'

import { RealIcon } from '@/app/components/RealIcon'

// Seções (abas) da ficha do aluno. Uma lista só alimenta a barra de abas
// (ficha larga) e o menu do título (ficha estreita: celular e tablet)
// Financeiro primeiro: é o que o mestre mais faz (cobrar e dar baixa)
export const STUDENT_SECTIONS = [
  { value: 'billing', label: 'Financeiro', icon: RealIcon },
  { value: 'enrollments', label: 'Matrículas', icon: ClipboardList },
  { value: 'data', label: 'Dados', icon: UserRound },
  { value: 'address', label: 'Endereço', icon: MapPin },
  { value: 'responsibles', label: 'Responsáveis', icon: Users },
] as const

export type StudentSection = (typeof STUDENT_SECTIONS)[number]['value']

type SectionMenuState = {
  value: StudentSection
  onChange: (value: StudentSection) => void
}

// Context: a ficha "empresta" a seção aberta para o TabHeader de cada aba,
// sem passar props aba por aba (parecido com uma ContextVar do Python:
// quem está dentro do Provider enxerga o valor)
const SectionMenuContext = createContext<SectionMenuState | null>(null)
export const SectionMenuProvider = SectionMenuContext.Provider

// null = fora da ficha (sem menu): o TabHeader mostra só o título
export function useSectionMenu() {
  return useContext(SectionMenuContext)
}
