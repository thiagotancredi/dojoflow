import { Pencil, RotateCcw, TriangleAlert } from 'lucide-react'
import { Fragment, useRef } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'

import { FormField } from '@/components/FormField'
import { InfoTip } from '@/components/InfoTip'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/features/auth/useAuth'
import type { BillingSettings } from '@/features/billing/api'
import { WhatsAppPhone } from '@/features/billing/components/WhatsAppPhone'
import { useBillingSettings, useSaveBillingSettings } from '@/features/billing/hooks'
import { fillTemplate } from '@/features/billing/whatsapp'
import { InfinitePayInvite } from '@/features/settings/components/InfinitePayInvite'
import { showApiError } from '@/lib/api/errors'

// Mesmo texto de DEFAULT_MESSAGE_TEMPLATE (backend, services/billing.py).
// Salvar exatamente este texto faz a academia seguir o padrão.
const DEFAULT_MESSAGE_TEMPLATE =
  'Olá, {nome}! Tudo bem?\n\n' +
  'Passando para lembrar que há uma mensalidade em aberto: {valor}.\n\n' +
  'Para pagar pelo Pix, é só tocar aqui:\n{link}\n\n' +
  'Se já pagou, desconsidere. Obrigado!\n\n' +
  '*{mestre}*\n{academia}'

// Marcadores trocados pelos dados de cada aluno ao abrir o WhatsApp
const MARKERS = [
  { marker: '{nome}', help: 'primeiro nome de quem recebe' },
  { marker: '{mestre}', help: 'seu nome (assina a mensagem)' },
  { marker: '{academia}', help: 'nome da academia' },
  { marker: '{valor}', help: 'total em atraso' },
  { marker: '{meses}', help: 'meses em atraso' },
  { marker: '{link}', help: 'link da página de pagamento' },
  { marker: '{pix}', help: 'chave Pix' },
  { marker: '{recebedor}', help: 'nome de quem recebe' },
]

// Tipos de chave Pix (o formato da chave depende dele)
const PIX_KEY_TYPES = [
  { value: 'cpf', label: 'CPF' },
  { value: 'cnpj', label: 'CNPJ' },
  { value: 'phone', label: 'Celular' },
  { value: 'email', label: 'E-mail' },
  { value: 'random', label: 'Chave aleatória' },
] as const

type PixKeyType = (typeof PIX_KEY_TYPES)[number]['value']

type FormValues = {
  pix_key: string
  // '' = ainda não escolhido
  pix_key_type: PixKeyType | ''
  pix_city: string
  recipient_name: string
  message_template: string
}

