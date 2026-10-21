import logoForDarkBg from '@/assets/brand/logo-dark.png'
import logoForLightBg from '@/assets/brand/logo-light.png'

type BrandLogoProps = {
  className?: string
  // 'auto': segue o tema (claro/escuro). 'on-dark': fundo sempre escuro
  // (ex.: o painel colorido do login), usa só a versão clara da tinta.
  tone?: 'auto' | 'on-dark'
}

const ALT = 'Katsuflow — gestão para academias de luta'

// Logo completa (lutador + "Katsuflow" + frase). Duas versões sem fundo:
// tinta escura para fundo claro e tinta clara para fundo escuro.
export function BrandLogo({ className = '', tone = 'auto' }: BrandLogoProps) {
  if (tone === 'on-dark') {
    return <img src={logoForDarkBg} alt={ALT} className={className} />
  }

  return (
    <>
      <img
        src={logoForLightBg}
        alt={ALT}
        className={`dark:hidden ${className}`}
      />
      <img
        src={logoForDarkBg}
        alt={ALT}
        className={`hidden dark:block ${className}`}
      />
    </>
  )
}
