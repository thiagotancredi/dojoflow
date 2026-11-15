import { ChevronRight, GraduationCap, Wallet } from 'lucide-react'
import { Fragment } from 'react'
import type { ReactNode } from 'react'

import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import type { Charge } from '@/features/billing/api'
import { AutomaticInfo, ChargeMenu } from '@/features/billing/components/ChargeMenu'
import type { ChargeHandlers } from '@/features/billing/history'
import { ChargeStatusChip } from '@/features/billing/components/ChargeStatusChip'
import { chargeDetail } from '@/features/billing/history'
import type { ChargePayment } from '@/features/billing/statement'
import { formatMoney } from '@/lib/money'

// Histórico do aluno: mensalidades e graduações numa lista só, da mais nova
// para a mais antiga, com o ano como separador
export function HistoryList({
  charges,
  byCharge,
  handlers,
  onOpen,
}: {
  charges: Charge[]
  byCharge: Map<string, ChargePayment[]>
  handlers: ChargeHandlers
  onOpen: (charge: Charge) => void
}) {
  const sorted = [...charges].sort((a, b) => b.due_date.localeCompare(a.due_date))
  return (
    <ul>
      {sorted.map((charge, index) => {
        const year = charge.due_date.slice(0, 4)
        const showYear = index === 0 || sorted[index - 1].due_date.slice(0, 4) !== year
        const payments = byCharge.get(charge.id) ?? []
        return (
          <Fragment key={charge.id}>
            {showYear && (
              <li className="pt-3 pb-1 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase first:pt-0">
                {year}
              </li>
            )}
            <li className="border-b last:border-0">
              {/* Computador: tudo na linha, com o "⋯" */}
              <div className="hidden items-center gap-4 py-3 md:flex">
                <KindIcon charge={charge} />
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    <Title charge={charge} />
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {chargeDetail(charge, payments)}
                  </p>
                  {/* Baixa automática: selo da InfinitePay e o recibo */}
                  {payments[0] && (
                    <div className="mt-1 text-xs">
                      <AutomaticInfo payment={payments[0].payment} />
                    </div>
                  )}
                </div>
                <ChargeStatusChip status={charge.status} />
                <p className="w-28 text-right font-semibold tabular-nums">
                  {formatMoney(charge.amount)}
                </p>
                <ChargeMenu charge={charge} chargePayments={payments} {...handlers} />
              </div>
              {/* Celular: tocar abre o painel com as mesmas ações */}
              <button
                type="button"
                onClick={() => onOpen(charge)}
                className="flex w-full items-center gap-3 py-3 text-left md:hidden"
              >
                <KindIcon charge={charge} small />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">
                    <Title charge={charge} short />
                  </span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {chargeDetail(charge, payments)}
                  </span>
                </span>
                <span className="shrink-0 text-right">
                  <span className="block font-semibold">{formatMoney(charge.amount)}</span>
                  <ChargeStatusChip status={charge.status} />
                </span>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </button>
            </li>
          </Fragment>
        )
      })}
    </ul>
  )
}

function KindIcon({ charge, small }: { charge: Charge; small?: boolean }) {
  const Icon = charge.kind === 'graduation' ? GraduationCap : Wallet
  return (
    <span
      className={
        small
          ? 'grid size-9 shrink-0 place-items-center rounded-2xl bg-accent text-primary'
          : 'grid size-10 shrink-0 place-items-center rounded-2xl bg-accent text-primary'
      }
    >
      <Icon className={small ? 'size-4' : 'size-5'} />
    </span>
  )
}

// "Mensalidade · Novembro", "Taxa de matrícula" ou "Graduação ▬ Verde"
export function Title({ charge, short }: { charge: Charge; short?: boolean }): ReactNode {
  if (charge.kind === 'graduation') {
    return (
      <span className="inline-flex items-center gap-1.5">
        {!short && 'Graduação'}
        {charge.graduation && (
          <BeltDrawing belt={charge.graduation.belt} width={26} height={9} className="shrink-0" />
        )}
        {charge.description}
      </span>
    )
  }
  if (charge.kind === 'enrollment_fee') return 'Taxa de matrícula'
  const month = new Date(`${charge.reference_month}T12:00:00`).toLocaleDateString(
    'pt-BR',
    { month: 'long' },
  )
  const name = month.charAt(0).toUpperCase() + month.slice(1)
  return short ? name : `Mensalidade · ${name}`
}
