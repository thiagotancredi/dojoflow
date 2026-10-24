import { Check, CircleCheck, Copy, Loader2, ShieldCheck } from 'lucide-react'
import {
  type ReactNode,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from 'react'
import { useParams, useSearchParams } from 'react-router'

import logo from '@/assets/brand/logo-light.png'
import { Button } from '@/components/ui/button'
import { applyMode, currentMode } from '@/app/theme'
import {
  confirmPayment,
  createCheckout,
  isInvalidLink,
  type PayConfirm,
  type PublicPayment,
  usePublicPayment,
} from '@/features/pay/api'
import { messageFor } from '@/lib/api/errors'
import { formatMoney } from '@/lib/money'

// Volta do checkout: confere a cada 2 s, por até 30 s
const CONFIRM_POLL_MS = 2000
const CONFIRM_TIMEOUT_MS = 30000

// Página que o aluno abre pelo link da cobrança do WhatsApp: o que está
// vencido e como pagar — o código Pix (copia e cola) ou, com a baixa
// automática ligada, o botão que leva ao checkout da InfinitePay
export function PayPage() {
  const { token } = useParams()
  const payment = usePublicPayment(token)
  const confirming = useReturnFromCheckout(token, payment.refetch)
  const stillOpen = payment.data?.status !== 'clear'
  useLightMode()

  return (
    <div className="min-h-svh bg-background pb-6 text-foreground">
      {payment.data ? (
        <PaymentView
          token={token ?? ''}
          data={payment.data}
          confirming={confirming.active && stillOpen}
          justPaid={confirming.started && !stillOpen}
        />
      ) : payment.isLoading ? (
        <Message>Carregando…</Message>
      ) : isInvalidLink(payment.error) ? (
        <Message>
          Link inválido ou expirado. Peça um novo link para a academia.
        </Message>
      ) : (
        <Message>
          <span>Não foi possível carregar. Tente de novo.</span>
          <Button
            variant="outline"
            className="rounded-full"
            onClick={payment.refetch}
          >
            Tentar de novo
          </Button>
        </Message>
      )}
      <Footer />
    </div>
  )
}

// A página é sempre clara (cores do sistema), mesmo para quem usa o site
// no escuro; ao sair, volta como estava
function useLightMode() {
  useEffect(() => {
    const before = currentMode()
    applyMode('light')
    return () => applyMode(before)
  }, [])
}

// O aluno voltou do checkout: a InfinitePay acrescenta ao endereço
// order_nsu, transaction_nsu, slug (e receipt_url). Manda isso ao servidor
// uma vez, limpa o endereço e recarrega a página até a baixa aparecer
// (ou até o tempo acabar: aí volta à tela normal).
function useReturnFromCheckout(token: string | undefined, reload: () => void) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [deadline, setDeadline] = useState<number | null>(null)
  const [started, setStarted] = useState(false)
  // Guarda contra mandar duas vezes (o React de dev roda efeitos 2x)
  const sent = useRef(false)

  const orderNsu = searchParams.get('order_nsu')
  const transactionNsu = searchParams.get('transaction_nsu')
  const slug = searchParams.get('slug')
  const receiptUrl = searchParams.get('receipt_url')

  useEffect(() => {
    if (!token || !orderNsu || !transactionNsu || !slug || sent.current) {
      return
    }
    sent.current = true
    const body: PayConfirm = {
      order_nsu: orderNsu,
      transaction_nsu: transactionNsu,
      slug,
      receipt_url: receiptUrl,
    }
    // Endereço limpo: recarregar a página não manda de novo
    setSearchParams({}, { replace: true })
    setStarted(true)
    setDeadline(Date.now() + CONFIRM_TIMEOUT_MS)
    // Se falhar, o aviso da InfinitePay ainda dá a baixa; a página só
    // continua conferindo até o tempo acabar
    confirmPayment(token, body).catch(() => {})
  }, [token, orderNsu, transactionNsu, slug, receiptUrl, setSearchParams])

  // useEffectEvent: o intervalo sempre chama o "reload" mais recente
  const tick = useEffectEvent(() => {
    if (deadline !== null && Date.now() > deadline) setDeadline(null)
    else reload()
  })

  useEffect(() => {
    if (deadline === null) return
    const timer = setInterval(tick, CONFIRM_POLL_MS)
    return () => clearInterval(timer)
  }, [deadline])

  return { active: deadline !== null, started }
}

