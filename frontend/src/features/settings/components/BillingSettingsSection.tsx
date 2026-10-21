import { MessageCircle, RotateCcw, TriangleAlert } from 'lucide-react'
import { Fragment, useRef } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'

import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/features/auth/useAuth'
import type { BillingSettings } from '@/features/billing/api'
import { WhatsAppMessage } from '@/features/billing/components/WhatsAppMessage'
import { useBillingSettings, useSaveBillingSettings } from '@/features/billing/hooks'
import { fillTemplate } from '@/features/billing/whatsapp'
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
  message_template: string
}

function toForm(settings: BillingSettings): FormValues {
  return {
    pix_key: settings.pix_key ?? '',
    recipient_name: settings.recipient_name ?? '',
    message_template: settings.message_template ?? DEFAULT_MESSAGE_TEMPLATE,
  }
}

// Configurações → Cobrança: Pix, quem recebe e a mensagem do WhatsApp
export function BillingSettingsSection() {
  const settings = useBillingSettings()

  return (
    <section className="space-y-6 rounded-3xl bg-card p-5">
      <div>
        <h2 className="font-semibold">Cobrança</h2>
        <p className="text-xs text-muted-foreground">
          Como você cobra os alunos pelo WhatsApp.
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
  const academyName = useAuth().master?.academy.name ?? ''
  // Prévia: o texto como chega no WhatsApp, com um aluno de exemplo
  const [template, pixKey, recipientName] = useWatch({
    control: form.control,
    name: ['message_template', 'pix_key', 'recipient_name'],
  })
  const preview = fillTemplate(template || DEFAULT_MESSAGE_TEMPLATE, {
    nome: 'Ana',
    academia: academyName,
    valor: 'R$ 150,00',
    meses: 'janeiro e fevereiro',
    // Igual ao backend: sem Pix fica vazio; sem recebedor, a academia
    pix: pixKey.trim(),
    recebedor: recipientName.trim() || academyName,
  })
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
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-8">
      {/* Bloco 1: para onde o aluno paga */}
      <div className="space-y-4">
        <BlockTitle
          title="Pix"
          description="Aparece na mensagem para o aluno saber para onde pagar."
        />
        <div className="grid gap-4 sm:grid-cols-2">
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
        </div>
      </div>

      <Separator />

      {/* Bloco 2: o texto (esquerda) e como ele chega (direita) */}
      <div className="space-y-4">
        <BlockTitle
          title="Mensagem de cobrança"
          description="O texto que abre no WhatsApp quando você cobra um aluno."
        />
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-4">
            <Label htmlFor="billing-message" className="sr-only">
              Mensagem de cobrança
            </Label>
            <Textarea
              id="billing-message"
              maxLength={1000}
              className="min-h-48 rounded-xl"
              {...messageField}
              ref={(element) => {
                registerMessageRef(element)
                messageRef.current = element
              }}
            />
            {errors.message_template && (
              <p role="alert" className="text-xs text-destructive">
                {errors.message_template.message}
              </p>
            )}

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Inserir no texto (entra onde está o cursor):
              </p>
              <div className="flex flex-wrap gap-2">
                {MARKERS.map(({ marker, help }) => (
                  <button
                    key={marker}
                    type="button"
                    title={help}
                    onClick={() => insertMarker(marker)}
                    className="rounded-full border px-3 py-1 font-mono text-xs hover:bg-accent"
                  >
                    {marker}
                  </button>
                ))}
              </div>
              <details className="text-xs text-muted-foreground">
                <summary className="w-fit cursor-pointer hover:text-foreground">
                  O que cada marcador significa?
                </summary>
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                  {MARKERS.map(({ marker, help }) => (
                    <Fragment key={marker}>
                      <dt className="font-mono text-foreground">{marker}</dt>
                      <dd>{help}</dd>
                    </Fragment>
                  ))}
                </dl>
              </details>
            </div>
          </div>

          <div className="space-y-3">
            <p className="flex items-center gap-1.5 text-sm font-medium">
              <MessageCircle className="size-4" /> Prévia no WhatsApp
            </p>
            <WhatsAppMessage text={preview} />
            <p className="text-xs text-muted-foreground">
              Exemplo: aluna Ana, devendo R$ 150,00 de janeiro e fevereiro.
            </p>
            {!pixKey.trim() && (template ?? '').includes('{pix}') && (
              <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <TriangleAlert className="mt-px size-3.5 shrink-0 text-status-pending" />
                Sem chave Pix, a mensagem sai com o "Pix:" vazio. Preencha a
                chave no bloco Pix.
              </p>
            )}
          </div>
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
          <RotateCcw /> Restaurar texto padrão
        </Button>
        <Button type="submit" className="rounded-full" disabled={isPending}>
          {isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </div>
    </form>
  )
}

function BlockTitle({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="space-y-1">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  )
}
