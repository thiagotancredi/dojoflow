import { createContext } from 'react'

import type { AuthSession } from '@/features/auth/api'

export type Master = AuthSession['master']

// loading: ainda tentando recuperar a sessão pelo cookie (ao abrir o site)
export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

// O que todo componente pode ler da sessão (via useAuth).
export type AuthContextValue = {
  status: AuthStatus
  master: Master | null
  accessToken: string | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

// Começa vazia (null): quem preenche é o AuthProvider.
export const AuthContext = createContext<AuthContextValue | null>(null)