function PaymentView({
  token,
  data,
  confirming,
  justPaid,
}: {
  token: string
  data: PublicPayment
  // Voltou do checkout e a baixa ainda não apareceu
  confirming: boolean
  // Voltou do checkout e a baixa já entrou
  justPaid: boolean
}) {
  const count = data.items.length

  return (
    <main>
      {/* Faixa escura de ponta a ponta: academia e mestre */}
      <header className="bg-linear-160 from-brand-from from-30% to-brand-to px-4 pt-8 pb-16 text-center text-brand-foreground">
        <h1 className="text-xl leading-tight font-extrabold">
          {data.academy_name}
        </h1>
        {data.master_name && (
          <p className="mt-1 text-sm opacity-80">Mestre {data.master_name}</p>
        )}
      </header>

      {/* Conteúdo numa coluna centralizada (celular e computador) */}
      <div className="mx-auto max-w-[420px] space-y-3 px-4">
        {data.status === 'clear' ? (
          <section className="-mt-10 rounded-2xl bg-white p-6 text-center shadow-lg">
            <CircleCheck className="mx-auto size-10 text-sidebar-primary" />
            <p className="mt-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
              Olá, {data.greeting_name}
            </p>
            <p className="mt-1 text-lg font-bold">
              {justPaid ? 'Pagamento recebido!' : 'Tudo em dia!'}
            </p>
            <p className="text-sm text-muted-foreground">
              {justPaid
                ? 'Obrigado! Sua mensalidade está em dia.'
                : 'Nenhuma mensalidade pendente.'}
            </p>
          </section>
        ) : (
          <>
            {/* Total, "flutuando" por cima da faixa */}
            <section className="-mt-10 rounded-2xl bg-white p-4 text-center shadow-lg">
              <p className="text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
                Olá, {data.greeting_name} · total em aberto
              </p>
              <p className="my-1 text-3xl font-extrabold tracking-tight">
                {formatMoney(data.total)}
              </p>
              <span className="inline-block rounded-full border border-chip-active-border bg-chip-active px-2.5 py-0.5 text-xs font-bold text-chip-active-foreground">
                {count} {count === 1 ? 'mensalidade' : 'mensalidades'}
              </span>
            </section>

            <Card title="O que está em aberto">
              <ul className="divide-y divide-dashed">
                {data.items.map((item, index) => (
                  <li
                    key={`${item.label}-${index}`}
                    className="flex justify-between gap-3 py-1.5 text-sm"
                  >
                    <span>{item.label}</span>
                    <span className="shrink-0 tabular-nums">
                      {formatMoney(item.amount)}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>

            <Card title="Pagar para">
              <div className="flex items-center gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full border border-chip-active-border bg-chip-active text-lg text-chip-active-foreground">
                  ◆
                </span>
                <div>
                  <p className="text-sm font-semibold">{data.recipient_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {data.checkout_enabled
                      ? 'Recebe pela InfinitePay (Pix ou cartão)'
                      : 'Recebe pelo Pix'}
                  </p>
                </div>
              </div>
            </Card>

            {confirming ? (
              <p
                role="status"
                className="flex items-center justify-center gap-2 py-4 text-sm font-semibold"
              >
                <Loader2 className="size-4 animate-spin" />
                Confirmando seu pagamento…
              </p>
            ) : data.checkout_enabled ? (
              <CheckoutButton token={token} count={count} />
            ) : data.pix_code ? (
              <CopyPixCode code={data.pix_code} total={data.total} />
            ) : (
              <p className="py-2 text-center text-sm text-muted-foreground">
                Fale com a academia para pagar.
              </p>
            )}
          </>
        )}
      </div>
    </main>
  )
}

// Baixa automática ligada: um caminho só, o checkout da InfinitePay
function CheckoutButton({ token, count }: { token: string; count: number }) {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function goToCheckout() {
    setIsPending(true)
    setError(null)
    try {
      const { url } = await createCheckout(token)
      // Sai do Katsuflow para a página segura da InfinitePay
      window.location.assign(url)
    } catch (caught) {
      setError(messageFor(caught))
      setIsPending(false)
    }
  }

  return (
    <div className="space-y-2 pt-2">
      <Button
        size="lg"
        className="h-12 w-full rounded-full text-base font-bold"
        disabled={isPending}
        onClick={goToCheckout}
      >
        {isPending ? <Loader2 className="animate-spin" /> : <ShieldCheck />}
        {count > 1 ? 'Pagar mensalidades' : 'Pagar mensalidade'}
      </Button>
      {error && (
        <p role="alert" className="text-center text-sm text-destructive">
          {error}
        </p>
      )}
      <p className="text-center text-xs text-muted-foreground">
        Você vai para a página segura da InfinitePay. Lá você escolhe Pix ou
        cartão e confirma com um código que chega no seu WhatsApp.
      </p>
    </div>
  )
}

function CopyPixCode({ code, total }: { code: string; total: string }) {
  const [copied, setCopied] = useState(false)
  // Sem acesso à área de transferência: mostra o código para copiar à mão
  const [manual, setManual] = useState(false)
  const manualRef = useRef<HTMLTextAreaElement | null>(null)

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
    } catch {
      setManual(true)
      requestAnimationFrame(() => manualRef.current?.select())
    }
  }

  return (
    <div className="space-y-2 pt-2">
      <Button
        size="lg"
        className={`h-12 w-full rounded-full text-base font-bold ${copied ? 'bg-sidebar-primary hover:bg-sidebar-primary' : ''}`}
        onClick={copy}
      >
        {copied ? <Check /> : <Copy />}
        {copied ? 'Código copiado!' : 'Copiar código Pix'}
      </Button>
      {copied && (
        <p className="rounded-xl bg-primary px-3 py-2 text-center text-sm text-primary-foreground">
          Agora abra o app do seu banco → Pix → Pix copia e cola.
        </p>
      )}
      {manual && (
        <textarea
          ref={manualRef}
          readOnly
          value={code}
          aria-label="Código Pix"
          className="h-24 w-full rounded-xl border bg-white p-2 font-mono text-xs break-all"
        />
      )}
      <p className="text-center text-xs text-muted-foreground">
        Cole no app do seu banco, em "Pix copia e cola".
        <br />O valor de {formatMoney(total)} já vai preenchido.
      </p>
    </div>
  )
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border bg-card p-3.5">
      <p className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
        {title}
      </p>
      {children}
    </section>
  )
}

function Message({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-[60svh] max-w-[420px] flex-col items-center justify-center gap-3 px-6 text-center text-sm text-muted-foreground">
      {children}
    </main>
  )
}

// Rodapé: símbolo do lutador (recorte da logo) + nome Katsuflow
function Footer() {
  return (
    <footer className="mx-auto mt-8 max-w-[420px] px-4">
      <div className="flex flex-col items-center gap-1 border-t pt-3">
        <span className="text-[10px] tracking-wide text-muted-foreground">
          Cobrança enviada pelo
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-7 w-[29px] overflow-hidden">
            <img src={logo} alt="" className="h-7 max-w-none" />
          </span>
          <span className="text-base font-black tracking-tight">
            <span className="text-sidebar-primary">Katsu</span>
            <span className="text-foreground">flow</span>
          </span>
        </span>
      </div>
    </footer>
  )
}
