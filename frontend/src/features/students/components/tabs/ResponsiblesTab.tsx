import { Phone } from 'lucide-react'

import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import { relationshipLabel } from '@/features/students/labels'
import { formatPhone } from '@/lib/format'

export function ResponsiblesTab({ student: { responsibles } }: StudentTabProps) {
  if (responsibles.length === 0) {
    // Como no bot: sem ninguém cadastrado, o próprio aluno responde por si
    return (
      <div className="space-y-1 py-6 text-center">
        <p className="text-sm font-medium">O próprio aluno é o responsável</p>
        <p className="text-xs text-muted-foreground">
          Se outra pessoa responde por ele (pai, mãe, avó…), adicione aqui.
        </p>
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {responsibles.map((responsible) => (
        <li
          key={responsible.id}
          className="rounded-xl border px-3 py-2.5 text-sm"
        >
          <p>
            <span className="font-medium">{responsible.name}</span>{' '}
            <span className="text-xs text-muted-foreground">
              · {relationshipLabel(responsible.relationship)}
            </span>
          </p>
          {responsible.phone && (
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Phone className="size-3" />
              {formatPhone(responsible.phone)}
              {responsible.phone_is_whatsapp && ' · WhatsApp'}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
