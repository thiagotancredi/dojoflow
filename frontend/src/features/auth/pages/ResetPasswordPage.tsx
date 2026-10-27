import { Lock } from 'lucide-react'
import { useState } from 'react'
import type { SubmitEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { BrandLogo } from '@/app/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfirmPasswordReset } from '@/features/auth/password-reset-api'
import { showApiError } from '@/lib/api/errors'

const MIN_PASSWORD_LENGTH = 8

// Página do link do e-mail (/redefinir-senha/:token): cria a senha nova.
export function ResetPasswordPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const confirm = useConfirmPasswordReset()
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [linkInvalid, setLinkInvalid] = useState(false)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`A senha precisa ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`)
      return
    }
    if (password !== repeat) {
      setError('As senhas não são iguais.')
      return
    }

    try {
      await confirm.mutate({ token, password })
      toast.success('Senha criada. Entre com a senha nova.')
      navigate('/login')
    } catch (err) {
      if ((err as { code?: string }).code === 'RESET_LINK_INVALID') {
        setLinkInvalid(true)
      } else {
        showApiError(err)
      }
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center p-4">
      <div className="w-full max-w-sm space-y-4 rounded-3xl bg-card p-8 shadow-xl shadow-primary/10">
        <BrandLogo className="mx-auto w-56" />
        <h1 className="text-2xl font-semibold">Criar senha nova</h1>

        {linkInvalid ? (
          <div className="space-y-4">
            <p role="alert" className="text-sm text-destructive">
              Este link venceu ou já foi usado. Peça um novo.
            </p>
            <Button
              asChild
              variant="outline"
              className="h-11 w-full rounded-full text-base"
            >
              <Link to="/esqueci-senha">Pedir novo link</Link>
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="password">Senha nova</Label>
              <div className="relative">
                <Lock className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  className="h-11 rounded-xl pl-9"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="repeat">Repita a senha</Label>
              <div className="relative">
                <Lock className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="repeat"
                  type="password"
                  autoComplete="new-password"
                  className="h-11 rounded-xl pl-9"
                  value={repeat}
                  onChange={(event) => setRepeat(event.target.value)}
                />
              </div>
            </div>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <Button
              type="submit"
              disabled={confirm.isPending}
              className="h-11 w-full rounded-full text-base"
            >
              Salvar
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}
