import { ArrowLeft, ArrowRight, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { FormField } from '@/components/FormField'
import { PasswordInput } from '@/components/PasswordInput'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useConnectInfinitePay } from '@/features/settings/infinitepay-api'
import type { InfinitePayStatus } from '@/features/settings/infinitepay-api'
import { messageFor } from '@/lib/api/errors'
import { cn } from '@/lib/utils'

const STEPS = ['Conta', 'Checkout', 'Sua tag e sua chave'] as const

type SetupValues = { handle: string; api_key: string }

type InfinitePaySetupDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  // Tag já salva (religar ou trocar a chave): o campo já vem preenchido
  handle: string | null
  // "Trocar chave" pula direto para a última etapa
  changeKeyOnly?: boolean
  onConnected: (status: InfinitePayStatus) => void
}

// Janela "Ligar a baixa automática": 3 etapas (Conta → Checkout → tag e
// chave). A última testa a conexão de verdade antes de ligar.
export function InfinitePaySetupDialog({
  open,
  onOpenChange,
  handle,
  changeKeyOnly = false,
  onConnected,
}: InfinitePaySetupDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {changeKeyOnly ? 'Trocar chave de API' : 'Ligar a baixa automática'}
          </DialogTitle>
          <DialogDescription>
            {changeKeyOnly
              ? 'Cole a chave nova; a gente testa antes de trocar.'
              : 'Leva uns 10 minutos, no app da InfinitePay.'}
          </DialogDescription>
        </DialogHeader>
        {/* Só existe com a janela aberta: abre sempre limpa (chave vazia) */}
        <SetupSteps
          handle={handle}
          firstStep={changeKeyOnly ? STEPS.length - 1 : 0}
          onCancel={() => onOpenChange(false)}
          onConnected={(status) => {
            onConnected(status)
            onOpenChange(false)
          }}
        />
      </DialogContent>
    </Dialog>
  )
}

function SetupSteps({
  handle,
  firstStep,
  onCancel,
  onConnected,
}: {
  handle: string | null
  firstStep: number
  onCancel: () => void
  onConnected: (status: InfinitePayStatus) => void
}) {
  const [step, setStep] = useState(firstStep)
  const [apiError, setApiError] = useState<string | null>(null)
  const { mutate, isPending } = useConnectInfinitePay()
  const form = useForm<SetupValues>({
    defaultValues: { handle: handle ? `$${handle}` : '', api_key: '' },
  })
  const {
    register,
    formState: { errors },
  } = form
  const isLast = step === STEPS.length - 1

  async function connect(values: SetupValues) {
    setApiError(null)
    try {
      const status = await mutate(values)
      toast.success('Baixa automática ligada')
      onConnected(status)
    } catch (error) {
      // O texto da API já diz o que fazer (ex.: criar uma chave nova)
      setApiError(messageFor(error))
    }
  }

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit(connect)}
      className="space-y-5"
    >
      {/* Etapas: 1 Conta · 2 Checkout · 3 Sua tag e sua chave */}
      <ol className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={cn(
              'flex items-center gap-1.5',
              index === step ? 'font-semibold' : 'text-muted-foreground',
            )}
          >
            <span
              className={cn(
                'flex size-5 items-center justify-center rounded-full border text-[0.7rem]',
                index === step && 'border-primary bg-primary text-primary-foreground',
                index < step && 'border-primary text-primary',
              )}
            >
              {index + 1}
            </span>
            {label}
          </li>
        ))}
      </ol>

      {step === 0 && <AccountStep />}
      {step === 1 && <CheckoutStep />}
      {isLast && (
        <div className="space-y-4">
          <FormField
            label="Sua InfiniteTag"
            htmlFor="infinitepay-handle"
            error={errors.handle?.message}
            hint="O nome com $ que aparece no app (ex.: $katsuflow)."
          >
            <Input
              id="infinitepay-handle"
              placeholder="$suatag"
              autoComplete="off"
              data-1p-ignore
              data-lpignore="true"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={61}
              className="rounded-xl"
              {...register('handle', {
                validate: (value) =>
                  value.replace(/[$\s]/g, '') !== '' || 'Informe a sua tag.',
              })}
            />
          </FormField>
          <FormField
            label="Chave de API"
            htmlFor="infinitepay-key"
            error={errors.api_key?.message}
          >
            {/* Não é senha: "one-time-code" e os data-* evitam que o
                navegador (ou 1Password/LastPass) cole aqui a senha salva
                do Katsuflow, que iria para a InfinitePay */}
            <PasswordInput
              id="infinitepay-key"
              autoComplete="one-time-code"
              data-1p-ignore
              data-lpignore="true"
              data-form-type="other"
              spellCheck={false}
              maxLength={200}
              className="rounded-xl"
              {...register('api_key', {
                validate: (value) =>
                  value.trim() !== '' || 'Cole a chave de API.',
              })}
            />
          </FormField>
          <div className="space-y-1 rounded-xl bg-muted/50 p-3 text-xs text-muted-foreground">
            <p>
              No app da InfinitePay: <strong>Checkout → Configurações → API
              Keys</strong> (Settings → API Keys) → criar uma chave (ex.: nome
              "katsuflow") → copiar e colar aqui.
            </p>
            <p>
              A chave aparece <strong>uma vez só</strong> no app. Aqui ela fica
              guardada com segurança e não volta a aparecer.
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            Ao testar, criamos um link de R$ 1,00 só para conferir a conexão.
            Ninguém é cobrado e ele expira sozinho.
          </p>
          {apiError && (
            <p
              role="alert"
              className="flex items-start gap-1.5 rounded-xl bg-destructive/10 p-3 text-sm text-destructive"
            >
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              {apiError}
            </p>
          )}
        </div>
      )}

      <div className="flex flex-wrap justify-between gap-2">
        {step > firstStep ? (
          <Button
            type="button"
            variant="ghost"
            className="rounded-full"
            onClick={() => setStep(step - 1)}
          >
            <ArrowLeft /> Voltar
          </Button>
        ) : (
          <Button
            type="button"
            variant="ghost"
            className="rounded-full"
            onClick={onCancel}
          >
            Cancelar
          </Button>
        )}
        {isLast ? (
          <Button type="submit" className="rounded-full" disabled={isPending}>
            {isPending ? 'Testando…' : 'Testar e ligar'}
          </Button>
        ) : (
          <Button
            type="button"
            className="rounded-full"
            onClick={() => setStep(step + 1)}
          >
            Próximo <ArrowRight />
          </Button>
        )}
      </div>
    </form>
  )
}

