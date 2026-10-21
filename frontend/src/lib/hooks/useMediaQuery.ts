import { useSyncExternalStore } from 'react'

// true enquanto a media query do CSS bater (ex.: '(min-width: 768px)').
// Redesenha sozinho quando a janela muda de tamanho.
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query)
      list.addEventListener('change', onChange)
      return () => list.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
  )
}
