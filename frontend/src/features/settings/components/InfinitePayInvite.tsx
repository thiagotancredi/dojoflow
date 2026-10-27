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

  // Logo empilhado à esquerda nos dois estados (escolhas do Thiago em 26/10:
  // desligada "E2", ligada "G1 + F3")
  const logo = (
    <img
      src={infinitePayLogo}
      alt="InfinitePay"
      className="h-[52px] w-auto shrink-0 self-start sm:self-center"
    />
  )

  return (
    <div
      className={
        enabled
          ? // Ligada: verde-claro com a faixa verde-musgo à esquerda
            'rounded-2xl border border-chip-active-border border-l-[6px] border-l-sidebar-primary bg-chip-active p-4'
          : // Desligada: o mesmo desenho, em cinza
            'rounded-2xl border border-border border-l-[6px] border-l-muted-foreground/30 bg-muted p-4'
      }
    >
      {/* No celular, os botões vão para baixo do texto */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        {enabled ? (
          <>
            <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center">
              {logo}
              <div className="min-w-0 space-y-1.5">
                <p className="flex flex-wrap items-center gap-2 text-base leading-tight font-bold text-chip-active-foreground">
                  Baixa automática
                  <Badge className="rounded-full bg-sidebar-primary text-primary-foreground">
                    ✓ LIGADA
                  </Badge>
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
            <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center">
              {logo}
              <div className="min-w-0 space-y-1.5">
                <p className="flex flex-wrap items-center gap-2 text-base leading-tight font-bold">
                  Receba com baixa automática
                  <Badge className="rounded-full bg-sidebar-primary text-primary-foreground">
                    GRÁTIS
                  </Badge>
                </p>
                <p className="text-xs text-muted-foreground">
                  O aluno paga pela InfinitePay e a mensalidade fica paga
                  sozinha, na hora. Não custa nada para você: o Pix é sem taxa e
                  a taxa do cartão fica com o aluno.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <Tag tone="green">Sem custo para você</Tag>
                  <Tag tone="gray">Pix sem taxa</Tag>
                  <Tag tone="gray">Baixa na hora</Tag>
                </div>
              </div>
            </div>
            <Button
              className="self-start rounded-full bg-sidebar-primary text-primary-foreground hover:bg-sidebar-primary/90 sm:self-center"
              onClick={() => setDialog('connect')}
            >
              Ligar
            </Button>
          </>
        )}
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
    </div>
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
    <span className={`rounded-full px-2.5 py-0.5 text-xs ${color}`}>
      {children}
    </span>
  )
}
