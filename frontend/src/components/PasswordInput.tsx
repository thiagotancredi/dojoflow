import { Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import type { ComponentProps } from 'react'

import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

// Campo de senha com o botão de olho para mostrar/esconder o que foi digitado.
// Aceita as mesmas props de um <Input> (id, value, onChange, autoComplete...).
export function PasswordInput({
  className,
  ...props
}: Omit<ComponentProps<typeof Input>, 'type'>) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="relative">
      <Input
        {...props}
        type={visible ? 'text' : 'password'}
        className={cn('pr-9', className)}
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? 'Esconder senha' : 'Mostrar senha'}
        className="absolute top-1/2 right-3 -translate-y-1/2 text-muted-foreground"
      >
        {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  )
}
