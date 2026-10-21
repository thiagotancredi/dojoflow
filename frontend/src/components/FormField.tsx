import type { ReactNode } from 'react'

import { Label } from '@/components/ui/label'

type FormFieldProps = {
  label: string
  htmlFor?: string
  // Mensagem de erro do campo (validação no navegador ou 422 da API)
  error?: string
  hint?: string
  children: ReactNode
}

// Rótulo + campo + erro, sempre no mesmo formato
export function FormField({
  label,
  htmlFor,
  error,
  hint,
  children,
}: FormFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor} className="text-xs text-muted-foreground">
        {label}
      </Label>
      {children}
      {error ? (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  )
}
