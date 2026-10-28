import { useEffect, useState } from 'react'

// Versão que está rodando agora (data e hora do build, ver vite.config.ts)
export const APP_VERSION: string = import.meta.env.VITE_APP_VERSION ?? ''

// Confere de novo a cada 5 minutos com o app aberto
const CHECK_INTERVAL_MS = 5 * 60 * 1000

// "2026-10-28T06:31:14.000Z" → "28/10/2026 03:31" (no fuso do aparelho)
export function formatAppVersion(version = APP_VERSION) {
  const date = new Date(version)
  if (Number.isNaN(date.getTime())) return 'desenvolvimento'
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

// App instalado (aberto pelo ícone, sem a barra do navegador)
export function isStandalone() {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && navigator.standalone === true)
  )
}

// Recarrega a página: o servidor manda o index.html sempre conferido de
// novo (no-cache), então vem a versão mais nova
export function reloadApp() {
  window.location.reload()
}

async function fetchServerVersion(): Promise<string | null> {
  try {
    const response = await fetch(`/version.json?t=${Date.now()}`, {
      cache: 'no-store',
    })
    if (!response.ok) return null
    const data: unknown = await response.json()
    if (data && typeof data === 'object' && 'version' in data) {
      return String(data.version)
    }
    return null
  } catch {
    // Sem internet ou servidor fora: tenta de novo na próxima vez
    return null
  }
}

// true quando o servidor já tem uma versão diferente da que está rodando.
// Confere ao abrir, ao voltar para o app (o iPhone "congela" o app em vez
// de recarregar) e a cada 5 minutos. Em desenvolvimento não confere.
export function useNewVersionAvailable() {
  const [available, setAvailable] = useState(false)

  useEffect(() => {
    if (import.meta.env.DEV || !APP_VERSION) return

    let cancelled = false

    async function check() {
      const serverVersion = await fetchServerVersion()
      if (!cancelled && serverVersion && serverVersion !== APP_VERSION) {
        setAvailable(true)
      }
    }

    function onVisibilityChange() {
      if (document.visibilityState === 'visible') check()
    }

    check()
    const timer = window.setInterval(check, CHECK_INTERVAL_MS)
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('focus', check)

    return () => {
      cancelled = true
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      window.removeEventListener('focus', check)
    }
  }, [])

  return available
}
