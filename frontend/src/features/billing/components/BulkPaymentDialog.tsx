import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { todayIso } from '@/features/belts/rules'
import { createBulkPayments } from '@/features/billing/api'
import type { BillingOverviewItem } from '@/features/billing/api'
import { PAYMENT_METHOD_LABELS } from '@/features/billing/labels'
import type { PaymentMethod } from '@/features/billing/labels'
import { showApiError } from '@/lib/api/errors'
import { useMutation } from '@/lib/hooks/useMutation'
import { formatMoney } from '@/lib/money'

const NO_METHOD = 'none'

type BulkPaymentDialogProps = {
  // Alunos selecionados; vazio = fechado
  items: BillingOverviewItem[]
  onClose: () => void
  onDone: () => void
}

// Baixa em lote: para quem pagou exatamente o que estava em aberto. Os
// valores não se editam aqui; quem pagou diferente dá baixa na própria linha.
export function BulkPaymentDialog({
  items,
  onClose,
  onDone,
}: BulkPaymentDialogProps) {
  const [paidOn, setPaidOn] = useState(todayIso)
  const [method, setMethod] = useState<string>('pix')
  const bulk = useMutation(createBulkPayments)
  const total = items.reduce((sum, item) => sum + Number(item.open_amount), 0)

  async function confirm() {
    try {
      const result = await bulk.mutate({
        paid_on: paidOn,
        method: method === NO_METHOD ? null : (method as PaymentMethod),
        items: items.map((item) => ({
          student_id: item.student_id,
          amount: item.open_amount,
        })),
      })
      toast.success(
        `Baixa de ${result.count} ${result.count === 1 ? 'aluno' : 'alunos'} registrada · ${formatMoney(result.total)}`,
      )
      onDone()
      onClose()
    } catch (error) {
      showApiError(error)
    }
  }

  return (
    <Dialog
      open={items.length > 0}
      onOpenChange={(open) => !open && !bulk.isPending && onClose()}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Dar baixa em {items.length}{' '}
            {items.length === 1 ? 'aluno' : 'alunos'}
          </DialogTitle>
          <DialogDescription>
            Cada um quita o valor em aberto da linha. Quem pagou um valor
            diferente: tire da seleção e dê baixa na própria linha.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="bulk-paid-on" className="text-xs text-muted-foreground">
              Data do pagamento
            </Label>
            <Input
              id="bulk-paid-on"
              type="date"
              className="rounded-xl"
              value={paidOn}
              onChange={(event) => setPaidOn(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Forma</Label>
            <Select value={method} onValueChange={setMethod}>
              <SelectTrigger className="w-full rounded-xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_METHOD}>Não informar</SelectItem>
                {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <ul className="max-h-60 divide-y overflow-y-auto rounded-2xl border text-sm">
          {items.map((item) => (
            <li
              key={item.student_id}
              className="flex items-center justify-between gap-3 px-3 py-2"
            >
              <span className="min-w-0 truncate">{item.name}</span>
              <span className="font-medium whitespace-nowrap">
                {formatMoney(item.open_amount)}
              </span>
            </li>
          ))}
        </ul>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm">
            Total{' '}
            <span className="font-semibold">
              {formatMoney(total.toFixed(2))}
            </span>
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              className="rounded-full"
              disabled={bulk.isPending}
              onClick={onClose}
            >
              Cancelar
            </Button>
            <Button
              className="rounded-full"
              disabled={bulk.isPending || !paidOn}
              onClick={() => void confirm()}
            >
              Confirmar baixa
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
