import { Eye, EyeOff, Lock, Mail } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { Logo } from '@/app/components/Logo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Por enquanto o botão só navega para /app. Na Fase 4 ele chama
// POST /api/v1/auth/login e guarda o token.
export function LoginPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Impede o navegador de recarregar a página (comportamento padrão do <form>)
    event.preventDefault()
    navigate('/app')
  }

  return (
    <div className="grid min-h-dvh place-items-center p-4">
      <div className="flex w-full max-w-4xl overflow-hidden rounded-3xl bg-card shadow-xl shadow-primary/10">
        {/* Painel da marca (cores em styles/theme.css): só no desktop */}
        <aside className="hidden w-[44%] flex-col bg-gradient-to-br from-brand-from to-brand-to p-8 text-brand-foreground md:flex">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="text-lg font-semibold">DojoFlow</span>
          </div>
          <div className="mt-auto space-y-3">
            <h2 className="text-2xl leading-tight font-semibold">
              As mensalidades do seu dojo, sem caderno e sem planilha.
            </h2>
            <p className="text-sm opacity-80">
              Alunos, matrículas e cobranças num só lugar — no site ou pelo
              Telegram.
            </p>
          </div>
        </aside>

        <form onSubmit={handleSubmit} className="flex-1 space-y-4 p-8 md:p-10">
          <div className="flex items-center gap-3 md:hidden">
            <Logo />
            <span className="font-semibold">DojoFlow</span>
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Entrar</h1>
            <p className="text-sm text-muted-foreground">
              Bem-vindo de volta, mestre.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">E-mail</Label>
            <div className="relative">
              <Mail className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="email"
                type="email"
                placeholder="voce@academia.com"
                className="h-11 rounded-xl pl-9"
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
          </div>

          <Button type="submit" className="h-11 w-full rounded-full text-base">
            Entrar
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Esqueceu a senha? Envie <strong>/web</strong> para o bot no
            Telegram.
          </p>
        </form>
      </div>
    </div>
  )
}
