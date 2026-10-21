import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import { getMe, login, logout, refresh } from '@/features/auth/api'
import type { Master } from '@/features/auth/api'
import { AuthContext } from '@/features/auth/auth-context'
import type { AuthStatus } from '@/features/auth/auth-context'
import { setApiToken, setRefreshHandler } from '@/lib/api/client'

// Guarda a sessão em memória (nunca no localStorage) e a coloca no
// AuthContext para qualquer componente abaixo ler via useAuth().
// Fluxo: login/refresh dão o token → GET /auth/me diz quem é o usuário.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [master, setMaster] = useState<Master | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')
  // Quem esta aba está mostrando (academia + modo suporte), para conferir
  // depois de cada renovação de sessão
  const masterRef = useRef<Master | null>(null)
  // Trava: o getMe() da conferência pode dar 401 e pedir outra renovação;
  // essa renovação aninhada não confere de novo (evita cascata)
  const checkingScope = useRef(false)

  const applySession = useCallback((token: string, me: Master) => {
    masterRef.current = me
    setMaster(me)
    setAccessToken(token)
    setStatus('authenticated')
  }, [])

  const clearSession = useCallback(() => {
    masterRef.current = null
    setMaster(null)
    setAccessToken(null)
    setApiToken(null)
    setStatus('anonymous')
  }, [])

  useEffect(() => {
    // Evita atualizar o estado depois que o componente saiu da tela
    let active = true

    // Troca o cookie de refresh por um token novo. Também é usado pelo
    // cliente da API quando uma chamada dá 401.
    async function renewToken(): Promise<string | null> {
      try {
        const { access_token } = await refresh()
        setApiToken(access_token)

        // O cookie de refresh é um só para todas as abas: se outra aba
        // entrou em modo suporte (ou saiu dele), esta aba agora estaria
        // mexendo em outra academia sem a tela mostrar. Confere e, se
        // mudou, recarrega para a tela mostrar a academia certa.
        const shown = masterRef.current
        if (shown && !checkingScope.current) {
          checkingScope.current = true
          try {
            const me = await getMe()
            if (
              me.academy.id !== shown.academy.id ||
              me.support_mode !== shown.support_mode
            ) {
              window.location.reload()
              return null
            }
          } finally {
            checkingScope.current = false
          }
        }

        if (active) setAccessToken(access_token)
        return access_token
      } catch {
        if (active) clearSession()
        return null
      }
    }

    // Ao abrir o site (ou dar F5): renova o token e busca quem é o usuário
    async function restoreSession() {
      const token = await renewToken()
      if (!token) return

      try {
        const me = await getMe()
        if (active) applySession(token, me)
      } catch {
        if (active) clearSession()
      }
    }

    setRefreshHandler(renewToken)
    void restoreSession()

    return () => {
      active = false
      setRefreshHandler(null)
    }
  }, [applySession, clearSession])

  const startSession = useCallback(
    async (token: string) => {
      setApiToken(token)

      try {
        applySession(token, await getMe())
      } catch (error) {
        clearSession()
        throw error
      }
    },
    [applySession, clearSession],
  )

  // useCallback mantém a mesma função entre renderizações, para poder ser
  // usada com segurança dentro de um useEffect (ex.: o polling do Telegram)
  const reloadMaster = useCallback(async () => {
    const me = await getMe()
    masterRef.current = me
    setMaster(me)
    return me
  }, [])

  async function signIn(email: string, password: string) {
    // Se o login falhar, o erro sobe para quem chamou (o LoginPage).
    const { access_token } = await login(email, password)
    await startSession(access_token)
  }

  async function signOut() {
    try {
      await logout()
    } finally {
      // Limpa a sessão mesmo se a API falhar.
      clearSession()
    }
  }

  return (
    <AuthContext
      value={{
        status,
        master,
        accessToken,
        signIn,
        signOut,
        startSession,
        reloadMaster,
      }}
    >
      {children}
    </AuthContext>
  )
}
