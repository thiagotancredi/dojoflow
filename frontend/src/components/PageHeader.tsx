import type { ReactNode } from 'react'

type PageHeaderProps = {
  title: string
  // "actions" recebe qualquer JSX (ex.: um botão) — o pai decide o quê
  actions?: ReactNode
}

export function PageHeader({ title, actions }: PageHeaderProps) {
  return (
    <header className="mb-4 flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2.5">
        {/* Ícone do app só no celular (no computador o logo fica na lateral) */}
        <img
          src="/icons/icon-192.png"
          alt=""
          aria-hidden="true"
          className="size-9 shrink-0 rounded-[0.6rem] md:hidden"
        />
        <h1 className="truncate text-2xl font-semibold tracking-tight">{title}</h1>
      </div>
      {actions}
    </header>
  )
}
