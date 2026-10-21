import { CircleCheck, Copy, TriangleAlert } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { buildWhatsAppAccessMessage } from '@/features/admin/api'

export type Credentials = {
  title: string
  masterName: string
  email: string
  password: string
}

// Senha recém-gerada + mensagem pronta para colar no WhatsApp do mestre.
// A senha não fica guardada em lugar nenhum: só aparece aqui.
export function CredentialsDialog({
  credentials,
  onClose,
}: {
  credentials: Credentials | null
  onClose: () => void
}) {
  const message = credentials
    ? buildWhatsAppAccessMessage(credentials.email, credentials.password)
    : ''

  async function copy() {
    try {
      await navigator.clipboard.writeText(message)
      toast.success('Mensagem copiada')
    } catch {
      toast.error('Não deu para copiar. Selecione o texto e copie à mão.')
    }
  }

  return (
    <Dialog
      open={credentials !== null}
      onOpenChange={(open) => !open && onClose()}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-status-exempt">
            <CircleCheck className="size-5" />
            {credentials?.title}
          </DialogTitle>
          <DialogDescription>
            Mande esta mensagem para {credentials?.masterName} no WhatsApp:
          </DialogDescription>
        </DialogHeader>
        <pre className="rounded-2xl border bg-muted p-4 font-mono text-sm leading-relaxed whitespace-pre-wrap select-all">
          {message}
        </pre>
        <p className="flex items-start gap-2 text-xs text-muted-foreground">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          A senha só aparece agora. Se perder, use "Trocar senha".
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" className="rounded-full" onClick={onClose}>
            Fechar
          </Button>
          <Button className="rounded-full" onClick={() => void copy()}>
            <Copy className="size-4" />
            Copiar mensagem
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
