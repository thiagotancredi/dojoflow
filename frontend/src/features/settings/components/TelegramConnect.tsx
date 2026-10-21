import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { createTelegramLink } from '@/features/auth/api'
import type { TelegramLink } from '@/features/auth/api'
import { useAuth } from '@/features/auth/useAuth'
import { showApiError } from '@/lib/api/errors'
import { useMutation } from '@/lib/hooks/useMutation'

// De quanto em quanto tempo pergunta ao backend se o bot já confirmou
const POLL_INTERVAL_MS = 3000

// Conectar Telegram: gera um link de uso único que abre o bot. Enquanto o
// link vale, a página pergunta ao backend se a conexão já foi feita; quando
// foi, o mestre passa a ter telegram_linked e a seção some sozinha.
export function TelegramConnect() {
  const { reloadMaster } = useAuth()
  const [link, setLink] = useState<TelegramLink | null>(null)
  const [expired, setExpired] = useState(false)
  const { mutate, isPending } = useMutation(createTelegramLink)

  async function handleConnect() {
    setExpired(false)
    try {
      setLink(await mutate())
    } catch (error) {
      showApiError(error)
    }
  }

  // "Polling": enquanto há link, roda a cada 3 s. O return limpa o timer
  // quando o link muda ou a seção sai da tela (senão ele rodaria para sempre).
  useEffect(() => {
    if (!link) return

    const expiresAt = new Date(link.expires_at).getTime()
    let done = false

    const timer = setInterval(async () => {
      if (done) return
      if (Date.now() >= expiresAt) {
        done = true
        setLink(null)
        setExpired(true)
        return
      }
      try {
        const me = await reloadMaster()
        if (me.telegram_linked && !done) {
          done = true
          toast.success('Telegram conectado')
        }
      } catch {
        // Falha pontual de rede: tenta de novo na próxima volta
      }
    }, POLL_INTERVAL_MS)

    return () => {
      done = true
      clearInterval(timer)
    }
  }, [link, reloadMaster])

  async function copyCode(code: string) {
    try {
      await navigator.clipboard.writeText(code)
      toast.success('Código copiado')
    } catch {
      toast.error('Não deu para copiar. Selecione o código e copie à mão.')
    }
  }

  return (
    <div className="max-w-xl space-y-2">
      <h3 className="text-sm font-medium">Telegram</h3>

      {!link && (
        <>
          <p className="text-sm text-muted-foreground">
            Conecte sua conta ao bot para cadastrar alunos pelo celular.
          </p>
          {expired && (
            <p role="alert" className="text-sm text-destructive">
              O link expirou. Gere outro para conectar.
            </p>
          )}
          <Button
            variant="outline"
            className="rounded-full"
            onClick={handleConnect}
            disabled={isPending}
          >
            {isPending ? 'Gerando link…' : 'Conectar Telegram'}
          </Button>
        </>
      )}

      {link?.deep_link && (
        <>
          <p className="text-sm text-muted-foreground">
            Abra o bot e toque em <strong>Iniciar</strong>.
          </p>
          {/* Link de verdade (não window.open): o navegador não bloqueia */}
          <Button asChild className="rounded-full">
            <a href={link.deep_link} target="_blank" rel="noreferrer">
              Abrir o bot no Telegram
            </a>
          </Button>
        </>
      )}

      {/* Sem o nome do bot configurado no servidor, não há link direto:
          o bot também aceita o código enviado como mensagem */}
      {link && !link.deep_link && (
        <>
          <p className="text-sm text-muted-foreground">
            Envie esta mensagem para o bot do DojoFlow no Telegram:
          </p>
          <code className="block rounded-xl bg-muted p-3 text-xs break-all">
            link_{link.token}
          </code>
          <Button
            variant="outline"
            className="rounded-full"
            onClick={() => copyCode(`link_${link.token}`)}
          >
            Copiar código
          </Button>
        </>
      )}

      {link && (
        <p className="text-xs text-muted-foreground">
          Aguardando a confirmação do bot… Esta página atualiza sozinha. O
          link vale até {formatTime(link.expires_at)}.
        </p>
      )}
    </div>
  )
}

// "2026-10-20T15:42:00Z" → "12:42" (no fuso do navegador)
function formatTime(isoDateTime: string) {
  return new Date(isoDateTime).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
