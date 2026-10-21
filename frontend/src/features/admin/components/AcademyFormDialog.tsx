import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { createAcademy, updateAcademy } from '@/features/admin/api'
import type { AdminAcademy, AdminCredentials } from '@/features/admin/api'
import { applyFieldErrors, messageFor, showApiError } from '@/lib/api/errors'
import { formatPhone } from '@/lib/format'
import { useMutation } from '@/lib/hooks/useMutation'

const academySchema = z.object({
  academy_name: z
    .string()
    .trim()
    .min(2, { error: 'Informe o nome da academia.' }),
  master_name: z
    .string()
    .trim()
    .min(2, { error: 'Informe o nome do mestre.' }),
  email: z.email({ error: 'Informe um e-mail válido.' }),
  phone: z.string(),
})

type AcademyValues = z.infer<typeof academySchema>

// Erros da API que pertencem ao campo de e-mail
const EMAIL_ERRORS = new Set(['EMAIL_ALREADY_REGISTERED', 'ADMIN_EMAIL_LOCKED'])

function onlyDigits(phone: string) {
  const digits = phone.replace(/\D/g, '')
  return digits ? digits : null
}

type AcademyFormDialogProps = {
  // null = fechado; 'new' = criar; academia = editar
  target: AdminAcademy | 'new' | null
  onClose: () => void
  onCreated: (result: AdminCredentials) => void
  onSaved: () => void
}

export function AcademyFormDialog({
  target,
  onClose,
  onCreated,
  onSaved,
}: AcademyFormDialogProps) {
  const isNew = target === 'new'

  return (
    <Dialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isNew ? 'Nova academia' : 'Editar academia'}
          </DialogTitle>
          <DialogDescription>
            {isNew
              ? 'O sistema gera a senha inicial do mestre.'
              : 'A senha não muda aqui. Use "Trocar senha" no menu.'}
          </DialogDescription>
        </DialogHeader>
        {target !== null && (
          <AcademyForm
            // Remonta o formulário ao trocar de academia
            key={target === 'new' ? 'new' : target.id}
            academy={target === 'new' ? null : target}
            onCancel={onClose}
            onCreated={(result) => {
              onClose()
              onCreated(result)
            }}
            onSaved={() => {
              onClose()
              onSaved()
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function AcademyForm({
  academy,
  onCancel,
  onCreated,
  onSaved,
}: {
  academy: AdminAcademy | null
  onCancel: () => void
  onCreated: (result: AdminCredentials) => void
  onSaved: () => void
}) {
  const create = useMutation(createAcademy)
  const update = useMutation(updateAcademy)
  const isPending = create.isPending || update.isPending
  // O e-mail do administrador não muda pelo painel (ele ficaria trancado fora)
  const emailLocked = academy?.is_own ?? false
  const form = useForm<AcademyValues>({
    resolver: zodResolver(academySchema),
    defaultValues: {
      academy_name: academy?.name ?? '',
      master_name: academy?.master?.name ?? '',
      email: academy?.master?.email ?? '',
      phone: academy?.master?.phone ? formatPhone(academy.master.phone) : '',
    },
  })
  const {
    register,
    formState: { errors },
  } = form

  async function save(values: AcademyValues) {
    const body = {
      academy_name: values.academy_name.trim(),
      master_name: values.master_name.trim(),
      email: values.email.trim(),
      phone: onlyDigits(values.phone),
    }

    try {
      if (academy === null) {
        onCreated(await create.mutate(body))
        return
      }

      await update.mutate(
        academy.id,
        emailLocked ? { ...body, email: undefined } : body,
      )
      toast.success('Academia salva')
      onSaved()
    } catch (error) {
      const code = (error as { code?: string }).code
      if (code && EMAIL_ERRORS.has(code)) {
        form.setError('email', { message: messageFor(error) })
        return
      }
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <FormField
        label="Nome da academia *"
        htmlFor="academy-name"
        error={errors.academy_name?.message}
      >
        <Input
          id="academy-name"
          className="rounded-xl"
          autoFocus
          {...register('academy_name')}
        />
      </FormField>
      <FormField
        label="Nome do mestre *"
        htmlFor="master-name"
        error={errors.master_name?.message}
      >
        <Input
          id="master-name"
          className="rounded-xl"
          {...register('master_name')}
        />
      </FormField>
      <FormField
        label="E-mail do mestre *"
        htmlFor="master-email"
        error={errors.email?.message}
        hint={
          emailLocked
            ? 'Seu e-mail não pode ser trocado por aqui.'
            : 'É o login dele.'
        }
      >
        <Input
          id="master-email"
          type="email"
          // readOnly (e não disabled): campo disabled some dos valores
          // do formulário e falharia na validação
          className="rounded-xl read-only:bg-muted read-only:text-muted-foreground"
          readOnly={emailLocked}
          {...register('email')}
        />
      </FormField>
      <FormField label="Telefone" htmlFor="master-phone" hint="Opcional.">
        <Input
          id="master-phone"
          inputMode="tel"
          placeholder="(62) 99999-0000"
          className="rounded-xl"
          {...register('phone')}
        />
      </FormField>
      <div className="flex justify-end gap-2 pt-1">
        <Button
          type="button"
          variant="ghost"
          className="rounded-full"
          onClick={onCancel}
        >
          Cancelar
        </Button>
        <Button type="submit" className="rounded-full" disabled={isPending}>
          {academy === null ? 'Criar academia' : 'Salvar'}
        </Button>
      </div>
    </form>
  )
}
