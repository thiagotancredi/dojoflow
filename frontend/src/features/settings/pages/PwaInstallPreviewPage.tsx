import { useState } from 'react'
import { Download, MonitorDown } from 'lucide-react'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'

const logoStyles = [
  { id: 'native', label: '1 · Cores originais' },
  { id: 'soft', label: '2 · Fundo suave' },
  { id: 'brand', label: '3 · Alto contraste' },
] as const

type LogoStyle = (typeof logoStyles)[number]['id']
type Platform = 'apple' | 'android'

export function PwaInstallPreviewPage() {
  const [logoStyle, setLogoStyle] = useState<LogoStyle>('native')

  return (
    <div className="space-y-4">
      <PageHeader title="Prévia: instalar app" />

      <section className="space-y-3 rounded-3xl bg-card p-5">
        <div className="space-y-1">
          <h2 className="font-semibold">Variações dos logos</h2>
          <p className="text-sm text-muted-foreground">
            O conteúdo e o passo a passo da opção 8 permanecem iguais. Escolha apenas como
            apresentar os logos Apple e Android.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {logoStyles.map((style) => (
            <Button
              key={style.id}
              type="button"
              variant={logoStyle === style.id ? 'default' : 'outline'}
              className="rounded-full"
              aria-pressed={logoStyle === style.id}
              onClick={() => setLogoStyle(style.id)}
            >
              {style.label}
            </Button>
          ))}
        </div>
      </section>

      <section className="space-y-4 rounded-3xl bg-card p-5">
        <div className="space-y-1">
          <h2 className="font-semibold">Como instalar o Katsuflow</h2>
          <p className="text-sm text-muted-foreground">
            Selecione seu dispositivo e siga as etapas. É necessário estar conectado à internet.
          </p>
        </div>

        <div className="grid items-stretch gap-3 lg:grid-cols-2">
          <PlatformGuide
            platform="apple"
            logoStyle={logoStyle}
            title="iPhone ou iPad"
            subtitle="Safari · Adicionar à Tela de Início"
            steps={[
              'Abra o Katsuflow no Safari e entre na sua conta.',
              'Toque em Compartilhar, na barra do navegador.',
              'Role as opções e toque em Adicionar à Tela de Início.',
              'Confirme em Adicionar. O ícone do Katsuflow ficará na tela inicial.',
            ]}
          />
          <PlatformGuide
            platform="android"
            logoStyle={logoStyle}
            title="Android"
            subtitle="Chrome · Instalar app"
            steps={[
              'Abra o Katsuflow no Chrome e entre na sua conta.',
              'Toque em Instalar app nesta tela. Se não aparecer, abra o menu ⋮.',
              'No menu, toque em Instalar app ou Adicionar à tela inicial.',
              'Confirme a instalação e abra pelo ícone do Katsuflow.',
            ]}
          />
        </div>

        <p className="flex items-center gap-2 border-t pt-3 text-sm text-muted-foreground">
          <MonitorDown aria-hidden="true" className="size-4 shrink-0" />
          <span>
            <strong className="font-medium text-foreground">Computador:</strong> no Chrome ou Edge,
            use o ícone de instalação na barra de endereço ou a opção “Instalar app” no menu.
          </span>
        </p>

        <Button className="rounded-full" onClick={() => undefined}>
          <Download aria-hidden="true" /> Instalar app
        </Button>
      </section>

      <p className="px-1 text-xs text-muted-foreground">
        Prévia demonstrativa. O botão não inicia uma instalação.
      </p>
    </div>
  )
}

function PlatformGuide({
  platform,
  logoStyle,
  title,
  subtitle,
  steps,
}: {
  platform: Platform
  logoStyle: LogoStyle
  title: string
  subtitle: string
  steps: string[]
}) {
  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border p-4">
      <div className="flex min-h-10 items-center gap-3">
        <PlatformLogo platform={platform} style={logoStyle} />
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      <ol className="grid flex-1 grid-rows-4 gap-y-2.5">
        {steps.map((step, index) => (
          <li key={step} className="grid grid-cols-[1.25rem_minmax(0,1fr)] items-start gap-2.5 text-sm">
            <span className="grid size-5 shrink-0 place-items-center rounded-full bg-muted text-[11px] font-semibold text-primary">
              {index + 1}
            </span>
            <span className="leading-relaxed text-muted-foreground">{step}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

function PlatformLogo({ platform, style }: { platform: Platform; style: LogoStyle }) {
  const contrastClass = platform === 'apple' ? 'bg-black' : 'bg-[#3DDC84]'

  if (style === 'native') {
    return (
      <span className="grid size-10 shrink-0 place-items-center">
        <img aria-hidden="true" src={`/icons/${platform}.svg`} alt="" className="size-6" />
      </span>
    )
  }

  if (style === 'soft') {
    return (
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-muted">
        <img aria-hidden="true" src={`/icons/${platform}.svg`} alt="" className="size-5" />
      </span>
    )
  }

  return (
    <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${contrastClass}`}>
      <img
        aria-hidden="true"
        src={`/icons/${platform}.svg`}
        alt=""
        className="size-5 brightness-0 invert"
      />
    </span>
  )
}
