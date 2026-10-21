import { useRef } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { BillingSettings } from '@/features/billing/api'
import { useBillingSettings, useSaveBillingSettings } from '@/features/billing/hooks'
import { showApiError } from '@/lib/api/errors'

// Mesmo texto de DEFAULT_MESSAGE_TEMPLATE (backend, services/billing.py).
// Salvar exatamente este texto faz a academia seguir o padrão.
const DEFAULT_MESSAGE_TEMPLATE =
  'Olá, {nome}! Tudo bem? 🥋\n\n' +
  'Passando para lembrar que a mensalidade da {academia} está em ' +
  'aberto: {valor} ({meses}).\n\n' +
  'Você pode pagar pelo Pix: {pix} ({recebedor}).\n\n' +
  'Se já pagou, desconsidere. Obrigado!'

// Marcadores trocados pelos dados de cada aluno ao abrir o WhatsApp
const MARKERS = [
  { marker: '{nome}', help: 'primeiro nome de quem recebe' },
  { marker: '{academia}', help: 'nome da academia' },
  { marker: '{valor}', help: 'total em atraso' },
  { marker: '{meses}', help: 'meses em atraso' },
  { marker: '{pix}', help: 'chave Pix' },
  { marker: '{recebedor}', help: 'nome de quem recebe' },
]

type FormValues = {
  pix_key: string
  recipient_name: string
  bank_details: string
  message_template: string
}

function toForm(settings: BillingSettings): FormValues {
  return {
    pix_key: settings.pix_key ?? '',
    recipient_name: settings.recipient_name ?? '',
    bank_details: settings.bank_details ?? '',
    message_template: settings.message_template ?? DEFAULT_MESSAGE_TEMPLATE,
  }
}

// Configurações → Cobrança: Pix, quem recebe e a mensagem do WhatsApp
export function BillingSettingsSection() {
  const settings = useBillingSettings()

  return (
    <section className="space-y-4 rounded-3xl bg-card p-5">
      <div>
        <h2 className="font-semibold">Cobrança</h2>
        <p className="text-xs text-muted-foreground">
          Usado na mensagem de cobrança que abre no WhatsApp.
        </p>
      </div>
      {settings.isLoading && !settings.data ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : settings.data ? (
        <BillingSettingsForm initial={settings.data} />
      ) : (
        <div className="space-y-2 text-sm">
          <p role="alert" className="text-destructive">
            Não foi possível carregar a cobrança.
          </p>
          <Button
            variant="outline"
            className="rounded-full"
            onClick={settings.refetch}
          >
            Tentar de novo
          </Button>
        </div>
      )}
    </section>
  )
}

function BillingSettingsForm({ initial }: { initial: BillingSettings }) {
  const { mutate, isPending } = useSaveBillingSettings()
  const form = useForm<FormValues>({ defaultValues: toForm(initial) })
  const { register, setValue, getValues, reset } = form
  const messageRef = useRef<HTMLTextAreaElement | null>(null)
  // register devolve o próprio "ref"; aqui ele também vai para messageRef,
  // para saber onde está o cursor do texto
  const { ref: registerMessageRef, ...messageField } = register(
    'message_template',
    {
      maxLength: { value: 1000, message: 'Até 1000 caracteres.' },
    },
  )

  // Clicar num marcador coloca ele onde o cursor está no texto
  function insertMarker(marker: string) {
    const textarea = messageRef.current
    const text = getValues('message_template')
    const start = textarea?.selectionStart ?? text.length
    const end = textarea?.selectionEnd ?? text.length
    setValue(
      'message_template',
      text.slice(0, start) + marker + text.slice(end),
      { shouldDirty: true },
    )
    // Depois que o React atualiza o campo: volta o foco, cursor após o marcador
    requestAnimationFrame(() => {
      textarea?.focus()
      textarea?.setSelectionRange(start + marker.length, start + marker.length)
    })
  }

  async function save(values: FormValues) {
    try {
      const saved = await mutate({
        pix_key: values.pix_key,
        recipient_name: values.recipient_name,
        bank_details: values.bank_details,
        message_template: values.message_template,
      })
      reset(toForm(saved))
      toast.success('Cobrança salva')
    } catch (error) {
      showApiError(error)
    }
  }

  const errors = form.formState.errors

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Chave Pix" htmlFor="billing-pix">
          <Input
            id="billing-pix"
            placeholder="e-mail, telefone, CPF/CNPJ ou chave aleatória"
            maxLength={140}
            className="rounded-xl"
            {...register('pix_key')}
          />
        </FormField>
        <FormField label="Nome de quem recebe" htmlFor="billing-recipient">
          <Input
            id="billing-recipient"
            placeholder="como aparece no Pix"
            maxLength={120}
            className="rounded-xl"
            {...register('recipient_name')}
          />
        </FormField>
        <div className="sm:col-span-2">
          <FormField
            label="Dados bancários (opcional)"
            htmlFor="billing-bank"
          >
            <Textarea
              id="billing-bank"
              placeholder="Banco · Agência · Conta"
              maxLength={500}
              className="rounded-xl"
              {...register('bank_details')}
            />
          </FormField>
        </div>
        <div className="space-y-2 sm:col-span-2">
          <FormField
            label="Mensagem de cobrança"
            htmlFor="billing-message"
            error={errors.message_template?.message}
          >
            <Textarea
              id="billing-message"
              maxLength={1000}
              className="min-h-36 rounded-xl"
              {...messageField}
              ref={(element) => {
                registerMessageRef(element)
                messageRef.current = element
              }}
            />
          </FormField>
          <div className="flex flex-wrap gap-1.5">
            {MARKERS.map(({ marker, help }) => (
              <button
                key={marker}
                type="button"
                title={help}
                onClick={() => insertMarker(marker)}
                className="rounded-full border px-2.5 py-0.5 font-mono text-xs text-muted-foreground hover:bg-accent"
              >
                {marker}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Clique num marcador para colocá-lo onde está o cursor. Cada um vira
            o dado do aluno: {MARKERS.map((item) => `${item.marker} = ${item.help}`).join(' · ')}.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          className="rounded-full"
          onClick={() =>
            setValue('message_template', DEFAULT_MESSAGE_TEMPLATE, {
              shouldDirty: true,
            })
          }
        >
          Restaurar texto padrão
        </Button>
        <Button type="submit" className="rounded-full" disabled={isPending}>
          {isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </div>
    </form>
  )
}
