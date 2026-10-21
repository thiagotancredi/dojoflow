import { createContext } from 'react'

import type { Master } from '@/features/auth/api'

// loading: ainda tentando recuperar a sessão pelo cookie (ao abrir o site)
export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

// O que todo componente pode ler da sessão (via useAuth).
export type AuthContextValue = {
  status: AuthStatus
  master: Master | null
  accessToken: string | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  // Entra com um token que já veio da API (ex.: depois de definir a senha)
  startSession: (accessToken: string) => Promise<void>
  // Busca de novo os dados do mestre (ex.: para ver se o Telegram conectou)
  reloadMaster: () => Promise<Master>
}

// Começa vazia (null): quem preenche é o AuthProvider.
export const AuthContext = createContext<AuthContextValue | null>(null)
