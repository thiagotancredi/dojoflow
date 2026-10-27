import { Mail } from 'lucide-react'
import { useState } from 'react'
import type { SubmitEvent } from 'react'
import { Link } from 'react-router'

import { BrandLogo } from '@/app/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useRequestPasswordReset } from '@/features/auth/password-reset-api'
import { showApiError } from '@/lib/api/errors'

// "Esqueci minha senha": pede o e-mail e a API manda o link. A resposta é
// sempre a mesma, então a tela nunca diz se o e-mail existe.
export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const request = useRequestPasswordReset()

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      await request.mutate(email.trim())
      setSent(true)
    } catch (err) {
      showApiError(err)
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center p-4">
      <div className="w-full max-w-sm space-y-4 rounded-3xl bg-card p-8 shadow-xl shadow-primary/10">
        <BrandLogo className="mx-auto w-56" />
        <h1 className="text-2xl font-semibold">Esqueci minha senha</h1>

        {sent ? (
          <div className="space-y-4">
            <p role="status" className="text-sm text-muted-foreground">
              Se esse e-mail estiver cadastrado, enviamos um link para criar uma
              senha nova. Confira também o spam.
            </p>
            <Button
              asChild
              variant="outline"
              className="h-11 w-full rounded-full text-base"
            >
              <Link to="/login">Voltar para o login</Link>
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <div className="relative">
                <Mail className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="h-11 rounded-xl pl-9"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </div>
            <Button
              type="submit"
              disabled={request.isPending}
              className="h-11 w-full rounded-full text-base"
            >
              Enviar link
            </Button>
            <p className="text-center text-sm">
              <Link to="/login" className="text-muted-foreground underline">
                Voltar para o login
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
