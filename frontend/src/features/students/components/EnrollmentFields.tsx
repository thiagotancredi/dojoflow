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
  // id único por bloco (o cadastro pode ter vários na mesma tela)
  idPrefix?: string
}

// Campos de uma matrícula (ficha e cadastro)
export function EnrollmentFields({
  form,
  modalities,
  showStatus = false,
  idPrefix = 'enrollment',
}: EnrollmentFieldsProps) {
  const {
    register,
    control,
    formState: { errors },
  } = form
  // Isenta marcada → mensalidade e vencimento não se aplicam
  const isExempt = useWatch({ control, name: 'is_exempt' })
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
                <Select value={field.value} onValueChange={field.onChange}>
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
        label="Mensalidade (R$)"
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
        label="Dia do vencimento (1 a 28)"
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

      {!isExempt && (
        <p className="text-xs text-muted-foreground sm:col-span-2">
          Mensalidade e vencimento podem ficar em branco: a matrícula aparece
          com "Pendência de cadastro".
        </p>
      )}
    </div>
  )
}
