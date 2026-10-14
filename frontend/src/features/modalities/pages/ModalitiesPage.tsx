import { useState } from 'react'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'

type ModalityOption = {
  id: string
  name: string
  emoji: string
  isSelected: boolean
}

// Formato de GET /api/v1/academy/modalities (dados fictícios por enquanto)
const initialOptions: ModalityOption[] = [
  { id: 'm1', name: 'Jiu-jitsu', emoji: '🥋', isSelected: true },
  { id: 'm2', name: 'Judô', emoji: '🥋', isSelected: true },
  { id: 'm3', name: 'Muay thai', emoji: '🥊', isSelected: true },
  { id: 'm4', name: 'Karatê', emoji: '🥋', isSelected: false },
  { id: 'm5', name: 'Boxe', emoji: '🥊', isSelected: false },
  { id: 'm6', name: 'Capoeira', emoji: '🤸', isSelected: false },
]

export function ModalitiesPage() {
  const [options, setOptions] = useState(initialOptions)

  function toggle(modalityId: string) {
    // Nunca alteramos o array antigo: criamos um novo com o item trocado.
    // É assim que o React percebe que algo mudou e redesenha a tela.
    setOptions((current) =>
      current.map((option) =>
        option.id === modalityId
          ? { ...option, isSelected: !option.isSelected }
          : option,
      ),
    )
  }

  return (
    <div>
      <PageHeader title="Modalidades" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {options.map((option) => (
          <div
            key={option.id}
            className="flex items-center justify-between rounded-3xl bg-card p-4"
          >
            <span className="flex items-center gap-2 font-medium">
              <span>{option.emoji}</span> {option.name}
            </span>
            <Button
              size="sm"
              variant={option.isSelected ? 'default' : 'outline'}
              className="rounded-full"
              onClick={() => toggle(option.id)}
            >
              {option.isSelected ? 'Ativa' : 'Ativar'}
            </Button>
          </div>
        ))}
      </div>
    </div>
  )
}
