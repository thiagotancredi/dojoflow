import { CircleCheck, Zap } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { InfinitePaySetupDialog } from '@/features/settings/components/InfinitePaySetupDialog'
import {
  useDisconnectInfinitePay,
  useInfinitePay,
} from '@/features/settings/infinitepay-api'
import { showApiError } from '@/lib/api/errors'

// "2026-10-24T09:30:00Z" → "24/10/2026" (no fuso do navegador)
function formatDay(isoDateTime: string) {
  return new Date(isoDateTime).toLocaleDateString('pt-BR')
}

// Topo do cartão Cobrança: convite para ligar a baixa automática pela
// InfinitePay, ou a situação dela (ligada, trocar chave, desligar).
export function InfinitePayInvite() {
  const status = useInfinitePay()
  const disconnect = useDisconnectInfinitePay()
  // null = janela fechada; 'connect' = 3 etapas; 'key' = só a chave
  const [dialog, setDialog] = useState<'connect' | 'key' | null>(null)
  const [confirmOff, setConfirmOff] = useState(false)

  // Sem os dados ainda (ou se falhou), não ocupa espaço: o resto do cartão
  // continua funcionando
  if (!status.data) return null

  const { enabled, handle, tested_at: testedAt } = status.data

  async function turnOff() {
    try {
      await disconnect.mutate()
      toast.success('Baixa automática desligada')
      status.refetch()
    } catch (error) {
      showApiError(error)
    }
  }

  return (
    <div className="rounded-2xl border border-primary/30 bg-primary/5 p-4">
      {enabled ? (
        // No celular, os botões vão para baixo do texto
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <p className="flex min-w-0 flex-1 items-start gap-2 text-sm">
            <CircleCheck className="mt-0.5 size-4 shrink-0 text-primary" />
            <span>
              <strong>Baixa automática ligada</strong> · ${handle}
              {testedAt && (
                <span className="text-muted-foreground">
                  {' '}
                  · testada em {formatDay(testedAt)}
                </span>
              )}
            </span>
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-full"
              onClick={() => setDialog('key')}
            >
              Trocar chave
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="rounded-full"
              disabled={disconnect.isPending}
              onClick={() => setConfirmOff(true)}
            >
              Desligar
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
          <div className="min-w-0 flex-1 space-y-1">
            <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
              <Zap className="size-4 text-primary" />
              Receba com baixa automática
              <Badge className="rounded-full">GRÁTIS</Badge>
            </p>
            <p className="text-xs text-muted-foreground">
              O aluno paga pela InfinitePay e a mensalidade fica paga sozinha,
              na hora. Pix sem taxa.
            </p>
          </div>
          <Button className="rounded-full" onClick={() => setDialog('connect')}>
            Ligar
          </Button>
        </div>
      )}

      <InfinitePaySetupDialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) setDialog(null)
        }}
        handle={handle}
        changeKeyOnly={dialog === 'key'}
        onConnected={() => status.refetch()}
      />
      <ConfirmDialog
        open={confirmOff}
        onOpenChange={setConfirmOff}
        title="Desligar a baixa automática?"
        description="A página de pagamento volta para o Pix copia e cola na hora. O que já foi pago continua registrado."
        confirmLabel="Desligar"
        onConfirm={turnOff}
      />
    </div>
  )
}
