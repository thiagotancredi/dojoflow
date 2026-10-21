import { useState } from 'react'
import type { SubmitEvent } from 'react'
import { toast } from 'sonner'

import { FormField } from '@/components/FormField'
import { PasswordInput } from '@/components/PasswordInput'
import { Button } from '@/components/ui/button'
import { setCredentials } from '@/features/auth/api'
import { useAuth } from '@/features/auth/useAuth'
import type { ApiError } from '@/lib/api/client'
import { showApiError } from '@/lib/api/errors'
import { useMutation } from '@/lib/hooks/useMutation'

const MIN_PASSWORD_LENGTH = 8

type FieldErrors = { current?: string; next?: string }

// Trocar senha: confere a senha atual e grava a nova. O backend devolve uma
// sessão nova (continua logado aqui) e derruba as dos outros aparelhos.
export function ChangePasswordForm() {
  const { master, startSession } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const { mutate, isPending } = useMutation(setCredentials)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()

    const found: FieldErrors = {}
    if (!currentPassword) found.current = 'Informe a senha atual.'
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      found.next = `A nova senha precisa ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`
    }
    setErrors(found)
    if (found.current || found.next) return

    try {
      const { access_token } = await mutate({
        // Só entra no site quem tem e-mail e senha, então o e-mail existe
        email: master?.email ?? '',
        password: newPassword,
        current_password: currentPassword,
      })
      await startSession(access_token)
      setCurrentPassword('')
      setNewPassword('')
      toast.success('Senha alterada', {
        description: 'Nos outros aparelhos, será preciso entrar de novo.',
      })
    } catch (error) {
      if ((error as ApiError).code === 'CURRENT_PASSWORD_INVALID') {
        setErrors({ current: 'Senha atual incorreta.' })
      } else {
        showApiError(error)
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="max-w-xl space-y-4">
      <h3 className="text-sm font-medium">Trocar senha</h3>
      <FormField
        label="Senha atual"
        htmlFor="current-password"
        error={errors.current}
      >
        <PasswordInput
          id="current-password"
          autoComplete="current-password"
          className="rounded-xl"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          aria-invalid={Boolean(errors.current)}
        />
      </FormField>
      <FormField
        label="Nova senha"
        htmlFor="new-password"
        error={errors.next}
        hint={`Pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`}
      >
        <PasswordInput
          id="new-password"
          autoComplete="new-password"
          className="rounded-xl"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          aria-invalid={Boolean(errors.next)}
        />
      </FormField>
      <Button type="submit" className="rounded-full" disabled={isPending}>
        {isPending ? 'Salvando…' : 'Salvar'}
      </Button>
    </form>
  )
}
