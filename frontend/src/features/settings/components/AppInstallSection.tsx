import { useEffect, useState, type ReactNode } from 'react'
import {
  Check,
  Download,
  EllipsisVertical,
  RefreshCw,
  Share,
  SquarePlus,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatAppVersion, isStandalone, reloadApp } from '@/lib/appUpdate'
import { cn } from '@/lib/utils'

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

type Device = 'iphone' | 'android' | 'computer'

const TABS: { device: Device; label: string; logo?: string }[] = [
  { device: 'iphone', label: 'iPhone', logo: '/icons/apple.svg' },
  { device: 'android', label: 'Android', logo: '/icons/android.svg' },
  { device: 'computer', label: 'Computador' },
]

// Captura o evento desde que o módulo da tela é carregado. O usuário pode
// abrir Configurações só depois de o navegador ter oferecido a instalação.
let pendingInstallPrompt: InstallPromptEvent | null = null
if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    pendingInstallPrompt = event as InstallPromptEvent
  })
}

// Aparelho de quem está vendo: a aba dele já abre selecionada
function detectDevice(): Device {
  const userAgent = navigator.userAgent
  const isIpad = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
  if (/iPhone|iPad|iPod/.test(userAgent) || isIpad) return 'iphone'
  if (/Android/.test(userAgent)) return 'android'
  return 'computer'
}

export function AppInstallSection() {
  const [installPrompt, setInstallPrompt] =
    useState<InstallPromptEvent | null>(pendingInstallPrompt)
  const [installed, setInstalled] = useState(isStandalone)
  const [currentDevice] = useState(detectDevice)
  const [tab, setTab] = useState<Device>(currentDevice)

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
    if (!installPrompt) return

    await installPrompt.prompt()
    const choice = await installPrompt.userChoice
    if (choice.outcome === 'accepted') setInstalled(true)
    pendingInstallPrompt = null
    setInstallPrompt(null)
  }

  // Botão "Instalar agora" só na aba do próprio aparelho e quando o
  // navegador permite instalar direto; senão, os passos (nunca os dois)
  const canInstallHere = installPrompt !== null && tab === currentDevice

  return (
    <section className="space-y-4 rounded-3xl bg-card p-5">
      <div className="flex items-center gap-3">
        <img
          src="/icons/icon-192.png"
          alt=""
          aria-hidden="true"
          className="size-13 shrink-0 rounded-[0.8rem]"
        />
        <div className="min-w-0 flex-1 space-y-0.5">
          <h2 className="font-semibold">Katsuflow no celular</h2>
          <p className="text-sm text-muted-foreground">
            Abra direto da tela inicial, como um app.
          </p>
        </div>
        {installed && (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-chip-active-border bg-chip-active px-3 py-1 text-xs font-semibold text-chip-active-foreground">
            <Check aria-hidden="true" className="size-3.5" /> Instalado
          </span>
        )}
      </div>

      {/* No app instalado não há botão de recarregar do navegador */}
      {installed && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <p className="text-xs text-muted-foreground">
            Versão de {formatAppVersion()}
          </p>
          <Button variant="outline" size="sm" className="rounded-full" onClick={reloadApp}>
            <RefreshCw aria-hidden="true" /> Recarregar app
          </Button>
        </div>
      )}

      {!installed && (
        <div className="space-y-3 border-t pt-4">
          {/* Seletor de 3 partes iguais: sempre cabe numa linha */}
          <div className="grid grid-cols-3 rounded-full bg-muted p-1 sm:max-w-md">
            {TABS.map((option) => (
              <button
                key={option.device}
                type="button"
                aria-pressed={tab === option.device}
                onClick={() => setTab(option.device)}
                className={cn(
                  'inline-flex min-w-0 items-center justify-center gap-1.5 rounded-full px-2 py-1.5 text-sm',
                  tab === option.device
                    ? 'bg-card font-semibold text-foreground shadow-sm'
                    : 'text-muted-foreground',
                )}
              >
                {option.logo && (
                  <img src={option.logo} alt="" aria-hidden="true" className="size-3.5" />
                )}
                {option.label}
              </button>
            ))}
          </div>

          {canInstallHere ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Seu {tab === 'computer' ? 'computador' : 'celular'} já permite instalar
                direto. É só um toque:
              </p>
              <Button className="w-full rounded-full sm:w-auto" onClick={handleInstall}>
                <Download aria-hidden="true" /> Instalar agora
              </Button>
            </div>
          ) : (
            <InstallSteps device={tab} />
          )}
        </div>
      )}
    </section>
  )
}

function InstallSteps({ device }: { device: Device }) {
  const steps: Record<Device, ReactNode[]> = {
    iphone: [
      <>Abra o Katsuflow no <Strong>Safari</Strong>.</>,
      <>Toque em <Key icon={<Share />}>Compartilhar</Key>.</>,
      <>Toque em <Key icon={<SquarePlus />}>Adicionar à Tela de Início</Key>.</>,
      <>Confirme em <Strong>Adicionar</Strong>. Pronto!</>,
    ],
    android: [
      <>Abra o Katsuflow no <Strong>Chrome</Strong>.</>,
      <>Toque no menu <Key icon={<EllipsisVertical />} label="Menu" /> no canto de cima.</>,
      <>Toque em <Key icon={<Download />}>Instalar app</Key>.</>,
      <>Confirme em <Strong>Instalar</Strong>. Pronto!</>,
    ],
    computer: [
      <>Abra o Katsuflow no <Strong>Chrome</Strong> ou no <Strong>Edge</Strong>.</>,
      <>Clique no ícone <Key icon={<Download />} label="Instalar" /> no fim da barra de endereço.</>,
      <>Confirme em <Strong>Instalar</Strong>. O Katsuflow abre numa janela própria.</>,
    ],
  }

  return (
    <ol className="space-y-2.5">
      {steps[device].map((step, index) => (
        <li key={index} className="flex items-start gap-2.5 text-sm">
          <span className="grid size-5.5 shrink-0 place-items-center rounded-full bg-chip-active text-[11px] font-semibold text-chip-active-foreground">
            {index + 1}
          </span>
          <span className="leading-relaxed text-muted-foreground">{step}</span>
        </li>
      ))}
    </ol>
  )
}

function Strong({ children }: { children: ReactNode }) {
  return <strong className="font-semibold text-foreground">{children}</strong>
}

// Desenha o botão do navegador como a pessoa vai vê-lo (ícone + nome)
function Key({ icon, children, label }: { icon: ReactNode; children?: ReactNode; label?: string }) {
  return (
    <span
      className="ml-0.5 inline-flex items-center gap-1 rounded-lg border bg-background px-1.5 py-px align-middle font-medium text-foreground [&_svg]:size-3.5"
      aria-label={children ? undefined : label}
    >
      {icon}
      {children}
    </span>
  )
}
