import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { DateField } from '@/components/DatePicker'
import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { todayIso } from '@/features/belts/rules'
import { previewPayment } from '@/features/billing/api'
import type { PaymentPreview } from '@/features/billing/api'
import { useCreatePayment } from '@/features/billing/hooks'
import { PAYMENT_METHOD_LABELS, capitalize } from '@/features/billing/labels'
import type { PaymentMethod } from '@/features/billing/labels'
import { applyFieldErrors, messageFor, showApiError } from '@/lib/api/errors'
import { formatMoney, parseMoney } from '@/lib/money'

const NO_METHOD = 'none'

const paymentSchema = z
  .object({
    amount: z.string(),
    paid_on: z.string().min(1, { error: 'Informe a data do pagamento.' }),
    method: z.string(),
    notes: z.string().trim().max(255, { error: 'Até 255 caracteres.' }),
  })
  .check((context) => {
    const parsed = parseMoney(context.value.amount)
    if (parsed === null || Number(parsed) <= 0) {
      context.issues.push({
        code: 'custom',
        path: ['amount'],
        message: 'Informe o valor recebido. Ex.: 150,00',
        input: context.value.amount,
      })
    }
  })

type PaymentValues = z.infer<typeof paymentSchema>

type PaymentDialogProps = {
  studentId: string
  studentName: string
  open: boolean
  onOpenChange: (open: boolean) => void
  // Depois de gravar: a tela busca os dados de novo
  onDone: () => void
}

// Janela "Dar baixa": valor, data, forma e a prévia do abatimento
export function PaymentDialog({
  studentId,
  studentName,
  open,
  onOpenChange,
  onDone,
}: PaymentDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Dar baixa · {studentName}</DialogTitle>
        </DialogHeader>
        {/* O formulário só existe com a janela aberta: abre sempre limpo */}
        <PaymentForm
          studentId={studentId}
          onCancel={() => onOpenChange(false)}
          onSaved={() => {
            onDone()
            onOpenChange(false)
          }}
        />
      </DialogContent>
    </Dialog>
  )
}

function PaymentForm({
  studentId,
  onCancel,
  onSaved,
}: {
  studentId: string
  onCancel: () => void
  onSaved: () => void
}) {
  const { mutate, isPending } = useCreatePayment()
  const form = useForm<PaymentValues>({
    resolver: zodResolver(paymentSchema),
    defaultValues: {
      amount: '',
      paid_on: todayIso(),
      method: 'pix',
      notes: '',
    },
  })
  const {
    register,
    control,
    formState: { errors },
  } = form
  const amount = parseMoney(useWatch({ control, name: 'amount' }) ?? '')
  const preview = usePaymentPreview(studentId, amount)

  async function save(values: PaymentValues) {
    try {
      await mutate(studentId, {
        amount: parseMoney(values.amount) as string,
        paid_on: values.paid_on,
        method:
          values.method === NO_METHOD
            ? null
            : (values.method as PaymentMethod),
        notes: values.notes || null,
      })
      toast.success('Baixa registrada')
      onSaved()
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label="Valor recebido (R$) *"
          htmlFor="payment-amount"
          error={errors.amount?.message}
        >
          <Input
            id="payment-amount"
            inputMode="decimal"
            placeholder="150,00"
            autoFocus
            className="rounded-xl"
            {...register('amount')}
          />
        </FormField>
        <FormField
          label="Data do pagamento *"
          htmlFor="payment-date"
          error={errors.paid_on?.message}
        >
          <Controller
            control={control}
            name="paid_on"
            render={({ field }) => (
              <DateField
                id="payment-date"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FormField>
        <FormField label="Forma (opcional)">
          <Controller
            control={control}
            name="method"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger className="w-full rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_METHOD}>Não informar</SelectItem>
                  {Object.entries(PAYMENT_METHOD_LABELS).map(
                    ([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            )}
          />
        </FormField>
        <FormField
          label="Observação (opcional)"
          htmlFor="payment-notes"
          error={errors.notes?.message}
        >
          <Input
            id="payment-notes"
            placeholder="ex.: pagou na recepção"
            className="rounded-xl"
            {...register('notes')}
          />
        </FormField>
      </div>

      <PreviewBox preview={preview} />

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          className="rounded-full"
          onClick={onCancel}
        >
          Cancelar
        </Button>
        <Button
          type="submit"
          className="rounded-full"
          disabled={isPending || preview.state === 'error'}
        >
          {isPending ? 'Salvando…' : 'Confirmar baixa'}
        </Button>
      </div>
    </form>
  )
}

type PreviewState =
  | { state: 'empty' }
  | { state: 'loading' }
  | { state: 'ready'; data: PaymentPreview }
  | { state: 'error'; message: string }

// Pede a prévia 300 ms depois que o mestre para de digitar o valor.
// O resultado fica guardado junto com o valor que o gerou: se o valor
// mudar, a prévia antiga não aparece por engano.
function usePaymentPreview(
  studentId: string,
  amount: string | null,
): PreviewState {
  const [result, setResult] = useState<{
    amount: string
    outcome: PreviewState
  } | null>(null)

  useEffect(() => {
    if (amount === null || Number(amount) <= 0) return

    const controller = new AbortController()
    const timer = setTimeout(() => {
      previewPayment(studentId, amount, controller.signal)
        .then((data) =>
          setResult({ amount, outcome: { state: 'ready', data } }),
        )
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setResult({
            amount,
            outcome: { state: 'error', message: messageFor(error) },
          })
        })
    }, 300)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [studentId, amount])

  if (amount === null || Number(amount) <= 0) return { state: 'empty' }
  if (result?.amount !== amount) return { state: 'loading' }
  return result.outcome
}

function PreviewBox({ preview }: { preview: PreviewState }) {
  return (
    <div className="space-y-2 rounded-2xl bg-muted p-4 text-sm">
      <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        Como vai ser abatido
      </p>
      {preview.state === 'empty' && (
        <p className="text-muted-foreground">
          Digite o valor para ver em quais meses ele entra (do mais antigo
          para o mais novo).
        </p>
      )}
      {preview.state === 'loading' && (
        <p className="text-muted-foreground">Calculando…</p>
      )}
      {preview.state === 'error' && (
        <p role="alert" className="text-destructive">
          {preview.message}
        </p>
      )}
      {preview.state === 'ready' && (
        <ul className="space-y-1">
          {preview.data.allocations.map((item) => (
            <li key={item.charge_id} className="flex justify-between gap-3">
              <span>{capitalize(item.label)}</span>
              <span className="text-right">
                {formatMoney(item.amount)}{' '}
                <span className="text-muted-foreground">
                  → {item.settles ? 'quitada' : 'parcial'}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
