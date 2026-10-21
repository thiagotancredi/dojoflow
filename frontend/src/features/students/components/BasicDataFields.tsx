import { Controller } from 'react-hook-form'
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
import { SEX_LABELS } from '@/features/students/labels'
import type { BasicDataValues } from '@/features/students/schemas'

// O Select não aceita valor vazio: "none" representa "não informado"
const NO_SEX = 'none'

// Campos dos dados do aluno (usado na ficha e na etapa 1 do cadastro)
export function BasicDataFields({ form }: { form: UseFormReturn<BasicDataValues> }) {
  const {
    register,
    control,
    formState: { errors },
  } = form

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <FormField label="Nome *" htmlFor="name" error={errors.name?.message}>
        <Input id="name" className="rounded-xl" {...register('name')} />
      </FormField>
      <FormField
        label="Telefone"
        htmlFor="phone"
        error={errors.phone?.message}
        hint="Com DDD, só números."
      >
        <Input
          id="phone"
          inputMode="tel"
          placeholder="62999990000"
          className="rounded-xl"
          {...register('phone')}
        />
      </FormField>

      <Controller
        control={control}
        name="phone_is_whatsapp"
        render={({ field }) => (
          <div className="flex items-center gap-2 sm:col-span-2">
            <Checkbox
              id="phone_is_whatsapp"
              checked={field.value}
              onCheckedChange={(checked) => field.onChange(checked === true)}
            />
            <Label htmlFor="phone_is_whatsapp">O telefone é WhatsApp</Label>
          </div>
        )}
      />

      <FormField label="E-mail" htmlFor="email" error={errors.email?.message}>
        <Input
          id="email"
          type="email"
          className="rounded-xl"
          {...register('email')}
        />
      </FormField>
      <FormField
        label="Nascimento"
        htmlFor="birth_date"
        error={errors.birth_date?.message}
      >
        <Input
          id="birth_date"
          type="date"
          className="rounded-xl"
          {...register('birth_date')}
        />
      </FormField>

      <FormField label="Sexo" error={errors.sex?.message}>
        <Controller
          control={control}
          name="sex"
          render={({ field }) => (
            <Select
              value={field.value || NO_SEX}
              onValueChange={(value) =>
                field.onChange(value === NO_SEX ? '' : value)
              }
            >
              <SelectTrigger className="w-full rounded-xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_SEX}>Não informado</SelectItem>
                {Object.entries(SEX_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </FormField>
      <FormField
        label="CPF"
        htmlFor="cpf"
        error={errors.cpf?.message}
        hint="11 números, sem pontos."
      >
        <Input
          id="cpf"
          inputMode="numeric"
          maxLength={11}
          className="rounded-xl"
          {...register('cpf')}
        />
      </FormField>
      <FormField
        label="Instagram"
        htmlFor="instagram"
        error={errors.instagram?.message}
      >
        <Input
          id="instagram"
          placeholder="@usuario"
          className="rounded-xl"
          {...register('instagram')}
        />
      </FormField>
    </div>
  )
}