function AccountStep() {
  return (
    <StepList>
      <li>
        Baixe o app da <strong>InfinitePay</strong> e crie a sua conta (CPF
        serve).
      </li>
      <li>Dentro do app, cadastre uma chave Pix.</li>
      <li>
        Anote a sua <strong>InfiniteTag</strong>: o nome com $ que aparece no
        app (ex.: $katsuflow).
      </li>
    </StepList>
  )
}

function CheckoutStep() {
  return (
    <div className="space-y-3">
      <p className="text-sm">
        No app da InfinitePay, abra <strong>Checkout → Configurações</strong>{' '}
        <span className="text-muted-foreground">(Settings)</span>:
      </p>
      <StepList>
        <li>Se o app pedir, crie o primeiro checkout.</li>
        <li>
          Ligue <strong>"Habilitar Checkout Integrado"</strong>{' '}
          <span className="text-muted-foreground">
            (Enable Integrated Checkout)
          </span>{' '}
          <strong>pelo app do celular</strong>.
        </li>
        <li>
          Desligue <strong>"Etapa de endereço"</strong>{' '}
          <span className="text-muted-foreground">(Address step)</span>.
        </li>
        <li>
          Em <strong>Meios de pagamento</strong>{' '}
          <span className="text-muted-foreground">(Payment methods)</span>,
          deixe o cartão com <strong>"Repassar todas as taxas"</strong>{' '}
          <span className="text-muted-foreground">(Pass on all fees)</span>: a
          taxa do cartão fica com o aluno. O Pix não tem taxa.
        </li>
      </StepList>
      <p className="flex items-start gap-1.5 rounded-xl bg-muted/50 p-3 text-xs text-muted-foreground">
        <TriangleAlert className="mt-px size-3.5 shrink-0 text-status-pending" />
        Pelo site da InfinitePay o botão pode aparecer ligado sem valer. Se o
        teste falhar, desligue e ligue de novo pelo app do celular.
      </p>
    </div>
  )
}

function StepList({ children }: { children: ReactNode }) {
  return (
    <ol className="list-decimal space-y-2 pl-5 text-sm marker:text-muted-foreground">
      {children}
    </ol>
  )
}
