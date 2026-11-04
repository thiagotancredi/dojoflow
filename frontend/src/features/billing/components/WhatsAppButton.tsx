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
  // Só o ícone (tabelas apertadas); o texto vai para o tooltip
  iconOnly?: boolean
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
  iconOnly = false,
}: WhatsAppButtonProps) {
  const [open, setOpen] = useState(false)
  const buttonSize = iconOnly ? (size === 'sm' ? 'icon-sm' : 'icon') : size
  const content = iconOnly ? (
    <MessageCircle />
  ) : (
    <>
      <MessageCircle /> {label}
    </>
  )

  if (!url) {
    return (
      <Button
        variant="outline"
        size={buttonSize}
        disabled
        title="Sem telefone ou nada a cobrar"
        aria-label={iconOnly ? `${label}: sem telefone ou nada a cobrar` : undefined}
        className={cn('rounded-full', className)}
      >
        {content}
      </Button>
    )
  }

  return (
    <>
      <Button
        variant="outline"
        size={buttonSize}
        title={iconOnly ? `Cobrar pelo ${label}` : undefined}
        aria-label={iconOnly ? `Cobrar ${studentName} pelo ${label}` : undefined}
        className={cn('rounded-full', className)}
        onClick={() => setOpen(true)}
      >
        {content}
      </Button>

      <WhatsAppDialog
        url={url}
        studentName={studentName}
        responsibleName={responsibleName}
        open={open}
        onOpenChange={setOpen}
      />
    </>
  )
}

// Janela "Cobrar fulano": a mensagem, para quem vai e "Abrir no WhatsApp".
// Separada do botão para poder abrir de um menu (ex.: "⋯" no celular)
export function WhatsAppDialog({
  url,
  studentName,
  responsibleName,
  open,
  onOpenChange,
}: {
  url: string
  studentName: string
  responsibleName?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { phone, text } = parseWhatsAppUrl(url)

  return (
  <Dialog open={open} onOpenChange={onOpenChange}>
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
            onClick={() => onOpenChange(false)}
          >
            Cancelar
          </Button>
          <Button asChild className="h-10 rounded-full">
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              onClick={() => onOpenChange(false)}
            >
              <MessageCircle /> Abrir no WhatsApp
            </a>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
