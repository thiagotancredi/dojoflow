import { useEffect, useState } from 'react'
import { Check, Download, Share } from 'lucide-react'

import { Button } from '@/components/ui/button'

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

// Captura o evento desde que o módulo da tela é carregado. O usuário pode
// abrir Configurações só depois de o navegador ter oferecido a instalação.
let pendingInstallPrompt: InstallPromptEvent | null = null
if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    pendingInstallPrompt = event as InstallPromptEvent
  })
}

function isAppleMobile() {
  return (
    /iPhone|iPad|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  )
}

function isInstalled() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && navigator.standalone === true)
  )
}

export function AppInstallSection() {
  const [installPrompt, setInstallPrompt] =
    useState<InstallPromptEvent | null>(pendingInstallPrompt)
  const [installed, setInstalled] = useState(isInstalled)
  const [appleMobile] = useState(isAppleMobile)
  const [showManualSteps, setShowManualSteps] = useState(appleMobile)

  useEffect(() => {
    function onBeforeInstallPrompt(event: Event) {
      event.preventDefault()
      setInstallPrompt(event as InstallPromptEvent)
    }

    function onAppInstalled() {
      setInstalled(true)
      setInstallPrompt(null)
    }

    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
    window.addEventListener('appinstalled', onAppInstalled)

    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
      window.removeEventListener('appinstalled', onAppInstalled)
    }
  }, [])

  async function handleInstall() {
    if (!installPrompt) {
      setShowManualSteps(true)
      return
    }

    await installPrompt.prompt()
    const choice = await installPrompt.userChoice
    if (choice.outcome === 'accepted') setInstalled(true)
    pendingInstallPrompt = null
    setInstallPrompt(null)
  }

  return (
    <section className="space-y-4 rounded-3xl bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="font-semibold">Instalar app</h2>
          <p className="max-w-xl text-sm text-muted-foreground">
            Adicione o Katsuflow à tela inicial para abrir em uma janela própria.
            É necessário estar conectado à internet para usar o sistema.
          </p>
        </div>
        {installed ? (
          <span className="inline-flex h-9 items-center gap-2 rounded-full bg-secondary px-4 text-sm font-medium text-secondary-foreground">
            <Check aria-hidden="true" className="size-4" /> Instalado
          </span>
        ) : (
          <Button className="rounded-full" onClick={handleInstall}>
            <Download aria-hidden="true" /> Instalar app
          </Button>
        )}
      </div>

      {!installed && !installPrompt && appleMobile && showManualSteps && (
        <div className="flex gap-3 rounded-2xl bg-muted p-4 text-sm">
          <Share aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
          <p>
            No Safari, toque em <strong>Compartilhar</strong> e depois em{' '}
            <strong>Adicionar à Tela de Início</strong>.
          </p>
        </div>
      )}

      {!installed && !installPrompt && !appleMobile && showManualSteps && (
        <p className="text-sm text-muted-foreground">
          Se o botão não aparecer, abra o menu do navegador e escolha{' '}
          <strong>Instalar app</strong> ou <strong>Adicionar à tela inicial</strong>.
        </p>
      )}
    </section>
  )
}
