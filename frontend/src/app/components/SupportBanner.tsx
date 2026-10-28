import { X } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '@/components/ui/button'
import { supportEndsAt } from '@/features/auth/support'
import { useAuth } from '@/features/auth/useAuth'

// Faixa fixa no modo suporte: lembra que é o administrador vendo outra
// academia. "Sair" encerra a sessão de suporte e fecha a aba.
export function SupportBanner() {
  const navigate = useNavigate()
  const { master, signOut } = useAuth()

  if (!master?.support_mode) return null

  const endsAt = supportEndsAt()

  async function leave() {
    await signOut()
    window.close()
    // Se o navegador não deixar fechar a aba, vai para o login
    navigate('/login', { replace: true })
  }

  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-status-pending/40 bg-status-pending-soft px-4 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-status-pending px-2 py-0.5 text-[11px] font-bold tracking-wide text-white uppercase">
          Modo suporte
        </span>
        <span>
          Você está vendo <strong>{master.academy.name}</strong> como{' '}
          {master.name}
          {endsAt &&
            ` · termina às ${endsAt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`}
        </span>
      </div>
      <Button
        variant="outline"
        size="sm"
        className="rounded-full"
        onClick={() => void leave()}
      >
        <X className="size-4" />
        Sair
      </Button>
    </div>
  )
}
