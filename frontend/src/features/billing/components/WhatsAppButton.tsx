import { MessageCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type WhatsAppButtonProps = {
  // Link wa.me pronto (vem da API); null = sem atraso ou sem telefone
  url: string | null | undefined
  size?: 'sm' | 'default'
  className?: string
}

// Abre o WhatsApp com a mensagem de cobrança já escrita
export function WhatsAppButton({
  url,
  size = 'default',
  className,
}: WhatsAppButtonProps) {
  if (!url) {
    return (
      <Button
        variant="outline"
        size={size}
        disabled
        title="Sem telefone ou sem atraso"
        className={cn('rounded-full', className)}
      >
        <MessageCircle /> WhatsApp
      </Button>
    )
  }

  return (
    <Button
      asChild
      variant="outline"
      size={size}
      className={cn('rounded-full', className)}
    >
      <a href={url} target="_blank" rel="noreferrer">
        <MessageCircle /> WhatsApp
      </a>
    </Button>
  )
}
