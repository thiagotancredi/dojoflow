import { useState } from 'react'
import type { SubmitEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { Logo } from '@/app/components/Logo'
import { FormField } from '@/components/FormField'
import { PasswordInput } from '@/components/PasswordInput'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { setCredentials } from '@/features/auth/api'
import { useAuth } from '@/features/auth/useAuth'
import { messageFor } from '@/lib/api/errors'
import { useMutation } from '@/lib/hooks/useMutation'

const MIN_PASSWORD_LENGTH = 8

// /definir-acesso?token=… — aberta pelo link que o bot manda no /web.
// O token (uso único, 15 min) prova quem é; o mestre escolhe e-mail e senha
// e já entra logado. Serve tanto para o primeiro acesso quanto para
// "esqueci minha senha".
export function SetAccessPage() {
  const navigate = useNavigate()
  // useSearchParams lê a parte "?token=…" da URL
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { startSession } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { mutate, isPending } = useMutation(setCredentials)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (!token) return
    if (!email.includes('@')) {
      setError('Informe um e-mail válido.')
      return
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(
        `A senha precisa ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`,
      )
      return
    }

    try {
      const { access_token } = await mutate({
        email,
        password,
        setup_token: token,
      })
      await startSession(access_token)
      navigate('/app', { replace: true })
    } catch (caught) {
      setError(messageFor(caught))
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center p-4">
      <div className="w-full max-w-md space-y-4 rounded-3xl bg-card p-8 shadow-xl shadow-primary/10">
        <div className="flex items-center gap-3">
          <Logo />
          <span className="font-semibold">Katsuflow</span>
        </div>

        {token ? (
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <h1 className="text-2xl font-semibold">Definir acesso</h1>
              <p className="text-sm text-muted-foreground">
                Escolha o e-mail e a senha para entrar no site.
              </p>
            </div>

            <FormField
              label="E-mail"
              htmlFor="email"
              hint="Se já tem acesso, pode usar o mesmo e-mail."
            >
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="voce@academia.com"
                className="h-11 rounded-xl"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </FormField>

            <FormField
              label="Nova senha"
              htmlFor="password"
              hint={`Pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`}
            >
              <PasswordInput
                id="password"
                autoComplete="new-password"
                className="h-11 rounded-xl"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </FormField>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="h-11 w-full rounded-full text-base"
              disabled={isPending}
            >
              {isPending ? 'Salvando…' : 'Salvar e entrar'}
            </Button>
          </form>
        ) : (
          <div className="space-y-2">
            <h1 className="text-2xl font-semibold">Link incompleto</h1>
            <p className="text-sm text-muted-foreground">
              Envie <strong>/web</strong> para o bot no Telegram e abra o link
              que ele mandar.
            </p>
          </div>
        )}

        <p className="text-center text-xs text-muted-foreground">
          <Link to="/login" className="underline">
            Voltar para o login
          </Link>
        </p>
      </div>
    </div>
  )
}
