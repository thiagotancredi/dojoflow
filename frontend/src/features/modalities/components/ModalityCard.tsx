import { Ellipsis } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { ModalityOption } from '@/features/modalities/api'

type ModalityCardProps = {
  option: ModalityOption
  // Abre a confirmação de remoção (quem confirma é a seção)
  onRemove: () => void
}

// Cartão de uma modalidade oferecida: situação das faixas, clique abre as
// faixas, menu ⋯ com "Ver faixas" e "Remover da academia".
export function ModalityCard({ option, onRemove }: ModalityCardProps) {
  const beltsUrl = `/app/configuracoes/modalidades/${option.id}/faixas`

  return (
    <div className="relative flex flex-col gap-2 rounded-2xl border bg-card p-4 transition-colors hover:border-ring/40">
      {/* Link "esticado" sobre o cartão inteiro: o cartão todo é clicável sem
          colocar o botão ⋯ dentro de um link (dois cliques aninhados) */}
      <Link
        to={beltsUrl}
        aria-label={`Faixas de ${option.name}`}
        className="absolute inset-0 rounded-2xl"
      />

      <div className="flex items-start justify-between">
        <span className="grid size-10 place-items-center rounded-xl bg-muted text-lg">
          {option.emoji}
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Opções de ${option.name}`}
              className="relative z-10 size-8 rounded-full"
            >
              <Ellipsis />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link to={beltsUrl}>Ver faixas</Link>
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onSelect={onRemove}>
              Remover da academia
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <p className="font-semibold">{option.name}</p>
      <BeltStatus option={option} />
    </div>
  )
}

function BeltStatus({ option }: { option: ModalityOption }) {
  if (option.belt_count === 0) {
    return (
      <div className="space-y-0.5 text-sm">
        <p className="text-muted-foreground">Sem faixas</p>
        <p className="font-medium text-sidebar-primary">Cadastrar faixas ›</p>
      </div>
    )
  }

  const pending = option.pending_belt_count

  return (
    <div className="space-y-0.5 text-sm">
      <p className="text-muted-foreground">
        {option.belt_count} {option.belt_count === 1 ? 'faixa' : 'faixas'}
      </p>
      {pending > 0 ? (
        <p className="flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-status-pending" />
          {pending} {pending === 1 ? 'aluno sem faixa' : 'alunos sem faixa'}
        </p>
      ) : (
        <p className="text-muted-foreground">todos com faixa</p>
      )}
    </div>
  )
}