function toForm(settings: BillingSettings): FormValues {
  return {
    pix_key: settings.pix_key ?? '',
    pix_key_type: settings.pix_key_type ?? '',
    pix_city: settings.pix_city ?? '',
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
      <InfinitePayInvite />
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
  const master = useAuth().master
  const academyName = master?.academy.name ?? ''
  // Prévia: o texto como chega no WhatsApp, com um aluno de exemplo
  const [template, pixKey, recipientName, pixKeyType, pixCity] = useWatch({
    control: form.control,
    name: [
      'message_template',
      'pix_key',
      'recipient_name',
      'pix_key_type',
      'pix_city',
    ],
  })
  const preview = fillTemplate(template || DEFAULT_MESSAGE_TEMPLATE, {
    nome: 'Ana',
    mestre: master?.name ?? '',
    academia: academyName,
    valor: 'R$ 150,00',
    meses: 'janeiro e fevereiro',
    // Igual ao backend: sem Pix fica vazio; sem recebedor, a academia
    pix: pixKey.trim(),
    recebedor: recipientName.trim() || academyName,
    link: `${window.location.origin}/pagar/exemplo`,
  })
  // Sem tipo ou cidade não dá para montar o código Pix da página de pagamento
  const pixIncomplete =
    pixKey.trim() !== '' && (pixKeyType === '' || pixCity.trim() === '')
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
        pix_key_type: values.pix_key_type || null,
        pix_city: values.pix_city,
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
          description="Usados para montar o código Pix que o aluno copia na página de pagamento."
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Tipo da chave"
            htmlFor="billing-pix-type"
            error={errors.pix_key_type?.message}
          >
            <Controller
              control={form.control}
              name="pix_key_type"
              rules={{
                validate: (value) =>
                  value !== '' ||
                  getValues('pix_key').trim() === '' ||
                  'Escolha o tipo da chave.',
              }}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger
                    id="billing-pix-type"
                    className="w-full rounded-xl"
                  >
                    <SelectValue placeholder="Escolha o tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {PIX_KEY_TYPES.map(({ value, label }) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </FormField>
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
          <FormField label="Cidade" htmlFor="billing-city">
            <Input
              id="billing-city"
              placeholder="cidade de quem recebe"
              maxLength={60}
              className="rounded-xl"
              {...register('pix_city')}
            />
          </FormField>
        </div>
        {pixIncomplete && (
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
            <TriangleAlert className="mt-px size-3.5 shrink-0 text-status-pending" />
            Sem tipo da chave e cidade, o aluno não consegue copiar o código
            Pix na página de pagamento.
          </p>
        )}
      </div>

      <Separator />

      {/* Bloco 2: o texto (esquerda) e como ele chega (direita) */}
      <div className="space-y-4">
        <BlockTitle
          title="Mensagem de cobrança"
          description="O texto que abre no WhatsApp quando você cobra um aluno."
        />
        {/* Texto à esquerda; à direita, um celular com a conversa como o
            aluno vai ver, centralizado na altura do texto. Largura limitada
            (40rem): numa tela grande o campo não estica até a borda e o
            celular fica junto dele. No celular, um embaixo do outro */}
        <div className="grid gap-6 lg:grid-cols-[minmax(0,40rem)_18rem] lg:items-center lg:gap-10">
          <div className="space-y-2">
            <Label
              htmlFor="billing-message"
              className="flex items-center gap-1.5 text-sm font-medium"
            >
              <Pencil className="size-4" /> Texto da mensagem
            </Label>
            {/* Campo com a barra de marcadores no topo */}
            <div className="overflow-hidden rounded-xl border border-input bg-background focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
              <div className="flex flex-wrap items-center gap-1.5 border-b bg-muted/50 px-3 py-2">
                <span className="text-xs text-muted-foreground">Inserir:</span>
                {MARKERS.map(({ marker, help }) => (
                  <button
                    key={marker}
                    type="button"
                    title={help}
                    onClick={() => insertMarker(marker)}
                    className="rounded-full border bg-background px-2.5 py-0.5 font-mono text-xs hover:bg-accent"
                  >
                    {marker}
                  </button>
                ))}
                <span className="ml-auto">
                  <InfoTip label="O que cada marcador significa">
                    <p className="font-semibold">Marcadores</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Na hora de cobrar, cada um vira o dado do aluno. Tocar
                      num marcador coloca ele onde está o cursor.
                    </p>
                    <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                      {MARKERS.map(({ marker, help }) => (
                        <Fragment key={marker}>
                          <dt className="font-mono">{marker}</dt>
                          <dd className="text-muted-foreground">{help}</dd>
                        </Fragment>
                      ))}
                    </dl>
                    <p className="mt-2 text-xs text-muted-foreground">
                      *Entre asteriscos* sai em negrito no WhatsApp.
                    </p>
                  </InfoTip>
                </span>
              </div>
              <Textarea
                id="billing-message"
                maxLength={1000}
                // field-sizing-content: o campo cresce com o texto, sem
                // esconder as últimas linhas (a assinatura) atrás de rolagem
                className="field-sizing-content min-h-64 rounded-none border-0 bg-transparent focus-visible:ring-0 dark:bg-transparent"
                {...messageField}
                ref={(element) => {
                  registerMessageRef(element)
                  messageRef.current = element
                }}
              />
            </div>
            {errors.message_template && (
              <p role="alert" className="text-xs text-destructive">
                {errors.message_template.message}
              </p>
            )}
            {!pixKey.trim() && (template ?? '').includes('{pix}') && (
              <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <TriangleAlert className="mt-px size-3.5 shrink-0 text-status-pending" />
                Sem chave Pix, a mensagem sai com o "Pix:" vazio. Preencha a
                chave no bloco Pix.
              </p>
            )}
          </div>

          <WhatsAppPhone contact="Ana" text={preview} />
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
