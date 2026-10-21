import { useState } from 'react'

// Escrita na API no formato da spec: { mutate, isPending, error }.
// mutate devolve a resposta, ou lança o erro (a tela decide o que mostrar).
export function useMutation<Args extends unknown[], Result>(
  action: (...args: Args) => Promise<Result>,
) {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function mutate(...args: Args): Promise<Result> {
    setIsPending(true)
    setError(null)

    try {
      return await action(...args)
    } catch (caught) {
      setError(caught)
      throw caught
    } finally {
      setIsPending(false)
    }
  }

  return { mutate, isPending, error }
}
