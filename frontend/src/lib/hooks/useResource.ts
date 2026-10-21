import { useEffect, useEffectEvent, useState } from 'react'

// Leitura de dados da API no formato da spec: { data, isLoading, error, refetch }
// (o mesmo do TanStack Query, para a troca futura mexer só aqui dentro).
//
// "key" identifica o que está sendo buscado: quando muda, busca de novo e
// cancela a busca anterior (AbortController). key = null → não busca nada.
export type Resource<T> = {
  data: T | null
  isLoading: boolean
  error: unknown
  refetch: () => void
}

type Loaded<T> = {
  key: string
  token: string
  data: T | null
  error: unknown
}

export function useResource<T>(
  key: string | null,
  load: (signal: AbortSignal) => Promise<T>,
  // keepPrevious: enquanto busca outra key, continua mostrando o resultado
  // anterior (bom para a lista enquanto o mestre digita; ruim para trocar
  // de aluno). Recarregar a mesma key (refetch) sempre mantém os dados.
  { keepPrevious = false }: { keepPrevious?: boolean } = {},
): Resource<T> {
  const [reloads, setReloads] = useState(0)
  const [loaded, setLoaded] = useState<Loaded<T> | null>(null)
  const token = `${key}#${reloads}`

  // useEffectEvent: a função sempre enxerga o "load" mais recente,
  // sem que o efeito precise rodar de novo quando ela muda
  const runLoad = useEffectEvent((signal: AbortSignal) => load(signal))

  useEffect(() => {
    if (key === null) return

    const controller = new AbortController()

    runLoad(controller.signal)
      .then((data) => setLoaded({ key, token, data, error: null }))
      .catch((error: unknown) => {
        // Cancelada porque a key mudou ou a tela fechou: não é erro
        if (!controller.signal.aborted) {
          // Falhou ao recarregar a mesma key: os dados anteriores ficam
          setLoaded((previous) => ({
            key,
            token,
            data: previous?.key === key ? previous.data : null,
            error,
          }))
        }
      })

    return () => controller.abort()
  }, [key, token])

  const isCurrent = loaded?.token === token
  // refetch da mesma key (ex.: depois de salvar) mantém os dados na tela
  const sameKey = loaded?.key === key

  return {
    data: isCurrent || sameKey || keepPrevious ? (loaded?.data ?? null) : null,
    isLoading: key !== null && !isCurrent,
    error: isCurrent ? loaded.error : null,
    refetch: () => setReloads((count) => count + 1),
  }
}
