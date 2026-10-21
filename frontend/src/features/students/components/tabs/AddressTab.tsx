import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import { formatZip } from '@/lib/format'

export function AddressTab({ student: { address } }: StudentTabProps) {
  if (!address) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        Sem endereço cadastrado.
      </p>
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
    <div className="space-y-1">
      <p className="text-base">{line1 || '—'}</p>
      <p className="text-sm text-muted-foreground">{line2}</p>
    </div>
  )
}
