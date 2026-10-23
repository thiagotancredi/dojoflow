import { zodResolver } from '@hookform/resolvers/zod'
import { Ellipsis, MessageCircle, Phone } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
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
  AddCard,
  TabHeader,
} from '@/features/students/components/tabs/TabParts'
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
import { callHref, whatsappHref } from '@/lib/phone'

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
    <div className="space-y-4">
      <TabHeader title="Responsáveis" />
      <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {detail.responsibles.length === 0 && (
          // Sem ninguém cadastrado, o próprio aluno responde por si
          <li className="flex flex-col justify-center gap-1 rounded-2xl border bg-popover p-5">
            <p className="text-sm font-medium">O próprio aluno é o responsável</p>
            <p className="text-xs text-muted-foreground">
              Se outra pessoa responde por ele (pai, mãe, avó…), adicione ao
              lado.
            </p>
          </li>
        )}
        {detail.responsibles.map((responsible) => (
          <ResponsibleCard
            key={responsible.id}
            responsible={responsible}
            onRemove={() => setToRemove(responsible)}
          />
        ))}
        <li>
          <AddCard
            label="Adicionar responsável"
            onClick={() => setAdding(true)}
            className="size-full min-h-40"
          />
        </li>
      </ul>
      <p className="text-xs text-muted-foreground">
        Para corrigir um responsável: remova e adicione de novo.
      </p>

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

// Um cartão por pessoa: iniciais, nome, parentesco e os contatos
function ResponsibleCard({
  responsible,
  onRemove,
}: {
  responsible: ResponsibleLink
  onRemove: () => void
}) {
  return (
    <li className="space-y-4 rounded-2xl border bg-popover p-5">
      <div className="flex items-start justify-between gap-2">
        <span className="flex size-12 items-center justify-center rounded-full bg-chip-active font-semibold text-chip-active-foreground">
          {initials(responsible.name)}
        </span>
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Opções de ${responsible.name}`}
              className="size-8 rounded-full"
            >
              <Ellipsis />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem variant="destructive" onSelect={onRemove}>
              Remover
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="min-w-0">
        <p className="truncate font-semibold">{responsible.name}</p>
        <p className="text-sm text-muted-foreground">
          {relationshipLabel(responsible.relationship)}
        </p>
      </div>
      <dl className="divide-y text-sm">
        <ContactRow label="Telefone">
          {responsible.phone ? (
            <a
              href={callHref(responsible.phone)}
              className="flex items-center gap-1.5 font-medium text-chip-active-foreground hover:underline"
            >
              <Phone className="size-3.5" />
              {formatPhone(responsible.phone)}
            </a>
          ) : (
            <span className="text-muted-foreground">Não informado</span>
          )}
        </ContactRow>
        <ContactRow label="WhatsApp">
          {responsible.phone && responsible.phone_is_whatsapp ? (
            <a
              href={whatsappHref(responsible.phone)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 font-medium text-chip-active-foreground hover:underline"
            >
              <MessageCircle className="size-3.5" />
              Abrir conversa
            </a>
          ) : (
            <span className="text-muted-foreground">Não usa</span>
          )}
        </ContactRow>
      </dl>
    </li>
  )
}

function ContactRow({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5">
      <dt className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  )
}

// "Cláudia Martins" → "CM"
function initials(name: string) {
  const parts = name.trim().split(/\s+/)
  const first = parts[0]?.[0] ?? ''
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : ''
  return (first + last).toUpperCase()
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
