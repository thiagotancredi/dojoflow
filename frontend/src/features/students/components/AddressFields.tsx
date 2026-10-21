import { useRef, useState } from 'react'
import type { UseFormReturn } from 'react-hook-form'

import { FormField } from '@/components/FormField'
import { Input } from '@/components/ui/input'
import { lookupCep } from '@/features/students/api'
import type { AddressValues } from '@/features/students/schemas'

type CepStatus = 'idle' | 'loading' | 'found' | 'not_found'

type AddressFieldsProps = {
  form: UseFormReturn<AddressValues>
}

// Campos de endereço + CEP automático (usado na ficha e no cadastro).
// CEP com 8 números → busca rua, bairro, cidade e UF; se não achar, os
// campos continuam livres para preencher à mão.
export function AddressFields({ form }: AddressFieldsProps) {
  const {
    register,
    setValue,
    setFocus,
    formState: { errors },
  } = form
  const [cepStatus, setCepStatus] = useState<CepStatus>('idle')
  // Busca de CEP em andamento (cancelada se o mestre digitar outro)
  const pending = useRef<AbortController | null>(null)

  async function searchCep(raw: string) {
    const zip = raw.replace(/\D/g, '')
    pending.current?.abort()

    if (zip.length !== 8) {
      setCepStatus('idle')
      return
    }

    const controller = new AbortController()
    pending.current = controller
    setCepStatus('loading')

    try {
      const found = await lookupCep(zip, controller.signal)
      const fill = { shouldDirty: true, shouldValidate: true }
      setValue('street', found.street ?? '', fill)
      setValue('neighborhood', found.neighborhood ?? '', fill)
      setValue('city', found.city, fill)
      setValue('state', found.state, fill)
      setCepStatus('found')
      setFocus('number')
    } catch {
      if (!controller.signal.aborted) setCepStatus('not_found')
    }
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <FormField
        label="CEP"
        htmlFor="zip_code"
        error={errors.zip_code?.message}
        hint={
          cepStatus === 'loading'
            ? 'Buscando CEP…'
            : cepStatus === 'found'
              ? 'Endereço preenchido pelo CEP.'
              : cepStatus === 'not_found'
                ? 'CEP não encontrado. Preencha à mão.'
                : 'Só números; o endereço vem sozinho.'
        }
      >
        <Input
          id="zip_code"
          inputMode="numeric"
          maxLength={9}
          placeholder="74000-000"
          className="rounded-xl"
          {...register('zip_code')}
          // Evento do campo (não do register): roda só quando o mestre digita
          onInput={(event) => {
            // "74000-000" colado ou digitado vira "74000000"
            const digits = event.currentTarget.value.replace(/\D/g, '').slice(0, 8)
            setValue('zip_code', digits)
            void searchCep(digits)
          }}
        />
      </FormField>
      <div className="hidden sm:block" />

      <FormField label="Rua" htmlFor="street" error={errors.street?.message}>
        <Input id="street" className="rounded-xl" {...register('street')} />
      </FormField>
      <FormField label="Número" htmlFor="number" error={errors.number?.message}>
        <Input id="number" className="rounded-xl" {...register('number')} />
      </FormField>
      <FormField
        label="Complemento"
        htmlFor="complement"
        error={errors.complement?.message}
      >
        <Input
          id="complement"
          className="rounded-xl"
          {...register('complement')}
        />
      </FormField>
      <FormField
        label="Bairro"
        htmlFor="neighborhood"
        error={errors.neighborhood?.message}
      >
        <Input
          id="neighborhood"
          className="rounded-xl"
          {...register('neighborhood')}
        />
      </FormField>
      <FormField label="Cidade" htmlFor="city" error={errors.city?.message}>
        <Input id="city" className="rounded-xl" {...register('city')} />
      </FormField>
      <FormField label="UF" htmlFor="state" error={errors.state?.message}>
        <Input
          id="state"
          maxLength={2}
          placeholder="GO"
          className="rounded-xl uppercase"
          {...register('state')}
        />
      </FormField>
    </div>
  )
}
