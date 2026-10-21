import type { ReactNode } from 'react'

import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import { SEX_LABELS } from '@/features/students/labels'
import { formatDate, formatPhone } from '@/lib/format'

export function BasicDataTab({ student: { student } }: StudentTabProps) {
  return (
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Field label="Nome">{student.name}</Field>
      <Field label="Telefone">
        {student.phone ? formatPhone(student.phone) : '—'}
        {student.phone && student.phone_is_whatsapp && ' · WhatsApp'}
      </Field>
      <Field label="E-mail">{student.email ?? '—'}</Field>
      <Field label="Nascimento">
        {student.birth_date ? formatDate(student.birth_date) : '—'}
      </Field>
      <Field label="Sexo">{student.sex ? SEX_LABELS[student.sex] : '—'}</Field>
      <Field label="CPF">{student.cpf ?? '—'}</Field>
      <Field label="Instagram">{student.instagram ?? '—'}</Field>
    </dl>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}
