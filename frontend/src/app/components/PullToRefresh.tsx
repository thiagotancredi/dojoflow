import { useEffect, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'

import { isStandalone, reloadApp } from '@/lib/appUpdate'
import { cn } from '@/lib/utils'

// Quanto puxar (em px, já com a resistência) para atualizar
const THRESHOLD = 70
const MAX_PULL = 110

// Puxar para baixo no topo da página recarrega. Só no app instalado: no
// navegador (Safari/Chrome) o próprio navegador já faz isso.
export function PullToRefresh() {
  const [pull, setPull] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  // Valores lidos pelos eventos de toque sem recriar os listeners
  const startY = useRef<number | null>(null)
  const current = useRef(0)

  useEffect(() => {
    if (!isStandalone()) return

    function onTouchStart(event: TouchEvent) {
      if (window.scrollY > 0 || event.touches.length !== 1) return
      // Janelas e gavetas têm a própria rolagem: puxar nelas não atualiza
      const target = event.target as Element | null
      if (target?.closest('[role="dialog"], [role="alertdialog"], [data-no-pull-refresh]')) {
        return
      }
      startY.current = event.touches[0].clientY
    }

    function onTouchMove(event: TouchEvent) {
      if (startY.current === null) return
      const delta = event.touches[0].clientY - startY.current
      if (delta <= 0 || window.scrollY > 0) {
        current.current = 0
        setPull(0)
        return
      }
      // Metade da distância do dedo: dá a sensação de "resistência"
      current.current = Math.min(delta * 0.5, MAX_PULL)
      setPull(current.current)
    }

    function onTouchEnd() {
      if (startY.current === null) return
      startY.current = null
      if (current.current >= THRESHOLD) {
        setRefreshing(true)
        reloadApp()
      } else {
        setPull(0)
      }
      current.current = 0
    }

    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: true })
    window.addEventListener('touchend', onTouchEnd)
    window.addEventListener('touchcancel', onTouchEnd)

    return () => {
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('touchend', onTouchEnd)
      window.removeEventListener('touchcancel', onTouchEnd)
    }
  }, [])

  if (pull === 0 && !refreshing) return null

  const ready = refreshing || pull >= THRESHOLD

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-x-0 top-[max(0.5rem,env(safe-area-inset-top))] z-50 flex justify-center"
      style={{ transform: `translateY(${refreshing ? THRESHOLD / 2 : pull / 2}px)` }}
    >
      <div
        className="grid size-10 place-items-center rounded-full bg-card shadow-md shadow-black/15"
        style={{ opacity: refreshing ? 1 : Math.min(pull / THRESHOLD, 1) }}
      >
        <RefreshCw
          className={cn(
            'size-5',
            ready ? 'text-sidebar-primary' : 'text-muted-foreground',
            refreshing && 'animate-spin',
          )}
          // Gira enquanto puxa; ao soltar, gira sozinho (animate-spin)
          style={refreshing ? undefined : { transform: `rotate(${pull * 3}deg)` }}
        />
      </div>
    </div>
  )
}
