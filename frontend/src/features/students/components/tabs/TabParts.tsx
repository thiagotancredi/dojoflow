import type { ReactNode } from 'react'
import { Plus } from 'lucide-react'

import { SectionMenu } from '@/features/students/components/tabs/SectionMenu'
import { useSectionMenu } from '@/features/students/components/tabs/sections'
import { cn } from '@/lib/utils'

// Peças comuns das abas da ficha: título com ações à direita e cartões
// com um rótulo pequeno em cima

// Topo de cada seção da ficha. O conteúdo vem direto, sem título na tela:
// no computador a aba verde já diz onde você está; no celular/tablet
// ("@max-xl/ficha": ficha com menos de 36rem) aparece a barra
// "trocar seção". O título fica só para leitores de tela (sr-only).
export function TabHeader({ title }: { title: string }) {
  const menu = useSectionMenu()

  return (
    <>
      <h3 className={menu ? 'sr-only' : 'font-semibold'}>{title}</h3>
      {menu && <SectionMenu className="@xl/ficha:hidden" />}
    </>
  )
}

export function InfoCard({
  title,
  action,
  children,
  className = '',
}: {
  title?: string
  // Botão do canto do cartão (ex.: "Editar"), na linha do título
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`rounded-2xl border bg-popover p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-3 flex min-h-7 items-center justify-between gap-2">
          {title && (
            <p className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
              {title}
            </p>
          )}
          {action && <div className="ml-auto flex gap-1">{action}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

// Cartão tracejado de "adicionar" (responsável, matrícula…): fica no fim
// da lista, no lugar de um botão solto no topo
export function AddCard({
  label,
  onClick,
  className,
}: {
  label: string
  onClick: () => void
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full flex-col items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed text-sm font-medium text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground',
        className,
      )}
    >
      <Plus className="size-5" />
      {label}
    </button>
  )
}

// Valor de um campo; vazio vira "Não informado", mais claro que um traço
export function Field({ label, children }: { label: string; children: ReactNode }) {
  const empty = children === null || children === undefined || children === ''

  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={empty ? 'text-sm text-muted-foreground/70' : 'text-sm'}>
        {empty ? 'Não informado' : children}
      </dd>
    </div>
  )
}
