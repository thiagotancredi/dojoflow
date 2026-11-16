import { Minus, Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { DateField, MonthField } from '@/components/DatePicker'
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
import type { Charge, ChargeCategory } from '@/features/billing/api'
import { useLaunchAdvance, useLaunchCharge } from '@/features/billing/hooks'
import {
  LAUNCH_OPTIONS,
  capitalize,
  currentMonth,
  formatDayMonth,
} from '@/features/billing/labels'
import type { LaunchOption } from '@/features/billing/labels'
import type { Enrollment } from '@/features/students/api'
import { showApiError } from '@/lib/api/errors'
import { toIsoDate } from '@/lib/dates'
import { formatMoney, moneyToInput, parseMoney } from '@/lib/money'

const MAX_DESCRIPTION = 120
const MONTH_NAMES = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]

// "2026-11" → "2026-12"
function nextMonth(month: string) {
  const [year, value] = month.split('-').map(Number)
  const date = new Date(year, value, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

// Vencimento da mensalidade no mês: o dia da matrícula (dia que não existe
// vira o último); no mês atual, se o dia já passou, hoje
function dueDateFor(month: string, dueDay: number | null) {
  if (!/^\d{4}-\d{2}$/.test(month)) return ''
  const [year, value] = month.split('-').map(Number)
  const lastDay = new Date(year, value, 0).getDate()
  const due = `${month}-${String(Math.min(dueDay ?? 10, lastDay)).padStart(2, '0')}`
  const today = toIsoDate(new Date())
  return month === currentMonth() && due < today ? today : due
}

// Meses do adiantamento: logo depois da última mensalidade da matrícula, ou
// a partir do mês atual (a mesma regra do servidor)
function advanceMonths(charges: Charge[], enrollment: Enrollment, count: number) {
  const last = charges
    .filter((charge) => charge.kind === 'monthly' && charge.enrollment_id === enrollment.id)
    .map((charge) => charge.reference_month.slice(0, 7))
    .sort()
    .at(-1)
  const now = currentMonth()
  let month = last ? nextMonth(last) : now
  if (month < now) month = now
  const months = [month]
  while (months.length < count) months.push(nextMonth(months[months.length - 1]))
  return months.map((item) => {
    const [year, value] = item.split('-').map(Number)
    const lastDay = new Date(year, value, 0).getDate()
    const day = Math.min(enrollment.due_day ?? 10, lastDay)
    return {
      month: item,
      name: capitalize(MONTH_NAMES[value - 1]) + (year === new Date().getFullYear() ? '' : ` de ${year}`),
      due: `${item}-${String(day).padStart(2, '0')}`,
    }
  })
}

type LaunchChargeDialogProps = {
  studentId: string
  enrollments: Enrollment[]
  charges: Charge[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onDone: () => void
}

// "Lançar cobrança": cria a dívida (mensalidade, adiantamento, matrícula ou
// uma categoria). Não manda mensagem nem gera link: quem cobra é o "Cobrar"
export function LaunchChargeDialog({ open, onOpenChange, onDone, ...props }: LaunchChargeDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Lançar cobrança</DialogTitle>
        </DialogHeader>
        {open && props.enrollments.length > 0 && (
          <LaunchForm
            {...props}
            onCancel={() => onOpenChange(false)}
            onSaved={() => {
              onDone()
              onOpenChange(false)
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function LaunchForm({
  studentId,
  enrollments,
  charges,
  onCancel,
  onSaved,
}: Omit<LaunchChargeDialogProps, 'open' | 'onOpenChange' | 'onDone'> & {
  onCancel: () => void
  onSaved: () => void
}) {
  const launch = useLaunchCharge(studentId)
  const advance = useLaunchAdvance(studentId)
  const today = toIsoDate(new Date())

  const [option, setOption] = useState<LaunchOption>('uniform')
  const [enrollmentId, setEnrollmentId] = useState(enrollments[0].id)
  const enrollment = enrollments.find((item) => item.id === enrollmentId) ?? enrollments[0]
  const [month, setMonth] = useState(currentMonth())
  const [amount, setAmount] = useState('')
  const [due, setDue] = useState(today)
  const [description, setDescription] = useState('')
  const [months, setMonths] = useState(3)
  const [errors, setErrors] = useState<{ amount?: string; description?: string; due?: string }>({})

  // Trocar o que cobrar (ou a matrícula) sugere valor e vencimento de novo
  function choose(next: LaunchOption, nextEnrollment = enrollment, nextMonth = month) {
    setOption(next)
    setErrors({})
    if (next === 'monthly') {
      setAmount(moneyToInput(nextEnrollment.monthly_fee))
      setDue(dueDateFor(nextMonth, nextEnrollment.due_day))
    } else {
      setAmount('')
      setDue(today)
    }
  }

  const preview = option === 'advance' ? advanceMonths(charges, enrollment, months) : []
  const pending = launch.isPending || advance.isPending

  async function save() {
    try {
      if (option === 'advance') {
        await advance.mutate({ enrollment_id: enrollment.id, months })
        toast.success(months === 1 ? '1 mês lançado' : `${months} meses lançados`)
        onSaved()
        return
      }

      const value = parseMoney(amount)
      const nextErrors: typeof errors = {}
      if (value === null || Number(value) <= 0) nextErrors.amount = 'Informe o valor. Ex.: 150,00'
      if (!due) nextErrors.due = 'Informe o vencimento.'
      if (option === 'other' && !description.trim()) {
        nextErrors.description = 'Escreva o que está sendo cobrado.'
      }
      setErrors(nextErrors)
      if (Object.keys(nextErrors).length > 0) return

      const base = { enrollment_id: enrollment.id, amount: value as string, due_date: due }
      if (option === 'monthly') {
        await launch.mutate({ ...base, kind: 'monthly', reference_month: `${month}-01` })
      } else if (option === 'enrollment_fee') {
        await launch.mutate({ ...base, kind: 'enrollment_fee' })
      } else {
        await launch.mutate({
          ...base,
          kind: 'extra',
          category: option as ChargeCategory,
          description: option === 'other' ? description.trim() : null,
        })
      }
      toast.success('Cobrança lançada')
      onSaved()
    } catch (error) {
      showApiError(error)
    }
  }

  return (
    <form
      noValidate
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault()
        void save()
      }}
    >
      <FormField label="O que cobrar *">
        <Select value={option} onValueChange={(value) => choose(value as LaunchOption)}>
          <SelectTrigger className="w-full rounded-xl">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LAUNCH_OPTIONS.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FormField>

      {enrollments.length > 1 && (
        <FormField label="Matrícula *">
          <Select
            value={enrollment.id}
            onValueChange={(value) => {
              setEnrollmentId(value)
              const next = enrollments.find((item) => item.id === value) ?? enrollment
              if (option === 'monthly') choose('monthly', next)
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
        </FormField>
      )}

      {option === 'advance' ? (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground">Quantos meses</p>
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                className="rounded-full"
                aria-label="Menos um mês"
                disabled={months <= 1}
                onClick={() => setMonths(months - 1)}
              >
                <Minus />
              </Button>
              <span className="w-6 text-center text-lg font-semibold">{months}</span>
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                className="rounded-full"
                aria-label="Mais um mês"
                disabled={months >= 12}
                onClick={() => setMonths(months + 1)}
              >
                <Plus />
              </Button>
            </div>
          </div>
          <ul className="space-y-1.5 rounded-2xl bg-muted p-3">
            {preview.map((item) => (
              <li key={item.month} className="flex justify-between gap-3 text-sm">
                <span>
                  {item.name}
                  <span className="text-xs text-muted-foreground">
                    {' '}
                    · vence {formatDayMonth(item.due)}
                  </span>
                </span>
                <span className="font-medium">{formatMoney(enrollment.monthly_fee)}</span>
              </li>
            ))}
            <li className="flex justify-between border-t pt-1.5 font-semibold">
              <span>Total</span>
              <span>{formatMoney((Number(enrollment.monthly_fee ?? 0) * months).toFixed(2))}</span>
            </li>
          </ul>
          <p className="text-xs text-muted-foreground">Valor normal do aluno.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {option === 'monthly' && (
            <div className="sm:col-span-2">
              <FormField label="Mês *" htmlFor="launch-month">
                <MonthField
                  id="launch-month"
                  max={currentMonth()}
                  value={month}
                  onChange={(value) => {
                    setMonth(value)
                    setDue(dueDateFor(value, enrollment.due_day))
                  }}
                />
              </FormField>
            </div>
          )}
          {option === 'other' && (
            <div className="sm:col-span-2">
              <FormField
                label="Descrição *"
                htmlFor="launch-description"
                error={errors.description}
                hint="Curta. Ex.: Kimono infantil emprestado"
              >
                <Input
                  id="launch-description"
                  className="rounded-xl"
                  maxLength={MAX_DESCRIPTION}
                  placeholder="O que está sendo cobrado"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </FormField>
            </div>
          )}
          <FormField label="Valor (R$) *" htmlFor="launch-amount" error={errors.amount}>
            <Input
              id="launch-amount"
              inputMode="decimal"
              placeholder="150,00"
              className="rounded-xl"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
          </FormField>
          <FormField label="Vencimento *" htmlFor="launch-due" error={errors.due}>
            <DateField id="launch-due" value={due} onChange={setDue} />
          </FormField>
        </div>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" className="rounded-full" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" className="rounded-full" disabled={pending}>
          {pending ? 'Salvando…' : 'Lançar'}
        </Button>
      </div>
    </form>
  )
}
