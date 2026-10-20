import { useContext } from 'react'

import { AuthContext } from '@/features/auth/auth-context'

// Lê a sessão do AuthContext. Falha com mensagem clara se usado fora do
// AuthProvider; depois do if, o tipo deixa de ser null.
export function useAuth() {
  const context = useContext(AuthContext)

  if (context === null) {
    throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  }

  return context
}
