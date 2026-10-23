import { zodResolver } from '@hookform/resolvers/zod'
import { Ellipsis, MapPin, Pencil } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { StudentDetail } from '@/features/students/api'
import { AddressFields } from '@/features/students/components/AddressFields'
import { FormActions } from '@/features/students/components/tabs/BasicDataTab'
import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import {
  AddCard,
  InfoCard,
  TabHeader,
} from '@/features/students/components/tabs/TabParts'
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
      <div className="space-y-4">
        <TabHeader title="Endereço" />
        {/* Sem endereço: cartão tracejado, igual a matrícula/responsável */}
        <AddCard
          label="Adicionar endereço"
          onClick={() => setEditing(true)}
          className="min-h-28"
        />
      </div>
    )
  }

  // Monta só as partes preenchidas (o endereço pode estar incompleto)
  const line1 = [address.street, address.number].filter(Boolean).join(', ')
  const line2 = [address.complement, address.neighborhood]
    .filter(Boolean)
    .join(' · ')
  const line3 = [
    [address.city, address.state].filter(Boolean).join('/'),
    address.zip_code && `CEP ${formatZip(address.zip_code)}`,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="space-y-4">
      <TabHeader title="Endereço" />
      {/* Editar/Remover no canto do cartão, como nas outras seções */}
      {/* O endereço vem direto (sem rótulo repetindo "Endereço"); Editar e
          Remover no menu "⋯" do canto, igual ao cartão de responsável */}
      <InfoCard className="flex items-start gap-4">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-chip-active text-chip-active-foreground">
          <MapPin className="size-5" />
        </span>
        <div className="min-w-0 flex-1 space-y-0.5">
          <p className="font-medium">{line1 || 'Endereço sem rua'}</p>
          {line2 && <p className="text-sm text-muted-foreground">{line2}</p>}
          {line3 && <p className="text-sm text-muted-foreground">{line3}</p>}
        </div>
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Opções do endereço"
              className="-mt-1 -mr-2 size-8 shrink-0 rounded-full"
            >
              <Ellipsis />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => setEditing(true)}>
              <Pencil /> Editar
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => setConfirming(true)}
            >
              Remover
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </InfoCard>
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
