import { MessageCircle } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { WhatsAppMessage } from '@/features/billing/components/WhatsAppMessage'
import { parseWhatsAppUrl } from '@/features/billing/whatsapp'
import { formatPhone } from '@/lib/format'
import { cn } from '@/lib/utils'

type WhatsAppButtonProps = {
  // Link wa.me pronto (vem da API); null = sem atraso ou sem telefone
  url: string | null | undefined
  studentName: string
  // Quando a cobrança vai para o responsável (aluno menor), o nome dele
  responsibleName?: string | null
  size?: 'sm' | 'default'
  className?: string
}

// Botão WhatsApp: mostra antes a mensagem e para quem vai; "Abrir no
// WhatsApp" abre a conversa com o texto já escrito
export function WhatsAppButton({
  url,
  studentName,
  responsibleName,
  size = 'default',
  className,
}: WhatsAppButtonProps) {
  const [open, setOpen] = useState(false)

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

  const { phone, text } = parseWhatsAppUrl(url)

  return (
    <>
      <Button
        variant="outline"
        size={size}
        className={cn('rounded-full', className)}
        onClick={() => setOpen(true)}
      >
        <MessageCircle /> WhatsApp
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cobrança · {studentName}</DialogTitle>
            <DialogDescription>
              Para: {responsibleName ? `${responsibleName} (responsável) · ` : ''}
              {formatPhone(phone)}
            </DialogDescription>
          </DialogHeader>

          <WhatsAppMessage text={text} />
          <p className="text-xs text-muted-foreground">
            Dá para mudar o texto no WhatsApp antes de enviar. O texto padrão
            fica em Configurações → Cobrança.
          </p>

          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              className="rounded-full"
              onClick={() => setOpen(false)}
            >
              Cancelar
            </Button>
            <Button asChild className="rounded-full">
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                onClick={() => setOpen(false)}
              >
                <MessageCircle /> Abrir no WhatsApp
              </a>
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
