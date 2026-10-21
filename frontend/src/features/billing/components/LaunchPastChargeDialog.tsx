import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

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
import { useLaunchPastCharge } from '@/features/billing/hooks'
import { currentMonth, formatMonth } from '@/features/billing/labels'
import type { Enrollment } from '@/features/students/api'
import { applyFieldErrors, showApiError } from '@/lib/api/errors'
import { moneyToInput, parseMoney } from '@/lib/money'

const launchSchema = z
  .object({
    enrollment_id: z.string().min(1, { error: 'Escolha a matrícula.' }),
    month: z.string().regex(/^\d{4}-\d{2}$/, { error: 'Escolha o mês.' }),
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

type LaunchValues = z.infer<typeof launchSchema>

// "2026-10" → "2026-09"
function previousMonth(month: string) {
  const [year, value] = month.split('-').map(Number)
  const date = new Date(year, value - 2, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

// Último mês que dá para lançar nesta matrícula: o anterior ao início da
// cobrança automática; sem cobrança automática, até o mês atual.
// Ex.: ligado em 21/10 com vencimento dia 10 → começa em novembro →
// outubro entra por aqui.
function lastLaunchableMonth(enrollment: Enrollment) {
  return enrollment.billing_start_month
    ? previousMonth(enrollment.billing_start_month.slice(0, 7))
    : currentMonth()
}

// Vencimento padrão: o dia de vencimento da matrícula naquele mês
// (dia que não existe, ex.: 31 em fevereiro, vira o último dia)
function dueDateFor(month: string, dueDay: number | null) {
  if (!/^\d{4}-\d{2}$/.test(month)) return ''
  const [year, value] = month.split('-').map(Number)
  const lastDay = new Date(year, value, 0).getDate()
  const day = Math.min(dueDay ?? 10, lastDay)
  return `${month}-${String(day).padStart(2, '0')}`
}

type LaunchPastChargeDialogProps = {
  studentId: string
  enrollments: Enrollment[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onDone: () => void
}

// "Lançar mês anterior": dívida de antes da cobrança automática
export function LaunchPastChargeDialog({
  studentId,
  enrollments,
  open,
  onOpenChange,
  onDone,
}: LaunchPastChargeDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Lançar mês anterior</DialogTitle>
        </DialogHeader>
        <LaunchForm
          studentId={studentId}
          enrollments={enrollments}
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

function LaunchForm({
  studentId,
  enrollments,
  onCancel,
  onSaved,
}: {
  studentId: string
  enrollments: Enrollment[]
  onCancel: () => void
  onSaved: () => void
}) {
  const { mutate, isPending } = useLaunchPastCharge(studentId)
  const first = enrollments[0]
  const month = lastLaunchableMonth(first)
  const form = useForm<LaunchValues>({
    resolver: zodResolver(launchSchema),
    defaultValues: {
      enrollment_id: first.id,
      month,
      amount: moneyToInput(first.monthly_fee),
      due_date: dueDateFor(month, first.due_day),
    },
  })
  const {
    register,
    control,
    setValue,
    getValues,
    formState: { errors },
  } = form

  const enrollmentById = (id: string) =>
    enrollments.find((item) => item.id === id) ?? first
  const selected = enrollmentById(
    useWatch({ control, name: 'enrollment_id' }) ?? first.id,
  )
  const lastMonth = lastLaunchableMonth(selected)

  // Trocar a matrícula ou o mês sugere valor e vencimento de novo
  function suggest(enrollmentId: string, chosenMonth: string) {
    const enrollment = enrollmentById(enrollmentId)
    // Mês depois do limite desta matrícula volta para o limite
    const limit = lastLaunchableMonth(enrollment)
    const fixedMonth = chosenMonth > limit ? limit : chosenMonth
    if (fixedMonth !== getValues('month')) setValue('month', fixedMonth)
    setValue('amount', moneyToInput(enrollment.monthly_fee))
    setValue('due_date', dueDateFor(fixedMonth, enrollment.due_day))
  }

  async function save(values: LaunchValues) {
    if (values.month > lastMonth) {
      form.setError('month', {
        message: `Até ${formatMonth(`${lastMonth}-01`)} (depois disso o sistema cobra sozinho).`,
      })
      return
    }
    try {
      await mutate({
        enrollment_id: values.enrollment_id,
        reference_month: `${values.month}-01`,
        amount: parseMoney(values.amount) as string,
        due_date: values.due_date,
      })
      toast.success('Mês lançado')
      onSaved()
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Para dívidas de antes de o sistema cobrar sozinho (nesta matrícula,
        até {formatMonth(`${lastMonth}-01`)}). Um mês que já tem cobrança não
        pode ser lançado de novo.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {enrollments.length > 1 && (
          <div className="sm:col-span-2">
            <FormField label="Matrícula *" error={errors.enrollment_id?.message}>
              <Controller
                control={control}
                name="enrollment_id"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      field.onChange(value)
                      suggest(value, getValues('month'))
                    }}
                  >
                    <SelectTrigger className="w-full rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {enrollments.map((item) => (
                        <SelectItem key={item.id} value={item.id}>
                          {item.modality_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FormField>
          </div>
        )}
        <FormField
          label="Mês de referência *"
          htmlFor="launch-month"
          error={errors.month?.message}
        >
          <Input
            id="launch-month"
            type="month"
            max={lastMonth}
            className="rounded-xl"
            {...register('month', {
              onChange: (event: { target: { value: string } }) =>
                suggest(getValues('enrollment_id'), event.target.value),
            })}
          />
        </FormField>
        <FormField
          label="Valor (R$) *"
          htmlFor="launch-amount"
          error={errors.amount?.message}
        >
          <Input
            id="launch-amount"
            inputMode="decimal"
            placeholder="150,00"
            className="rounded-xl"
            {...register('amount')}
          />
        </FormField>
        <FormField
          label="Vencimento *"
          htmlFor="launch-due"
          error={errors.due_date?.message}
        >
          <Input
            id="launch-due"
            type="date"
            className="rounded-xl"
            {...register('due_date')}
          />
        </FormField>
      </div>
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
          {isPending ? 'Salvando…' : 'Lançar'}
        </Button>
      </div>
    </form>
  )
}
