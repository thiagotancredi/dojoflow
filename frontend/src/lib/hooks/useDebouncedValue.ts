import { useEffect, useState } from 'react'

// Devolve "value" só depois que ele fica parado por "delayMs".
// Ex.: a busca só consulta a API 300 ms depois da última tecla.
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)

    // Nova tecla antes do prazo: cancela o timer anterior
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
