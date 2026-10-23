import { MessageCircle } from 'lucide-react'
import { useState } from 'react'

import { InfoTip } from '@/components/InfoTip'
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
  // Texto do botão (padrão: "WhatsApp")
  label?: string
}

// Botão WhatsApp: mostra antes a mensagem e para quem vai; "Abrir no
// WhatsApp" abre a conversa com o texto já escrito
export function WhatsAppButton({
  url,
  studentName,
  responsibleName,
  size = 'default',
  className,
  label = 'WhatsApp',
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
        <MessageCircle /> {label}
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
        <MessageCircle /> {label}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cobrar {studentName}</DialogTitle>
            {/* "Para…" só quando vai para outra pessoa (o responsável);
                para o próprio aluno, o nome já está no título */}
            <DialogDescription>
              {responsibleName
                ? `Para ${responsibleName} (responsável) · ${formatPhone(phone)}`
                : formatPhone(phone)}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-1.5">
            <WhatsAppMessage text={text} />
            {/* Logo abaixo do balão, à direita (como a hora no WhatsApp) */}
            <p className="flex items-center justify-end gap-1 text-xs text-muted-foreground">
              Pode editar no WhatsApp
              <InfoTip label="Sobre editar a mensagem">
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Dá para mudar o texto no WhatsApp antes de enviar. O texto
                  padrão fica em Configurações → Cobrança.
                </p>
              </InfoTip>
            </p>
          </div>

          {/* Dois botões do mesmo tamanho, na largura toda */}
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              className="h-10 rounded-full"
              onClick={() => setOpen(false)}
            >
              Cancelar
            </Button>
            <Button asChild className="h-10 rounded-full">
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
