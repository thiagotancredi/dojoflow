import * as React from 'react'

import { cn } from '@/lib/utils'

// Campo de texto com várias linhas, no mesmo estilo do <Input>. Altura
// fixa (o mestre arrasta o canto para aumentar): a altura automática
// (field-sizing) deixava um traço da borda no Chrome
function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'block min-h-20 w-full min-w-0 resize-y rounded-lg border border-input bg-transparent px-2.5 py-2 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
