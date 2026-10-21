import { zodResolver } from '@hookform/resolvers/zod'
import { Pencil } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import type { StudentDetail } from '@/features/students/api'
import { BasicDataFields } from '@/features/students/components/BasicDataFields'
import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import { useUpdateStudent } from '@/features/students/hooks'
import { SEX_LABELS } from '@/features/students/labels'
import { basicDataSchema, toBasicDataPayload } from '@/features/students/schemas'
import type { BasicDataValues } from '@/features/students/schemas'
import { applyFieldErrors, showApiError } from '@/lib/api/errors'
import { formatDate, formatPhone } from '@/lib/format'

export function BasicDataTab({ student: detail, onChanged }: StudentTabProps) {
  const [editing, setEditing] = useState(false)
  const { student } = detail

  if (editing) {
    return (
      <BasicDataForm
        detail={detail}
        onClose={() => setEditing(false)}
        onSaved={onChanged}
      />
    )
  }

  return (
    <div className="space-y-4">
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
        <Field label="Sexo">
          {student.sex ? SEX_LABELS[student.sex] : '—'}
        </Field>
        <Field label="CPF">{student.cpf ?? '—'}</Field>
        <Field label="Instagram">{student.instagram ?? '—'}</Field>
      </dl>
      <Button
        variant="outline"
        className="rounded-full"
        onClick={() => setEditing(true)}
      >
        <Pencil /> Editar
      </Button>
    </div>
  )
}

function toFormValues({ student }: StudentDetail): BasicDataValues {
  return {
    name: student.name,
    phone: student.phone ?? '',
    phone_is_whatsapp: student.phone_is_whatsapp ?? false,
    email: student.email ?? '',
    birth_date: student.birth_date ?? '',
    sex: student.sex ?? '',
    cpf: student.cpf ?? '',
    instagram: student.instagram ?? '',
  }
}

type BasicDataFormProps = {
  detail: StudentDetail
  onClose: () => void
  onSaved: () => void
}

function BasicDataForm({ detail, onClose, onSaved }: BasicDataFormProps) {
  const { mutate, isPending } = useUpdateStudent(detail.student.id)
  const form = useForm<BasicDataValues>({
    resolver: zodResolver(basicDataSchema),
    defaultValues: toFormValues(detail),
  })

  async function save(values: BasicDataValues) {
    try {
      await mutate(toBasicDataPayload(values))
      toast.success('Dados salvos')
      onSaved()
      onClose()
    } catch (error) {
      // 422 → erro no campo; o resto (rede, 404…) → toast
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit(save)}
      className="space-y-4"
    >
      <BasicDataFields form={form} />
      <FormActions isPending={isPending} onCancel={onClose} />
    </form>
  )
}

export function FormActions({
  isPending,
  onCancel,
  submitLabel = 'Salvar',
}: {
  isPending: boolean
  onCancel: () => void
  submitLabel?: string
}) {
  return (
    <div className="flex justify-end gap-2">
      <Button
        type="button"
        variant="outline"
        className="rounded-full"
        onClick={onCancel}
      >
        Cancelar
      </Button>
      {/* Desabilitado enquanto salva: clique duplo grava uma vez só */}
      <Button type="submit" className="rounded-full" disabled={isPending}>
        {isPending ? 'Salvando…' : submitLabel}
      </Button>
    </div>
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
