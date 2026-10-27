import { Mail } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  useEmailBilling,
  useEmailPreview,
  useSetEmailBilling,
} from '@/features/settings/email-billing-api'
import { showApiError } from '@/lib/api/errors'

const MONTHS = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]

// Próximo dia 1º às 8h a partir de agora (hora do navegador). No dia 1º
// antes das 8h, o próximo envio é o de hoje.
function nextSendMonth(now: Date) {
  const beforeSend = now.getDate() === 1 && now.getHours() < 8
  const month = beforeSend ? now.getMonth() : (now.getMonth() + 1) % 12
  return MONTHS[month]
}

// Cartão "Cobrança por e-mail", logo abaixo do convite da InfinitePay.
export function EmailBillingCard() {
  const status = useEmailBilling()
  const setBilling = useSetEmailBilling()
  // 'turn-on' = prévia com o botão "Ligar cobrança por e-mail"
  const [dialog, setDialog] = useState<'view' | 'turn-on' | null>(null)
  const [confirmOff, setConfirmOff] = useState(false)
  const preview = useEmailPreview(dialog !== null)

  // Sem os dados ainda (ou se falhou), não ocupa espaço
  if (!status.data) return null

  const {
    enabled,
    can_enable: canEnable,
    students_without_email: withoutEmail,
  } = status.data
  // Ligada, mas sem cobrança configurada: o worker não envia nada
  const notConfigured = enabled && !canEnable

  async function change(value: boolean) {
    try {
      await setBilling.mutate(value)
      toast.success(
        value ? 'Cobrança por e-mail ligada' : 'Cobrança por e-mail desligada',
      )
      setDialog(null)
    } catch (error) {
      showApiError(error)
    } finally {
      // Sempre relê: o aviso "sem e-mail" e o botão acompanham o servidor
      status.refetch()
    }
  }

  return (
    <div
      className={
        enabled
          ? 'rounded-2xl border border-chip-active-border border-l-[6px] border-l-sidebar-primary bg-chip-active p-4'
          : 'rounded-2xl border border-border border-l-[6px] border-l-muted-foreground/30 bg-muted p-4'
      }
    >
      {/* No celular, os botões vão para baixo do texto */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center">
          <span
            className={`flex size-[52px] shrink-0 items-center justify-center rounded-full ${
              enabled
                ? 'bg-sidebar-primary text-primary-foreground'
                : 'bg-border text-muted-foreground'
            }`}
          >
            <Mail className="size-6" aria-hidden />
          </span>
          <div className="min-w-0 space-y-1.5">
            <p
              className={`flex flex-wrap items-center gap-2 text-base leading-tight font-bold ${
                enabled ? 'text-chip-active-foreground' : ''
              }`}
            >
              Cobrança por e-mail
              {enabled && (
                <Badge className="rounded-full bg-sidebar-primary text-primary-foreground">
                  ✓ LIGADA
                </Badge>
              )}
            </p>
            <p
              className={`text-xs ${
                enabled
                  ? 'text-chip-active-foreground/85'
                  : 'text-muted-foreground'
              }`}
            >
              {!enabled
                ? 'Todo dia 1º, às 8h, o aluno recebe o link de pagamento.'
                : notConfigured
                  ? 'Nada será enviado até a cobrança ser configurada.'
                  : `Próximo envio: 1º de ${nextSendMonth(new Date())}, às 8h.`}
            </p>
            {/* Ligada, mas a chave Pix ou a InfinitePay saiu depois */}
            {notConfigured && (
              <p className="text-xs font-medium text-amber-700 dark:text-amber-400">
                Configure a chave Pix ou ligue a InfinitePay primeiro.
              </p>
            )}
            {withoutEmail > 0 && (
              <p className="text-xs font-medium text-amber-700 dark:text-amber-400">
                {withoutEmail} {withoutEmail === 1 ? 'aluno' : 'alunos'} sem
                e-mail ·{' '}
                <Link
                  to="/app/alunos?sem-email=1"
                  className="font-bold underline underline-offset-2"
                >
                  ver quem
                </Link>
              </p>
            )}
            {!enabled && !canEnable && (
              <p className="text-xs text-muted-foreground">
                Configure a chave Pix ou ligue a InfinitePay primeiro.
              </p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-full"
            onClick={() => setDialog('view')}
          >
            Ver e-mail
          </Button>
          {enabled ? (
            <Button
              variant="outline"
              size="sm"
              className="rounded-full border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
              disabled={setBilling.isPending}
              onClick={() => setConfirmOff(true)}
            >
              Desligar
            </Button>
          ) : (
            <Button
              size="sm"
              className="rounded-full bg-sidebar-primary text-primary-foreground hover:bg-sidebar-primary/90"
              disabled={!canEnable || setBilling.isPending}
              onClick={() => setDialog('turn-on')}
            >
              Ligar
            </Button>
          )}
        </div>
      </div>

      <Dialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) setDialog(null)
        }}
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>E-mail que o aluno recebe</DialogTitle>
            <DialogDescription>
              {preview.data
                ? `Assunto: ${preview.data.subject}`
                : 'Prévia do e-mail do dia 1º.'}
            </DialogDescription>
          </DialogHeader>
          {preview.data ? (
            <iframe
              title="Prévia do e-mail de cobrança"
              sandbox=""
              srcDoc={preview.data.html}
              className="h-[60dvh] w-full rounded-lg border bg-white"
            />
          ) : preview.error ? (
            <p role="alert" className="text-sm text-destructive">
              Não foi possível carregar a prévia.
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Carregando…</p>
          )}
          {dialog === 'turn-on' && (
            <DialogFooter>
              <Button
                className="rounded-full bg-sidebar-primary text-primary-foreground hover:bg-sidebar-primary/90"
                disabled={setBilling.isPending}
                onClick={() => change(true)}
              >
                Ligar cobrança por e-mail
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={confirmOff}
        onOpenChange={setConfirmOff}
        title="Desligar a cobrança por e-mail?"
        description="Os alunos deixam de receber o link no dia 1º."
        confirmLabel="Desligar"
        onConfirm={() => change(false)}
      />
    </div>
  )
}
