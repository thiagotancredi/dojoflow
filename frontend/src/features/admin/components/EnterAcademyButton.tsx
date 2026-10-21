import { ExternalLink } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { createSupportEntry } from '@/features/admin/api'
import type { AdminAcademy } from '@/features/admin/api'
import { showApiError } from '@/lib/api/errors'
import { mainAppOrigin } from '@/lib/host'
import { useMutation } from '@/lib/hooks/useMutation'

// "Entrar": abre o app da academia numa aba nova, em modo suporte
export function EnterAcademyButton({
  academy,
  className,
}: {
  academy: AdminAcademy
  className?: string
}) {
  const entry = useMutation(createSupportEntry)

  async function enter() {
    // A aba abre ANTES do await: aberta depois, o navegador a trataria
    // como pop-up e bloquearia
    const tab = window.open('', '_blank')
    if (tab) tab.opener = null

    try {
      const { code } = await entry.mutate(academy.id)
      if (!tab) {
        toast.error('O navegador bloqueou a aba nova. Libere pop-ups.')
        return
      }
      tab.location.href = `${mainAppOrigin()}/suporte#${code}`
    } catch (error) {
      tab?.close()
      showApiError(error)
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      className={`rounded-full ${className ?? ''}`}
      disabled={entry.isPending}
      onClick={() => void enter()}
    >
      <ExternalLink className="size-4" />
      Entrar
    </Button>
  )
}
