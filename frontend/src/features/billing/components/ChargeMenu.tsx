import { Ellipsis } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { Charge, Payment } from '@/features/billing/api'
import {
  AutomaticBadge,
  ReceiptLink,
} from '@/features/billing/components/InfinitePayBits'
import { chargeActions } from '@/features/billing/history'
import type { ChargeHandlers } from '@/features/billing/history'
import { chargeTitle } from '@/features/billing/statement'
import type { ChargePayment } from '@/features/billing/statement'

// "⋯" da linha da cobrança (computador)
export function ChargeMenu({
  charge,
  chargePayments,
  ...handlers
}: ChargeHandlers & { charge: Charge; chargePayments: ChargePayment[] }) {
  const actions = chargeActions(charge, chargePayments, handlers)
  if (actions.length === 0) return <span className="block size-8" />

  const items: ReactNode[] = []
  actions.forEach((action, index) => {
    const previous = actions[index - 1]
    if (previous && !previous.destructive && action.destructive) {
      items.push(<DropdownMenuSeparator key="sep" />)
    }
    items.push(
      <DropdownMenuItem
        key={action.key}
        variant={action.destructive ? 'destructive' : 'default'}
        onSelect={action.run}
      >
        {action.label}
      </DropdownMenuItem>,
    )
  })

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          disabled={handlers.busy}
          aria-label={`Opções de ${chargeTitle(charge)}`}
          className="size-8 rounded-full"
        >
          <Ellipsis />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">{items}</DropdownMenuContent>
    </DropdownMenu>
  )
}

// Baixa automática: o selo da InfinitePay e o recibo
export function AutomaticInfo({ payment }: { payment: Payment }) {
  if (payment.source !== 'infinitepay') return null

  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <AutomaticBadge />
      <ReceiptLink url={payment.receipt_url} />
    </span>
  )
}
