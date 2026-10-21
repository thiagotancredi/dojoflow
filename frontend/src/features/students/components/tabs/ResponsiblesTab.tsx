import { zodResolver } from '@hookform/resolvers/zod'
import { Phone, Plus } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ResponsibleLink } from '@/features/students/api'
import { ResponsibleFields } from '@/features/students/components/ResponsibleFields'
import { FormActions } from '@/features/students/components/tabs/BasicDataTab'
import type { StudentTabProps } from '@/features/students/components/tabs/EnrollmentsTab'
import {
  useAddResponsible,
  useRemoveResponsible,
} from '@/features/students/hooks'
import { relationshipLabel } from '@/features/students/labels'
import {
  emptyResponsible,
  responsibleSchema,
  toResponsiblePayload,
} from '@/features/students/schemas'
import type {
  ResponsibleInput,
  ResponsibleValues,
} from '@/features/students/schemas'
import { applyFieldErrors, showApiError } from '@/lib/api/errors'
import { formatPhone } from '@/lib/format'

export function ResponsiblesTab({ student: detail, onChanged }: StudentTabProps) {
  const studentId = detail.student.id
  const [adding, setAdding] = useState(false)
  const [toRemove, setToRemove] = useState<ResponsibleLink | null>(null)
  const { mutate: remove } = useRemoveResponsible(studentId)

  async function confirmRemove() {
    if (!toRemove) return
    const link = toRemove
    setToRemove(null)
    try {
      await remove(link.id)
      toast.success('Responsável removido')
      onChanged()
    } catch (error) {
      showApiError(error)
    }
  }

  return (
    <div className="space-y-3">
      {detail.responsibles.length === 0 ? (
        // Como no bot: sem ninguém cadastrado, o próprio aluno responde por si
        <div className="space-y-1 py-4 text-center">
          <p className="text-sm font-medium">O próprio aluno é o responsável</p>
          <p className="text-xs text-muted-foreground">
            Se outra pessoa responde por ele (pai, mãe, avó…), adicione abaixo.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {detail.responsibles.map((responsible) => (
            <li
              key={responsible.id}
              className="flex items-center justify-between gap-2 rounded-xl border px-3 py-2.5 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate">
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
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="rounded-full text-destructive"
                onClick={() => setToRemove(responsible)}
              >
                Remover
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          className="rounded-full"
          onClick={() => setAdding(true)}
        >
          <Plus /> Adicionar outra pessoa
        </Button>
        <span className="text-xs text-muted-foreground">
          Para corrigir um responsável: remova e adicione de novo.
        </span>
      </div>

      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Adicionar responsável</DialogTitle>
          </DialogHeader>
          {/* Só existe com a janela aberta: cada abertura começa vazia */}
          {adding && (
            <AddResponsibleForm
              studentId={studentId}
              onClose={() => setAdding(false)}
              onSaved={onChanged}
            />
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={toRemove !== null}
        onOpenChange={(open) => !open && setToRemove(null)}
        title={`Remover ${toRemove?.name ?? ''} dos responsáveis?`}
        onConfirm={() => void confirmRemove()}
      />
    </div>
  )
}

type AddResponsibleFormProps = {
  studentId: string
  onClose: () => void
  onSaved: () => void
}

function AddResponsibleForm({
  studentId,
  onClose,
  onSaved,
}: AddResponsibleFormProps) {
  const { mutate, isPending } = useAddResponsible(studentId)
  const form = useForm<ResponsibleInput, unknown, ResponsibleValues>({
    resolver: zodResolver(responsibleSchema),
    defaultValues: emptyResponsible,
  })

  async function save(values: ResponsibleValues) {
    try {
      await mutate(toResponsiblePayload(values))
      toast.success('Responsável adicionado')
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
      <ResponsibleFields form={form} />
      <FormActions
        isPending={isPending}
        onCancel={onClose}
        submitLabel="Adicionar"
      />
    </form>
  )
}
