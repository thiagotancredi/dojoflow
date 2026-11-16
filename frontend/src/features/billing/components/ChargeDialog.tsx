import { Check, Copy } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { InfoTip } from '@/components/InfoTip'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import type { Charge, PayLink } from '@/features/billing/api'
import { WhatsAppButton } from '@/features/billing/components/WhatsAppButton'
import { useCreatePayLink } from '@/features/billing/hooks'
import { chargeLabel, daysFromToday, formatDayMonth } from '@/features/billing/labels'
import { showApiError } from '@/lib/api/errors'
import { formatMoney, moneyToInput, parseMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

const LABEL = 'text-[11px] font-semibold tracking-wider text-muted-foreground uppercase'

type ChargeDialogProps = {
  studentId: string
  studentName: string
  // Quem recebe a mensagem, quando é um responsável (aluno menor)
  responsibleName: string | null
  charges: Charge[]
  openTotal: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onDone: () => void
}

// "Cobrar": o mestre vê o que está em aberto, digita quanto cobrar e gera um
// link novo (o anterior para de funcionar). Em dois passos: o celular
// bloqueia abrir o WhatsApp ou copiar depois de esperar o servidor.
export function ChargeDialog({ open, onOpenChange, onDone, ...props }: ChargeDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next)
        if (!next) onDone()
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cobrar {props.studentName}</DialogTitle>
        </DialogHeader>
        {/* key: cada abertura começa do total, sem o link da vez anterior */}
        {open && <ChargeForm key={props.openTotal} {...props} />}
      </DialogContent>
    </Dialog>
  )
}

function ChargeForm({
  studentId,
  studentName,
  responsibleName,
  charges,
  openTotal,
}: Omit<ChargeDialogProps, 'open' | 'onOpenChange' | 'onDone'>) {
  const createLink = useCreatePayLink(studentId)
  const [value, setValue] = useState(moneyToInput(openTotal))
  const [link, setLink] = useState<PayLink | null>(null)

  // Mensalidade, taxa e avulsas em aberto, do mais antigo para o mais novo
  const items = charges
    .filter(
      (charge) =>
        charge.kind !== 'graduation' &&
        charge.status !== 'paid' &&
        charge.status !== 'waived',
    )
    .sort((a, b) => a.due_date.localeCompare(b.due_date))

  const amount = parseMoney(value)
  const total = Number(openTotal)
  const tooMuch = amount !== null && Number(amount) > total
  const invalid = amount === null || Number(amount) <= 0 || tooMuch

  async function generate() {
    if (invalid) return
    try {
      setLink(await createLink.mutate(amount))
    } catch (error) {
      showApiError(error)
    }
  }

  async function copy() {
    if (!link) return
    try {
      await navigator.clipboard.writeText(link.pay_url)
      toast.success('Link copiado')
    } catch {
      toast.error('Não foi possível copiar. Copie o link à mão.')
    }
  }

  if (link) {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-2xl bg-status-exempt-soft p-3">
          <Check className="mt-0.5 size-4 shrink-0 text-status-exempt" />
          <p className="text-sm">
            Link de <span className="font-semibold">{formatMoney(link.amount)}</span>{' '}
            gerado. O anterior parou de funcionar.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Button variant="outline" className="h-10 rounded-full" onClick={() => void copy()}>
            <Copy /> Copiar link
          </Button>
          <WhatsAppButton
            url={link.whatsapp_url}
            studentName={studentName}
            responsibleName={responsibleName}
            className="h-10 w-full"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-muted p-3">
        <p className={cn(LABEL, 'mb-2')}>Em aberto</p>
        <ul className="space-y-2">
          {items.map((charge) => {
            const late = daysFromToday(charge.due_date) < 0
            return (
              <li key={charge.id} className="flex items-baseline justify-between gap-3">
                <span className="min-w-0">
                  <span className="block truncate">{chargeLabel(charge)}</span>
                  <span
                    className={cn(
                      'text-xs',
                      late ? 'text-status-critical' : 'text-muted-foreground',
                    )}
                  >
                    {late ? 'venceu' : 'vence'} {formatDayMonth(charge.due_date)}
                  </span>
                </span>
                <span className="font-medium whitespace-nowrap">
                  {formatMoney((Number(charge.amount) - Number(charge.paid)).toFixed(2))}
                </span>
              </li>
            )
          })}
        </ul>
        <div className="mt-3 flex justify-between border-t pt-2 font-semibold">
          <span>Total</span>
          <span>{formatMoney(openTotal)}</span>
        </div>
      </div>

      <div className="space-y-1.5">
        <label htmlFor="charge-value" className="flex items-center gap-1 text-xs text-muted-foreground">
          Valor a cobrar (R$)
          <InfoTip label="Como funciona o valor">
            <p className="font-semibold">Como funciona o valor</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              O valor paga primeiro o que está em aberto há mais tempo, depois o
              seguinte, e assim por diante. O que sobrar fica pago em parte.
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Não pode passar do total em aberto. Para cobrar mais, lance a
              cobrança antes (por exemplo, um adiantamento).
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Gerar uma cobrança nova cancela o link anterior do aluno.
            </p>
          </InfoTip>
        </label>
        <Input
          id="charge-value"
          inputMode="decimal"
          className="rounded-xl text-base font-semibold"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          aria-invalid={tooMuch || undefined}
        />
        {tooMuch ? (
          <p role="alert" className="text-xs text-destructive">
            O valor passa do total em aberto ({formatMoney(openTotal)}). Lance a
            cobrança antes.
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Paga do mais antigo para o mais novo.
          </p>
        )}
      </div>

      <Button
        className="h-10 w-full rounded-full"
        disabled={invalid || createLink.isPending}
        onClick={() => void generate()}
      >
        {createLink.isPending ? 'Gerando…' : 'Gerar cobrança'}
      </Button>
    </div>
  )
}
