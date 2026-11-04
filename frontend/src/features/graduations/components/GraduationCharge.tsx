import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import type { GraduationEntry } from '@/features/belts/api'
import { todayIso } from '@/features/belts/rules'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import { dayMonth, openAmount } from '@/features/graduations/charge'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

// Cobrança da graduação na lista: mesmo visual da linha de Mensalidades

// Números do topo: quem já acertou, quem deve e quanto falta receber
export function ChargeStats({
  entries,
  deadline,
}: {
  entries: GraduationEntry[]
  deadline: string
}) {
  const settled = entries.filter(
    (entry) => entry.charge?.status === 'paid' || entry.charge?.status === 'waived',
  ).length
  const open = entries.filter((entry) => openAmount(entry) > 0).length
  const total = entries.reduce((sum, entry) => sum + openAmount(entry), 0)
  const passed = open > 0 && deadline < todayIso()

  return (
    <>
      <Stat value={settled} label="quites" className="text-sidebar-primary" />
      <Stat value={open} label="em aberto" className="text-status-pending" />
      <Stat
        value={formatMoney(total.toFixed(2))}
        label={passed ? 'total a receber · prazo passou' : 'total a receber'}
        className={passed ? 'text-status-critical' : undefined}
      />
    </>
  )
}

// Computador: número grande com a legenda embaixo.
// Celular: uma linha de extrato (legenda à esquerda, número à direita).
export function Stat({
  value,
  label,
  className,
}: {
  value: ReactNode
  label: string
  className?: string
}) {
  return (
    <div className="flex min-w-0 flex-row-reverse items-baseline justify-between gap-3 py-2 md:block md:py-0 md:text-center">
      <p
        className={cn(
          'font-semibold whitespace-nowrap md:text-xl md:tracking-tight',
          className,
        )}
      >
        {value}
      </p>
      <p className="text-sm text-muted-foreground first-letter:uppercase md:text-xs md:first-letter:normal-case">
        {label}
      </p>
    </div>
  )
}

// Linha do celular: valor (ou "✓ Pago") e o atraso em vermelho embaixo
export function ChargeShort({ entry }: { entry: GraduationEntry }) {
  const charge = entry.charge
  if (!charge) return null
  if (charge.status === 'paid') {
    return <span className="font-semibold whitespace-nowrap text-sidebar-primary">✓ Pago</span>
  }
  if (charge.status === 'waived') {
    return <span className="text-xs text-muted-foreground">Dispensada</span>
  }

  const days = charge.days_late
  return (
    <span className="text-right leading-tight whitespace-nowrap">
      <span className="block font-semibold">{formatMoney(charge.open_amount)}</span>
      {days > 0 && (
        <span className="block text-xs text-status-critical">
          {days} {days === 1 ? 'dia' : 'dias'} de atraso
        </span>
      )}
    </span>
  )
}

// Nome (com link para a ficha) e o responsável que recebe a cobrança
export function EntryName({ entry }: { entry: GraduationEntry }) {
  return (
    <p className="min-w-0">
      <Link to={`/app/alunos/${entry.student_id}`} className="font-medium hover:underline">
        {entry.student_name}
      </Link>
      {entry.responsible_name && (
        <span className="text-xs whitespace-nowrap text-muted-foreground">
          {' '}
          · resp. {entry.responsible_name.split(' ')[0]}
        </span>
      )}
    </p>
  )
}

// Coluna "Graduação": valor e, embaixo, até quando pagar ou o atraso
export function ChargeCell({ entry }: { entry: GraduationEntry }) {
  const charge = entry.charge
  if (!charge) return <span className="text-muted-foreground">Sem cobrança</span>
  if (charge.status === 'waived') return <span className="text-muted-foreground">Dispensada</span>
  if (charge.status === 'paid') {
    return (
      <div className="leading-tight whitespace-nowrap">
        <p className="font-semibold text-sidebar-primary">✓ Pago</p>
        {charge.paid_at && (
          <p className="text-xs text-muted-foreground">em {dayMonth(charge.paid_at)}</p>
        )}
      </div>
    )
  }

  const days = charge.days_late
  return (
    <div className="leading-tight whitespace-nowrap">
      <p className="font-semibold">{formatMoney(charge.open_amount)}</p>
      {days > 0 ? (
        <p className="text-xs text-status-critical">
          {days} {days === 1 ? 'dia' : 'dias'} de atraso
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">até {dayMonth(charge.due_date)}</p>
      )}
    </div>
  )
}

// WhatsApp (só o ícone) e Dar baixa, colados ao valor
export function ChargeActions({
  entry,
  onPay,
}: {
  entry: GraduationEntry
  onPay: (entry: GraduationEntry) => void
}) {
  if (openAmount(entry) <= 0) return null

  return (
    <div className="flex items-center justify-end gap-1.5">
      <WhatsAppButton
        url={entry.whatsapp_url}
        studentName={entry.student_name}
        responsibleName={entry.responsible_name}
        size="sm"
        iconOnly
      />
      <Button size="sm" className="rounded-full" onClick={() => onPay(entry)}>
        Dar baixa
      </Button>
    </div>
  )
}
