import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
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
import type { Charge } from '@/features/billing/api'
import { useUpdateCharge } from '@/features/billing/hooks'
import { applyFieldErrors, showApiError } from '@/lib/api/errors'
import { moneyToInput, parseMoney } from '@/lib/money'

const editSchema = z
  .object({
    amount: z.string(),
    due_date: z.string().min(1, { error: 'Informe o vencimento.' }),
  })
  .check((context) => {
    const parsed = parseMoney(context.value.amount)
    if (parsed === null || Number(parsed) <= 0) {
      context.issues.push({
        code: 'custom',
        path: ['amount'],
        message: 'Informe o valor. Ex.: 150,00',
        input: context.value.amount,
      })
    }
  })

type EditValues = z.infer<typeof editSchema>

type EditChargeDialogProps = {
  studentId: string
  // null = janela fechada
  charge: Charge | null
  title: string
  onClose: () => void
  onDone: () => void
}

// Muda valor e vencimento de uma cobrança que ainda não tem pagamento
export function EditChargeDialog({
  studentId,
  charge,
  title,
  onClose,
  onDone,
}: EditChargeDialogProps) {
  return (
    <Dialog open={charge !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar cobrança · {title}</DialogTitle>
        </DialogHeader>
        {charge && (
          <EditForm
            studentId={studentId}
            charge={charge}
            onCancel={onClose}
            onSaved={() => {
              onDone()
              onClose()
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function EditForm({
  studentId,
  charge,
  onCancel,
  onSaved,
}: {
  studentId: string
  charge: Charge
  onCancel: () => void
  onSaved: () => void
}) {
  const { mutate, isPending } = useUpdateCharge(studentId)
  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      amount: moneyToInput(charge.amount),
      due_date: charge.due_date,
    },
  })
  const {
    register,
    control,
    formState: { errors },
  } = form

  async function save(values: EditValues) {
    try {
      await mutate(charge.id, {
        amount: parseMoney(values.amount) as string,
        due_date: values.due_date,
      })
      toast.success('Cobrança salva')
      onSaved()
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label="Valor (R$) *"
          htmlFor="charge-amount"
          error={errors.amount?.message}
        >
          <Input
            id="charge-amount"
            inputMode="decimal"
            className="rounded-xl"
            {...register('amount')}
          />
        </FormField>
        <FormField
          label="Vencimento *"
          htmlFor="charge-due"
          error={errors.due_date?.message}
        >
          <Controller
            control={control}
            name="due_date"
            render={({ field }) => (
              <DateField
                id="charge-due"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FormField>
      </div>
      <p className="text-xs text-muted-foreground">
        Mudar o valor da matrícula não muda as cobranças já criadas; use esta
        edição para corrigir uma delas.
      </p>
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          className="rounded-full"
          onClick={onCancel}
        >
          Cancelar
        </Button>
        <Button type="submit" className="rounded-full" disabled={isPending}>
          {isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </div>
    </form>
  )
}
