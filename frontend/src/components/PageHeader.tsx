import type { ReactNode } from 'react'

type PageHeaderProps = {
  title: string
  // "actions" recebe qualquer JSX (ex.: um botão) — o pai decide o quê
  actions?: ReactNode
}

export function PageHeader({ title, actions }: PageHeaderProps) {
  return (
    <header className="mb-4 flex items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {actions}
    </header>
  )
}
