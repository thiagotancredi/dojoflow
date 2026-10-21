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
import { RELATIONSHIP_LABELS } from '@/features/students/labels'
import type {
  ResponsibleInput,
  ResponsibleValues,
} from '@/features/students/schemas'

type ResponsibleFieldsProps = {
  // Input = o que o mestre digita; Values = depois da validação (telefone só números)
  form: UseFormReturn<ResponsibleInput, unknown, ResponsibleValues>
}

// Campos de um responsável (outra pessoa), usados na ficha e no cadastro
export function ResponsibleFields({ form }: ResponsibleFieldsProps) {
  const {
    register,
    control,
    formState: { errors },
  } = form

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <FormField
        label="Nome *"
        htmlFor="responsible_name"
        error={errors.name?.message}
      >
        <Input
          id="responsible_name"
          className="rounded-xl"
          {...register('name')}
        />
      </FormField>
      <FormField label="Parentesco *" error={errors.relationship?.message}>
        <Controller
          control={control}
          name="relationship"
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger className="w-full rounded-xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(RELATIONSHIP_LABELS).map(([value, label]) => (
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
        label="Telefone *"
        htmlFor="responsible_phone"
        error={errors.phone?.message}
        hint="Com DDD."
      >
        <Input
          id="responsible_phone"
          inputMode="tel"
          placeholder="62999990000"
          className="rounded-xl"
          {...register('phone')}
        />
      </FormField>
      <FormField
        label="E-mail"
        htmlFor="responsible_email"
        error={errors.email?.message}
      >
        <Input
          id="responsible_email"
          type="email"
          className="rounded-xl"
          {...register('email')}
        />
      </FormField>
      <Controller
        control={control}
        name="phone_is_whatsapp"
        render={({ field }) => (
          <div className="flex items-center gap-2 sm:col-span-2">
            <Checkbox
              id="responsible_whatsapp"
              checked={field.value}
              onCheckedChange={(checked) => field.onChange(checked === true)}
            />
            <Label htmlFor="responsible_whatsapp">O telefone é WhatsApp</Label>
          </div>
        )}
      />
    </div>
  )
}
