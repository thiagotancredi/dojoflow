import type { ReactNode } from 'react'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

// Painel do aluno no celular: a janela padrão, que no celular sobe de
// baixo (gaveta) e no computador abre no meio. Título, uma linha embaixo
// (ex.: "Cobrança vai para…") e um atalho à direita (ex.: "Ver ficha ›").
export function BottomSheet({
  title,
  subtitle,
  action,
  onClose,
  children,
}: {
  title: string
  subtitle?: ReactNode
  action?: ReactNode
  onClose: () => void
  children: ReactNode
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent showCloseButton={false}>
        <DialogHeader className="flex-row items-start justify-between gap-3 text-left">
          <div className="min-w-0">
            <DialogTitle className="leading-snug">{title}</DialogTitle>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {action}
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  )
}

// Quadro com título pequeno em maiúsculas (ex.: "Cobrança", "Faixa")
export function SheetBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border bg-card p-3">
      <p className="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
        {title}
      </p>
      {children}
    </section>
  )
}

// Linha "rótulo ........ valor" dentro de um SheetBlock
export function SheetRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  )
}
