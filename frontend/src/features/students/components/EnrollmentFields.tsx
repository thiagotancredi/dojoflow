import { Controller, useWatch } from 'react-hook-form'
import type { UseFormReturn } from 'react-hook-form'

import { FormField } from '@/components/FormField'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { EnrollmentValues } from '@/features/students/schemas'

type ModalityChoice = { id: string; name: string }

type EnrollmentFieldsProps = {
  form: UseFormReturn<EnrollmentValues>
  // Com opções: mostra a escolha da modalidade (matrícula nova)
  modalities?: ModalityChoice[]
  // Mostra Ativa/Inativa (só na edição)
  showStatus?: boolean
  // Mostra a taxa de matrícula (só ao criar a matrícula)
  showEnrollmentFee?: boolean
  // id único por bloco (o cadastro pode ter vários na mesma tela)
  idPrefix?: string
  // Avisa quem está fora quando a modalidade muda (ex.: esconder nos outros blocos)
  onModalityChange?: (modalityId: string) => void
}

// Campos de uma matrícula (ficha e cadastro)
export function EnrollmentFields({
  form,
  modalities,
  showStatus = false,
  showEnrollmentFee = false,
  idPrefix = 'enrollment',
  onModalityChange,
}: EnrollmentFieldsProps) {
  const {
    register,
    control,
    formState: { errors },
  } = form
  // Isenta marcada → mensalidade e vencimento não se aplicam
  const isExempt = useWatch({ control, name: 'is_exempt' })
  const status = useWatch({ control, name: 'status' })
  const waiveFee = useWatch({ control, name: 'waive_enrollment_fee' })
  // Ativa e não isenta: valor e dia são obrigatórios (igual ao backend)
  const required = !isExempt && status === 'active' ? ' *' : ''
  const id = (field: string) => `${idPrefix}-${field}`

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {modalities && (
        <div className="sm:col-span-2">
          <FormField label="Modalidade *" error={errors.modality_id?.message}>
            <Controller
              control={control}
              name="modality_id"
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={(value) => {
                    field.onChange(value)
                    onModalityChange?.(value)
                  }}
                >
                  <SelectTrigger className="w-full rounded-xl">
                    <SelectValue placeholder="Escolha a modalidade" />
                  </SelectTrigger>
                  <SelectContent>
                    {modalities.map((modality) => (
                      <SelectItem key={modality.id} value={modality.id}>
                        {modality.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
        </div>
      )}

      <Controller
        control={control}
        name="is_exempt"
        render={({ field }) => (
          <div className="flex items-center gap-2 sm:col-span-2">
            <Checkbox
              id={id('exempt')}
              checked={field.value}
              onCheckedChange={(checked) => field.onChange(checked === true)}
            />
            <Label htmlFor={id('exempt')}>Isenta (não paga mensalidade)</Label>
          </div>
        )}
      />

      <FormField
        label={`Mensalidade (R$)${required}`}
        htmlFor={id('fee')}
        error={errors.monthly_fee?.message}
      >
        <Input
          id={id('fee')}
          inputMode="decimal"
          placeholder="150,00"
          disabled={isExempt}
          className="rounded-xl"
          {...register('monthly_fee')}
        />
      </FormField>
      <FormField
        label={`Dia do vencimento (1 a 28)${required}`}
        htmlFor={id('due')}
        error={errors.due_day?.message}
      >
        <Input
          id={id('due')}
          inputMode="numeric"
          placeholder="10"
          disabled={isExempt}
          className="rounded-xl"
          {...register('due_day')}
        />
      </FormField>

      {showStatus && (
        <div className="sm:col-span-2">
          <FormField label="Situação">
            <Controller
              control={control}
              name="status"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Ativa</SelectItem>
                    <SelectItem value="inactive">Inativa</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
        </div>
      )}

      {showEnrollmentFee && (
        <>
          <FormField
            label={`Taxa de matrícula (R$)${waiveFee ? '' : ' *'}`}
            htmlFor={id('enrollment-fee')}
            error={errors.enrollment_fee?.message}
          >
            <Input
              id={id('enrollment-fee')}
              inputMode="decimal"
              placeholder="80,00"
              disabled={waiveFee}
              className="rounded-xl"
              {...register('enrollment_fee')}
            />
          </FormField>
          <Controller
            control={control}
            name="waive_enrollment_fee"
            render={({ field }) => (
              <div className="flex items-center gap-2 sm:self-end sm:pb-2.5">
                <Checkbox
                  id={id('waive-fee')}
                  checked={field.value}
                  onCheckedChange={(checked) =>
                    field.onChange(checked === true)
                  }
                />
                <Label htmlFor={id('waive-fee')}>Isentar taxa</Label>
              </div>
            )}
          />
          <p className="text-xs text-muted-foreground sm:col-span-2">
            A taxa vence hoje. A primeira mensalidade é a do mês que vem.
          </p>
        </>
      )}
    </div>
  )
}
