import { Eye, EyeOff, Lock, Mail } from 'lucide-react'
import { useState } from 'react'
import type { SubmitEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'

import { useAuth } from '@/features/auth/useAuth'
import type { ApiError } from '@/lib/api/client'

import { BrandLogo } from '@/app/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type LoginPageProps = {
  // Para onde ir depois de entrar ("/" no painel admin.*)
  redirectTo?: string
  // 'admin': cartão compacto do painel, diferente do login dos mestres
  variant?: 'app' | 'admin'
}

// Login: o signIn() do AuthContext chama a API e guarda a sessão.
export function LoginPage({
  redirectTo = '/app',
  variant = 'app',
}: LoginPageProps) {
  const navigate = useNavigate()
  const { status, signIn } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    // Impede o navegador de recarregar a página (comportamento padrão do <form>)
    event.preventDefault()
    setError(null)

    try {
      await signIn(email, password)
      navigate(redirectTo)
    } catch (err) {
      const apiError = err as ApiError
      setError(
        apiError.code === 'INVALID_CREDENTIALS'
          ? 'E-mail ou senha incorretos.'
          : apiError.code === 'ACADEMY_BLOCKED'
            ? 'Academia desativada. Fale com o suporte.'
            : 'Não foi possível entrar. Tente novamente.',
      )
    }
  }

  // Já logado (ex.: voltou para /login com a sessão ativa): vai direto ao app
  if (status === 'authenticated') {
    return <Navigate to={redirectTo} replace />
  }

  // Campos e botão: iguais nas duas versões
  const fields = (
    <>
      <div className="space-y-1.5">
        <Label htmlFor="email">E-mail</Label>
        <div className="relative">
          <Mail className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="email"
            type="email"
            placeholder={
              variant === 'admin' ? 'seu@email.com' : 'voce@academia.com'
            }
            className="h-11 rounded-xl pl-9"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="password">Senha</Label>
        <div className="relative">
          <Lock className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="password"
            type={showPassword ? 'text' : 'password'}
            className="h-11 rounded-xl px-9"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            aria-label={showPassword ? 'Esconder senha' : 'Mostrar senha'}
            className="absolute top-1/2 right-3 -translate-y-1/2 text-muted-foreground"
          >
            {showPassword ? (
              <EyeOff className="size-4" />
            ) : (
              <Eye className="size-4" />
            )}
          </button>
        </div>
        <div className="text-right">
          <Link
            to="/esqueci-senha"
            className="text-sm text-muted-foreground underline"
          >
            Esqueci minha senha
          </Link>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <Button type="submit" className="h-11 w-full rounded-full text-base">
        Entrar
      </Button>
    </>
  )

  // Painel do administrador: cartão único, sem a parte de marketing
  if (variant === 'admin') {
    return (
      <div className="grid min-h-dvh place-items-center p-4">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-sm space-y-4 rounded-3xl bg-card p-8 shadow-xl shadow-primary/10"
        >
          <BrandLogo className="mx-auto w-60" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">Painel administrativo</h1>
              <span className="rounded-full border border-chip-active-border bg-chip-active px-2 py-0.5 text-[11px] font-semibold tracking-wide text-chip-active-foreground uppercase">
                Admin
              </span>
            </div>
            <p className="text-sm text-muted-foreground">Acesso restrito.</p>
          </div>
          {fields}
        </form>
      </div>
    )
  }

  return (
    <div className="grid min-h-dvh place-items-center p-4">
      <div className="flex w-full max-w-4xl overflow-hidden rounded-3xl bg-card shadow-xl shadow-primary/10">
        {/* Painel da marca (cores em styles/theme.css): só no desktop */}
        {/* Mesmo recuo do formulário (p-10): o topo da logo fica na linha
            do "Entrar" */}
        <aside className="hidden w-1/2 flex-col justify-between gap-8 bg-gradient-to-br from-brand-from to-brand-to p-10 text-brand-foreground md:flex">
          {/* O painel é escuro nos dois temas: sempre a logo de tinta clara */}
          <BrandLogo tone="on-dark" className="w-full" />
          <div className="space-y-3">
            <h2 className="text-2xl leading-tight font-semibold">
              As mensalidades do seu dojo, sem caderno e sem planilha.
            </h2>
            <p className="text-sm opacity-80">
              Alunos, faixas, matrículas e cobranças num só lugar.
            </p>
          </div>
        </aside>

        <form onSubmit={handleSubmit} className="flex-1 space-y-4 p-8 md:p-10">
          {/* Celular: o painel colorido some, a logo vem para cá */}
          <div className="md:hidden">
            <BrandLogo className="mx-auto w-56" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Entrar</h1>
            <p className="text-sm text-muted-foreground">
              Bem-vindo de volta, mestre.
            </p>
          </div>

          {fields}
        </form>
      </div>
    </div>
  )
}
