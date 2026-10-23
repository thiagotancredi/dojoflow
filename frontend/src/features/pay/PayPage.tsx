import { Check, CircleCheck, Copy } from 'lucide-react'
import { type ReactNode, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router'

import logo from '@/assets/brand/logo-light.png'
import { Button } from '@/components/ui/button'
import { applyMode, currentMode } from '@/app/theme'
import {
  isInvalidLink,
  type PublicPayment,
  usePublicPayment,
} from '@/features/pay/api'
import { formatMoney } from '@/lib/money'

// Página que o aluno abre pelo link da cobrança do WhatsApp:
// o que está vencido e o botão que copia o código Pix (copia e cola)
export function PayPage() {
  const { token } = useParams()
  const payment = usePublicPayment(token)
  useLightMode()

  return (
    <div className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex min-h-svh max-w-[420px] flex-col">
        {payment.data ? (
          <PaymentView data={payment.data} />
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

function PaymentView({ data }: { data: PublicPayment }) {
  const count = data.items.length

  return (
    <main className="flex-1">
      {/* Faixa escura: academia e mestre */}
      <header className="bg-linear-160 from-[#2a2d33] from-30% to-[#155e75] px-4 pt-8 pb-16 text-center text-white">
        <h1 className="text-xl leading-tight font-extrabold">
          {data.academy_name}
        </h1>
        {data.master_name && (
          <p className="mt-1 text-sm opacity-80">Mestre {data.master_name}</p>
        )}
      </header>

      <div className="space-y-3 px-4">
        {data.status === 'clear' ? (
          <section className="-mt-10 rounded-2xl bg-white p-6 text-center shadow-lg">
            <CircleCheck className="mx-auto size-10 text-[#155e75]" />
            <p className="mt-2 text-lg font-bold">Tudo em dia!</p>
            <p className="text-sm text-muted-foreground">
              Nenhuma mensalidade pendente.
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
                    Recebe pelo Pix
                  </p>
                </div>
              </div>
            </Card>

            {data.pix_code ? (
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
        className="h-12 w-full rounded-full text-base font-bold"
        style={copied ? { backgroundColor: '#155e75' } : undefined}
        onClick={copy}
      >
        {copied ? <Check /> : <Copy />}
        {copied ? 'Código copiado!' : 'Copiar código Pix'}
      </Button>
      {copied && (
        <p className="rounded-xl bg-[#18191c] px-3 py-2 text-center text-sm text-white">
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
    <main className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center text-sm text-muted-foreground">
      {children}
    </main>
  )
}

// Rodapé: símbolo do lutador (recorte da logo) + nome Katsuflow
function Footer() {
  return (
    <footer className="mx-4 mt-6 mb-6 flex flex-col items-center gap-1 border-t pt-3">
      <span className="text-[10px] tracking-wide text-muted-foreground">
        Cobrança enviada pelo
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-7 w-[29px] overflow-hidden">
          <img src={logo} alt="" className="h-7 max-w-none" />
        </span>
        <span className="text-base font-black tracking-tight">
          <span className="text-[#155e75]">Katsu</span>
          <span className="text-[#2a2d33]">flow</span>
        </span>
      </span>
    </footer>
  )
}
