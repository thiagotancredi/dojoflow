import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { exchangeSupportCode } from '@/features/auth/api'
import { rememberSupportEnd } from '@/features/auth/support'
import { useAuth } from '@/features/auth/useAuth'
import { messageFor } from '@/lib/api/errors'

// /suporte#<código>: aberta pelo botão "Entrar" do painel admin.*.
// Troca o código de uso único por uma sessão de suporte e vai para o app.
export function SupportEntryPage() {
  const navigate = useNavigate()
  const { status, startSession } = useAuth()
  const [error, setError] = useState<string | null>(null)
  // Código lido uma vez (o hash é apagado logo em seguida) e troca feita
  // uma vez só, mesmo com o efeito rodando duas vezes no StrictMode
  const code = useRef(window.location.hash.slice(1))
  const started = useRef(false)

  useEffect(() => {
    // Tira o código da barra de endereço e do histórico
    window.history.replaceState(null, '', window.location.pathname)
  }, [])

  useEffect(() => {
    // Espera o AuthProvider terminar de recuperar a sessão antiga (pelo
    // cookie); senão ela poderia chegar depois e passar por cima desta
    if (status === 'loading' || started.current) return
    started.current = true

    async function enter() {
      try {
        if (!code.current) throw new Error('missing code')
        const { access_token } = await exchangeSupportCode(code.current)
        rememberSupportEnd()
        await startSession(access_token)
        navigate('/app', { replace: true })
      } catch (caught) {
        setError(messageFor(caught, 'Link de suporte inválido ou expirado.'))
      }
    }

    void enter()
  }, [status, startSession, navigate])

  return (
    <div className="grid min-h-dvh place-items-center p-4 text-center text-sm text-muted-foreground">
      {error ? (
        <div className="max-w-sm space-y-3 rounded-3xl bg-card p-8 shadow-sm">
          <p className="text-base font-semibold text-foreground">
            Não deu para entrar
          </p>
          <p>{error}</p>
          <Link to="/login" className="font-medium text-foreground underline">
            Ir para o login
          </Link>
        </div>
      ) : (
        'Entrando em modo suporte…'
      )}
    </div>
  )
}
