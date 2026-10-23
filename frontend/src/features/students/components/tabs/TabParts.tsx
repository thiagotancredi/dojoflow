import type { ReactNode } from 'react'

import { SectionMenu } from '@/features/students/components/tabs/SectionMenu'
import { useSectionMenu } from '@/features/students/components/tabs/sections'
import { cn } from '@/lib/utils'

// Peças comuns das abas da ficha: título com ações à direita e cartões
// com um rótulo pequeno em cima

export function TabHeader({
  title,
  children,
  narrowOnly = false,
}: {
  title: string
  // Botões do canto direito (Editar, Remover…)
  children?: ReactNode
  // Só aparece na ficha estreita (aba sem título próprio no computador)
  narrowOnly?: boolean
}) {
  const menu = useSectionMenu()

  // "@xl/ficha": a ficha (container "ficha") tem 36rem ou mais. Abaixo
  // disso (celular, tablet) o título vira o menu de seções ("@max-xl")
  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-2',
        narrowOnly && menu && '@xl/ficha:hidden',
      )}
    >
      {menu ? (
        <>
          <h3 className="font-semibold @max-xl/ficha:hidden">{title}</h3>
          <SectionMenu className="@xl/ficha:hidden" />
        </>
      ) : (
        <h3 className="font-semibold">{title}</h3>
      )}
      {children && <div className="flex flex-wrap gap-1">{children}</div>}
    </div>
  )
}

export function InfoCard({
  title,
  children,
  className = '',
}: {
  title?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`rounded-2xl border bg-popover p-5 ${className}`}>
      {title && (
        <p className="mb-3 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
          {title}
        </p>
      )}
      {children}
    </section>
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
