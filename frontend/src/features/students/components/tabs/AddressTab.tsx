import { zodResolver } from '@hookform/resolvers/zod'
import { Pencil, Plus } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import type { StudentDetail } from '@/features/students/api'
import { AddressFields } from '@/features/students/components/AddressFields'
import { FormActions } from '@/features/students/components/tabs/BasicDataTab'
import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import { useRemoveAddress, useSaveAddress } from '@/features/students/hooks'
import {
  addressSchema,
  emptyAddress,
  toAddressPayload,
} from '@/features/students/schemas'
import type { AddressValues } from '@/features/students/schemas'
import { applyFieldErrors, showApiError } from '@/lib/api/errors'
import { formatZip } from '@/lib/format'

export function AddressTab({ student: detail, onChanged }: StudentTabProps) {
  const [editing, setEditing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const { mutate: remove } = useRemoveAddress(detail.student.id)
  const { address } = detail

  async function confirmRemove() {
    setConfirming(false)
    try {
      await remove()
      toast.success('Endereço removido')
      onChanged()
    } catch (error) {
      showApiError(error)
    }
  }

  if (editing) {
    return (
      <AddressForm
        detail={detail}
        onClose={() => setEditing(false)}
        onSaved={onChanged}
      />
    )
  }

  if (!address) {
    return (
      <div className="space-y-3 py-6 text-center">
        <p className="text-sm text-muted-foreground">Sem endereço cadastrado.</p>
        <Button
          variant="outline"
          className="rounded-full"
          onClick={() => setEditing(true)}
        >
          <Plus /> Adicionar endereço
        </Button>
      </div>
    )
  }

  // Monta só as partes preenchidas (o endereço pode estar incompleto)
  const line1 = [address.street, address.number].filter(Boolean).join(', ')
  const line2 = [
    address.complement,
    address.neighborhood,
    [address.city, address.state].filter(Boolean).join('/'),
    address.zip_code && `CEP ${formatZip(address.zip_code)}`,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <p className="text-base">{line1 || '—'}</p>
        <p className="text-sm text-muted-foreground">{line2}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          className="rounded-full"
          onClick={() => setEditing(true)}
        >
          <Pencil /> Editar
        </Button>
        <Button
          variant="ghost"
          className="rounded-full text-destructive"
          onClick={() => setConfirming(true)}
        >
          Remover endereço
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Remover o endereço?"
        onConfirm={() => void confirmRemove()}
      />
    </div>
  )
}

function toFormValues({ address }: StudentDetail): AddressValues {
  if (!address) return emptyAddress

  return {
    zip_code: address.zip_code ?? '',
    street: address.street ?? '',
    number: address.number ?? '',
    complement: address.complement ?? '',
    neighborhood: address.neighborhood ?? '',
    city: address.city ?? '',
    state: address.state ?? '',
  }
}

type AddressFormProps = {
  detail: StudentDetail
  onClose: () => void
  onSaved: () => void
}

function AddressForm({ detail, onClose, onSaved }: AddressFormProps) {
  const { mutate, isPending } = useSaveAddress(detail.student.id)
  const form = useForm<AddressValues>({
    resolver: zodResolver(addressSchema),
    defaultValues: toFormValues(detail),
  })

  async function save(values: AddressValues) {
    try {
      await mutate(toAddressPayload(values))
      toast.success('Endereço salvo')
      onSaved()
      onClose()
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit(save)}
      className="space-y-4"
    >
      <AddressFields form={form} />
      <FormActions isPending={isPending} onCancel={onClose} />
    </form>
  )
}
