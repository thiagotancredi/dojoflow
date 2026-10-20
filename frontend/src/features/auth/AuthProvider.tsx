import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { login, logout, refresh } from '@/features/auth/api'
import { AuthContext } from '@/features/auth/auth-context'
import type { AuthStatus, Master } from '@/features/auth/auth-context'

// Guarda a sessão em memória (nunca no localStorage) e a coloca no
// AuthContext para qualquer componente abaixo ler via useAuth().
export function AuthProvider({ children }: { children: ReactNode }) {
  const [master, setMaster] = useState<Master | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  // Ao abrir o site (ou dar F5), tenta recuperar a sessão pelo cookie.
  useEffect(() => {
    // Evita atualizar o estado depois que o componente saiu da tela
    let active = true

    refresh()
      .then((session) => {
        if (!active) return
        setMaster(session.master)
        setAccessToken(session.access_token)
        setStatus('authenticated')
      })
      .catch(() => {
        if (active) setStatus('anonymous')
      })

    return () => {
      active = false
    }
  }, [])

  async function signIn(email: string, password: string) {
    // Se o login falhar, o erro sobe para quem chamou (o LoginPage).
    const session = await login(email, password)
    setMaster(session.master)
    setAccessToken(session.access_token)
    setStatus('authenticated')
  }

  async function signOut() {
    try {
      await logout()
    } finally {
      // Limpa a sessão mesmo se a API falhar.
      setMaster(null)
      setAccessToken(null)
      setStatus('anonymous')
    }
  }

  return (
    <AuthContext value={{ status, master, accessToken, signIn, signOut }}>
      {children}
    </AuthContext>
  )
}
