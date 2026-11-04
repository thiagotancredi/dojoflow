import { CircleAlert } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import type { GraduationEntry } from '@/features/belts/api'
import { todayIso } from '@/features/belts/rules'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import { dayMonth, openAmount } from '@/features/graduations/charge'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

// Cobrança da graduação na lista: mesmo visual da linha de Mensalidades

// Alerta no topo: quem ainda não pagou (some quando ninguém deve)
export function UnpaidAlert({
  entries,
  deadline,
}: {
  entries: GraduationEntry[]
  deadline: string
}) {
  const unpaid = entries.filter((entry) => openAmount(entry) > 0)
  if (unpaid.length === 0) return null

  const total = unpaid.reduce((sum, entry) => sum + openAmount(entry), 0)
  const passed = deadline < todayIso()
  const count = unpaid.length

  return (
    <p
      role="status"
      className={cn(
        'flex items-start gap-2 rounded-2xl px-3 py-2 text-sm',
        passed
          ? 'bg-status-critical-soft text-status-critical'
          : 'bg-status-warning-soft text-foreground',
      )}
    >
      <CircleAlert className="mt-0.5 size-4 shrink-0" />
      <span>
        <span className="font-semibold">
          {count} {count === 1 ? 'aluno ainda não pagou' : 'alunos ainda não pagaram'}
        </span>{' '}
        a graduação · {formatMoney(total.toFixed(2))}
        {passed && ` · a data limite passou (${dayMonth(deadline)})`}
      </span>
    </p>
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

// "Em aberto": valor, "✓ Pago em dd/mm" ou "Sem cobrança"
export function ChargeOpen({ entry }: { entry: GraduationEntry }) {
  const charge = entry.charge
  if (!charge) return <span className="text-muted-foreground">Sem cobrança</span>
  if (charge.status === 'paid') {
    return (
      <span className="font-semibold whitespace-nowrap text-sidebar-primary">
        ✓ Pago{charge.paid_at ? ` em ${dayMonth(charge.paid_at)}` : ''}
      </span>
    )
  }
  if (charge.status === 'waived') return <span className="text-muted-foreground">Dispensada</span>

  return <span className="whitespace-nowrap">{formatMoney(charge.open_amount)}</span>
}

// "Atraso": dias depois da data limite
export function ChargeLate({ entry }: { entry: GraduationEntry }) {
  const days = entry.charge?.days_late ?? 0
  if (days <= 0 || openAmount(entry) <= 0) {
    return <span className="text-muted-foreground">—</span>
  }

  return (
    <span className="whitespace-nowrap text-status-critical">
      {days} {days === 1 ? 'dia' : 'dias'}
    </span>
  )
}

// WhatsApp e Dar baixa, como na linha de Mensalidades
export function ChargeActions({
  entry,
  onPay,
}: {
  entry: GraduationEntry
  onPay: (entry: GraduationEntry) => void
}) {
  if (openAmount(entry) <= 0) return null

  return (
    <div className="flex justify-end gap-2">
      <WhatsAppButton
        url={entry.whatsapp_url}
        studentName={entry.student_name}
        responsibleName={entry.responsible_name}
        size="sm"
      />
      <Button size="sm" className="rounded-full" onClick={() => onPay(entry)}>
        Dar baixa
      </Button>
    </div>
  )
}

// Caixinha da baixa em lote (só para quem tem algo em aberto)
export function ChargeSelect({
  entry,
  selected,
  onToggle,
}: {
  entry: GraduationEntry
  selected: Map<string, GraduationEntry>
  onToggle: (entry: GraduationEntry) => void
}) {
  if (openAmount(entry) <= 0) return <span className="block size-4" />

  return (
    <Checkbox
      aria-label={`Selecionar ${entry.student_name}`}
      checked={selected.has(entry.id)}
      onCheckedChange={() => onToggle(entry)}
      className="mt-0.5"
    />
  )
}
