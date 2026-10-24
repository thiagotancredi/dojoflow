import { ExternalLink, TriangleAlert, Zap } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { CheckoutReview } from '@/features/billing/api'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

// Peças da baixa automática pela InfinitePay na ficha do aluno

// "Ver recibo" da InfinitePay, numa aba nova. O servidor só guarda
// endereços https da InfinitePay; a checagem aqui é uma segunda trava.
export function ReceiptLink({
  url,
  className,
}: {
  url: string | null | undefined
  className?: string
}) {
  if (!url?.startsWith('https://')) return null

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'inline-flex items-center gap-1 text-xs font-medium text-primary underline-offset-2 hover:underline',
        className,
      )}
    >
      Ver recibo <ExternalLink className="size-3" />
    </a>
  )
}

// Selo da baixa que entrou sozinha
export function AutomaticBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-chip-active-border bg-chip-active px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap text-chip-active-foreground">
      <Zap className="size-3" /> Automática · InfinitePay
    </span>
  )
}

// "2027-02-20" → "20/02"
function dayMonth(isoDate: string) {
  const [, month, day] = isoDate.split('-')
  return `${day}/${month}`
}

// Topo da aba Mensalidades: pagamentos recebidos pela InfinitePay que não
// viraram baixa porque o valor em aberto mudou no meio do caminho
export function CheckoutReviews({
  reviews,
  busy,
  onResolve,
}: {
  reviews: CheckoutReview[]
  busy: boolean
  onResolve: (review: CheckoutReview) => void
}) {
  if (reviews.length === 0) return null

  return (
    <div className="space-y-2">
      {reviews.map((review) => (
        <section
          key={review.id}
          role="alert"
          className="flex flex-col gap-3 rounded-2xl border border-status-pending/40 bg-status-pending/10 p-4 sm:flex-row sm:items-center"
        >
          <p className="flex min-w-0 flex-1 items-start gap-2 text-sm">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-status-pending" />
            <span>
              Pagamento de {formatMoney(review.amount)} recebido pela
              InfinitePay em {dayMonth(review.paid_at)}, mas o valor em aberto
              mudou. Confira e, se for o caso, lance à mão ou devolva.
            </span>
          </p>
          <div className="flex shrink-0 flex-wrap items-center gap-3">
            <ReceiptLink url={review.receipt_url} />
            <Button
              variant="outline"
              size="sm"
              className="rounded-full"
              disabled={busy}
              onClick={() => onResolve(review)}
            >
              Marcar como resolvido
            </Button>
          </div>
        </section>
      ))}
    </div>
  )
}
