import { RefreshCw } from 'lucide-react'

import { reloadApp, useNewVersionAvailable } from '@/lib/appUpdate'

// Faixa no topo quando sai uma versão nova do site. Não recarrega sozinho:
// a pessoa pode estar no meio de um formulário. Um toque atualiza.
export function UpdateBanner() {
  const available = useNewVersionAvailable()

  if (!available) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 top-[max(0.75rem,env(safe-area-inset-top))] z-50 flex justify-center px-3">
      <div
        role="status"
        className="pointer-events-auto flex items-center gap-3 rounded-full bg-sidebar py-1.5 pr-1.5 pl-4 text-sm text-sidebar-foreground shadow-lg shadow-black/20"
      >
        <span>Nova versão disponível</span>
        <button
          type="button"
          onClick={reloadApp}
          className="inline-flex items-center gap-1.5 rounded-full bg-sidebar-primary px-3 py-1 font-medium text-primary-foreground"
        >
          <RefreshCw aria-hidden="true" className="size-3.5" /> Atualizar
        </button>
      </div>
    </div>
  )
}
