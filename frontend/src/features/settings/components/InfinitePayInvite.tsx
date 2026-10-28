import { type ReactNode, useState } from 'react'
import { toast } from 'sonner'

// Logo oficial (kit de imprensa da InfinitePay), sem alteração
import infinitePayLogo from '@/assets/brand/infinitepay-logo.png'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { InfinitePaySetupDialog } from '@/features/settings/components/InfinitePaySetupDialog'
import {
  useDisconnectInfinitePay,
  useInfinitePay,
} from '@/features/settings/infinitepay-api'
import { showApiError } from '@/lib/api/errors'
import { cn } from '@/lib/utils'

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

  const {
    enabled,
    handle,
    tested_at: testedAt,
    key_last4: keyLast4,
  } = status.data

  async function turnOff() {
    try {
      await disconnect.mutate()
      toast.success('Baixa automática desligada')
      status.refetch()
    } catch (error) {
      showApiError(error)
    }
  }

  // Computador: logo empilhado à esquerda (escolhas do Thiago em 26/10:
  // desligada "E2", ligada "G1 + F3"). Celular: o logo vai para uma faixa
  // branca no topo do cartão e o texto usa a largura toda (28/10, "A2")
  const logo = (
    <img
      src={infinitePayLogo}
      alt="InfinitePay"
      className="hidden h-[52px] w-auto shrink-0 sm:block"
    />
  )

  const badge = (
    <Badge className="rounded-full bg-sidebar-primary text-primary-foreground">
      {enabled ? '✓ LIGADA' : 'GRÁTIS'}
    </Badge>
  )

  // Cartão próprio em Configurações (28/10: cobrança em três cartões)
  return (
    <section className="space-y-4 rounded-3xl bg-card p-5">
      <div className="space-y-1">
        <h2 className="font-semibold">Baixa automática</h2>
        <p className="text-xs text-muted-foreground">
          Receba pela InfinitePay e a mensalidade fica paga sozinha.
        </p>
      </div>

      <div
        className={cn(
          'overflow-hidden rounded-2xl border sm:border-l-[6px] sm:p-4',
          enabled
            ? // Ligada: verde-claro com a faixa verde-musgo à esquerda
              'border-chip-active-border bg-chip-active sm:border-l-sidebar-primary'
            : // Desligada: o mesmo desenho, em cinza
              'border-border bg-muted sm:border-l-muted-foreground/30',
        )}
      >
        {/* Só no celular: faixa branca com o logo e a etiqueta */}
        <div className="flex items-center justify-between gap-3 border-b bg-white px-4 py-2.5 sm:hidden">
          <img src={infinitePayLogo} alt="InfinitePay" className="h-9 w-auto" />
          {badge}
        </div>

        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-0">
          {enabled ? (
            <>
              <div className="flex min-w-0 flex-1 items-center gap-3">
                {logo}
                <div className="min-w-0 space-y-1.5">
                  <p className="flex flex-wrap items-center gap-2 text-base leading-tight font-bold text-chip-active-foreground">
                    Baixa automática
                    <span className="hidden sm:inline-flex">{badge}</span>
                  </p>
                  <p className="text-xs text-chip-active-foreground/85">
                    Tudo pronto! Cada pagamento do aluno já dá baixa na
                    mensalidade sozinho.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    <Tag strong>${handle}</Tag>
                    {keyLast4 && <Tag strong>chave ••••{keyLast4}</Tag>}
                    {testedAt && <Tag>testada em {formatDay(testedAt)}</Tag>}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:flex">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-full"
                  onClick={() => setDialog('key')}
                >
                  Trocar chave
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-full border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
                  disabled={disconnect.isPending}
                  onClick={() => setConfirmOff(true)}
                >
                  Desligar
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="flex min-w-0 flex-1 items-center gap-3">
                {logo}
                <div className="min-w-0 space-y-1.5">
                  <p className="flex flex-wrap items-center gap-2 text-base leading-tight font-bold">
                    Receba com baixa automática
                    <span className="hidden sm:inline-flex">{badge}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    O aluno paga pela InfinitePay e a mensalidade fica paga
                    sozinha, na hora. Não custa nada para você: o Pix é sem
                    taxa e a taxa do cartão fica com o aluno.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    <Tag tone="green">Sem custo para você</Tag>
                    <Tag tone="gray">Pix sem taxa</Tag>
                    <Tag tone="gray">Baixa na hora</Tag>
                  </div>
                </div>
              </div>
              <Button
                className="w-full rounded-full bg-sidebar-primary text-primary-foreground hover:bg-sidebar-primary/90 sm:w-auto"
                onClick={() => setDialog('connect')}
              >
                <span className="sm:hidden">Ligar baixa automática</span>
                <span className="hidden sm:inline">Ligar</span>
              </Button>
            </>
          )}
        </div>
      </div>

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
    </section>
  )
}

// Cor de cada tipo de etiqueta. Ligada: detalhes da conexão (tag, final da
// chave, data do teste). Desligada: benefícios, em cinza ou em verde.
const TAG_TONES = {
  strong: 'bg-muted font-semibold',
  soft: 'bg-muted text-muted-foreground',
  gray: 'bg-border font-semibold',
  green: 'bg-sidebar-primary font-semibold text-primary-foreground',
}

function Tag({
  children,
  strong,
  tone,
}: {
  children: ReactNode
  strong?: boolean
  tone?: keyof typeof TAG_TONES
}) {
  const color = TAG_TONES[tone ?? (strong ? 'strong' : 'soft')]
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] sm:px-2.5 sm:text-xs ${color}`}>
      {children}
    </span>
  )
}
