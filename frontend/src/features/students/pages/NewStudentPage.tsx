import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, Check, Plus } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { setMockCurrentBelt } from '@/features/belts/mock'
import { todayIso } from '@/features/belts/rules'
import { useAcademyModalities } from '@/features/modalities/hooks'
import { AddressFields } from '@/features/students/components/AddressFields'
import { BasicDataFields } from '@/features/students/components/BasicDataFields'
import { ResponsibleFields } from '@/features/students/components/ResponsibleFields'
import { EnrollmentBlock } from '@/features/students/components/wizard/EnrollmentBlock'
import type {
  EnrollmentBlockHandle,
  EnrollmentDraft,
} from '@/features/students/components/wizard/EnrollmentBlock'
import { useCreateStudent } from '@/features/students/hooks'
import { relationshipLabel } from '@/features/students/labels'
import {
  addressSchema,
  basicDataSchema,
  emptyAddress,
  emptyBasicData,
  emptyEnrollment,
  emptyResponsible,
  hasAddress,
  responsibleSchema,
  toAddressPayload,
  toBasicDataPayload,
  toEnrollmentPayload,
  toResponsiblePayload,
} from '@/features/students/schemas'
import type {
  AddressValues,
  BasicDataValues,
  ResponsibleInput,
  ResponsibleValues,
} from '@/features/students/schemas'
import { showApiError } from '@/lib/api/errors'
import { formatPhone } from '@/lib/format'
import { cn } from '@/lib/utils'

const STEPS = ['Dados', 'Endereço', 'Responsáveis', 'Matrículas']

type Block = { key: number; draft: EnrollmentDraft }

const newDraft = (modalityId: string): EnrollmentDraft => ({
  values: emptyEnrollment(modalityId),
  belt: null,
  since: todayIso(),
})

// Cadastro em 4 etapas. Cada etapa tem seu formulário; o que já foi
// preenchido fica guardado aqui, então "Voltar" não perde nada. Tudo é
// enviado junto no fim (recarregar a página no meio perde o cadastro).
export function NewStudentPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [basic, setBasic] = useState<BasicDataValues>(emptyBasicData)
  const [address, setAddress] = useState<AddressValues>(emptyAddress)
  const [who, setWho] = useState<'self' | 'other'>('self')
  const [responsibles, setResponsibles] = useState<ResponsibleValues[]>([])
  const [blocks, setBlocks] = useState<Block[]>([])

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        to="/app/alunos"
        className="mb-2 flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" /> Alunos
      </Link>
      <PageHeader title="Novo aluno" />

      <section className="space-y-5 rounded-3xl bg-card p-5">
        <StepIndicator current={step} />

        {step === 1 && (
          <BasicStep
            initial={basic}
            onCancel={() => navigate('/app/alunos')}
            onNext={(values) => {
              setBasic(values)
              setStep(2)
            }}
          />
        )}
        {step === 2 && (
          <AddressStep
            initial={address}
            onBack={(values) => {
              setAddress(values)
              setStep(1)
            }}
            onNext={(values) => {
              setAddress(values)
              setStep(3)
            }}
          />
        )}
        {step === 3 && (
          <ResponsiblesStep
            who={who}
            responsibles={responsibles}
            onWhoChange={setWho}
            onAdd={(item) => setResponsibles((current) => [...current, item])}
            onRemove={(index) =>
              setResponsibles((current) =>
                current.filter((_, position) => position !== index),
              )
            }
            onBack={() => setStep(2)}
            onNext={() => setStep(4)}
          />
        )}
        {step === 4 && (
          <EnrollmentsStep
            blocks={blocks}
            onBlocksChange={setBlocks}
            onBack={() => setStep(3)}
            buildPayload={(drafts) => ({
              ...toBasicDataPayload(basic),
              address: hasAddress(address) ? toAddressPayload(address) : null,
              responsibles:
                who === 'other' ? responsibles.map(toResponsiblePayload) : [],
              enrollments: drafts.map((draft) => ({
                modality_id: draft.values.modality_id,
                ...toEnrollmentPayload(draft.values),
              })),
            })}
          />
        )}
      </section>

      <p className="mt-3 text-xs text-muted-foreground">
        Recarregar a página no meio do cadastro perde o que foi digitado.
      </p>
    </div>
  )
}

function StepIndicator({ current }: { current: number }) {
  return (
    <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {STEPS.map((label, index) => {
        const number = index + 1
        const done = number < current
        return (
          <li
            key={label}
            aria-current={number === current ? 'step' : undefined}
            className={cn(
              'flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs',
              number === current
                ? 'bg-chip-active font-medium text-chip-active-foreground'
                : done
                  ? 'bg-status-exempt-soft text-status-exempt'
                  : 'bg-muted text-muted-foreground',
            )}
          >
            {done && <Check className="size-3.5" />}
            {number} · {label}
          </li>
        )
      })}
    </ol>
  )
}

function StepNav({
  backLabel = '← Voltar',
  onBack,
  extra,
  next,
}: {
  backLabel?: string
  onBack: () => void
  extra?: ReactNode
  next: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
      <Button
        type="button"
        variant="outline"
        className="rounded-full"
        onClick={onBack}
      >
        {backLabel}
      </Button>
      <div className="flex gap-2">
        {extra}
        {next}
      </div>
    </div>
  )
}

// ---------- 1 · Dados ----------
function BasicStep({
  initial,
  onCancel,
  onNext,
}: {
  initial: BasicDataValues
  onCancel: () => void
  onNext: (values: BasicDataValues) => void
}) {
  const form = useForm<BasicDataValues>({
    resolver: zodResolver(basicDataSchema),
    defaultValues: initial,
  })

  return (
    <form noValidate onSubmit={form.handleSubmit(onNext)} className="space-y-4">
      <BasicDataFields form={form} />
      <StepNav
        backLabel="Cancelar"
        onBack={onCancel}
        next={
          <Button type="submit" className="rounded-full">
            Próximo →
          </Button>
        }
      />
    </form>
  )
}

// ---------- 2 · Endereço (opcional) ----------
function AddressStep({
  initial,
  onBack,
  onNext,
}: {
  initial: AddressValues
  onBack: (values: AddressValues) => void
  onNext: (values: AddressValues) => void
}) {
  const form = useForm<AddressValues>({
    resolver: zodResolver(addressSchema),
    defaultValues: initial,
  })

  return (
    <form noValidate onSubmit={form.handleSubmit(onNext)} className="space-y-4">
      <AddressFields form={form} />
      <StepNav
        onBack={() => onBack(form.getValues())}
        extra={
          <Button
            type="button"
            variant="outline"
            className="rounded-full"
            onClick={() => onNext(emptyAddress)}
          >
            Pular endereço
          </Button>
        }
        next={
          <Button type="submit" className="rounded-full">
            Próximo →
          </Button>
        }
      />
    </form>
  )
}

// ---------- 3 · Responsáveis (como no bot do Telegram) ----------
function ResponsiblesStep({
  who,
  responsibles,
  onWhoChange,
  onAdd,
  onRemove,
  onBack,
  onNext,
}: {
  who: 'self' | 'other'
  responsibles: ResponsibleValues[]
  onWhoChange: (who: 'self' | 'other') => void
  onAdd: (item: ResponsibleValues) => void
  onRemove: (index: number) => void
  onBack: () => void
  onNext: () => void
}) {
  const [missing, setMissing] = useState(false)
  const form = useForm<ResponsibleInput, unknown, ResponsibleValues>({
    resolver: zodResolver(responsibleSchema),
    defaultValues: emptyResponsible,
  })

  const [notAdded, setNotAdded] = useState(false)

  function next() {
    if (who === 'other') {
      // Digitou alguém e não clicou em "Adicionar": não deixa sumir calado
      const typed = form.getValues()
      if (typed.name.trim() || typed.phone.trim()) {
        setNotAdded(true)
        return
      }
      if (responsibles.length === 0) {
        setMissing(true)
        return
      }
    }
    onNext()
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-2" role="radiogroup" aria-label="Responsável">
        <Choice
          selected={who === 'self'}
          onSelect={() => {
            onWhoChange('self')
            setMissing(false)
          }}
          title="O próprio aluno é o responsável"
          description="Aluno adulto: não precisa cadastrar mais ninguém."
        />
        <Choice
          selected={who === 'other'}
          onSelect={() => onWhoChange('other')}
          title="Outra pessoa"
          description="Pai, mãe, avó… (pode adicionar mais de uma)"
        />
      </div>

      {who === 'other' && (
        <div className="space-y-3">
          {responsibles.length > 0 && (
            <ul className="space-y-2">
              {responsibles.map((item, index) => (
                <li
                  key={`${index}-${item.name}`}
                  className="flex items-center justify-between gap-2 rounded-xl border px-3 py-2 text-sm"
                >
                  <span>
                    <span className="font-medium">{item.name}</span>{' '}
                    <span className="text-xs text-muted-foreground">
                      · {relationshipLabel(item.relationship)} ·{' '}
                      {formatPhone(item.phone)}
                    </span>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="rounded-full text-destructive"
                    onClick={() => onRemove(index)}
                  >
                    Remover
                  </Button>
                </li>
              ))}
            </ul>
          )}

          <form
            noValidate
            onSubmit={form.handleSubmit((values) => {
              onAdd(values)
              setMissing(false)
              setNotAdded(false)
              form.reset(emptyResponsible)
            })}
            className="space-y-3 rounded-2xl bg-muted p-4"
          >
            <ResponsibleFields form={form} />
            <Button type="submit" variant="outline" className="rounded-full">
              <Plus /> Adicionar este responsável
            </Button>
          </form>

          {notAdded && (
            <p role="alert" className="text-xs text-destructive">
              Você preencheu um responsável e não adicionou. Clique em
              "Adicionar este responsável" ou apague os campos.
            </p>
          )}
          {missing && (
            <p role="alert" className="text-xs text-destructive">
              Adicione pelo menos um responsável, ou escolha "O próprio aluno".
            </p>
          )}
        </div>
      )}

      <StepNav
        onBack={onBack}
        next={
          <Button type="button" className="rounded-full" onClick={next}>
            Próximo →
          </Button>
        }
      />
    </div>
  )
}

function Choice({
  selected,
  onSelect,
  title,
  description,
}: {
  selected: boolean
  onSelect: () => void
  title: string
  description: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        'flex items-start gap-3 rounded-2xl border p-3 text-left text-sm',
        selected && 'border-chip-active-border bg-chip-active',
      )}
    >
      <span
        className={cn(
          'mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border',
          selected && 'border-primary',
        )}
      >
        {selected && <span className="size-2 rounded-full bg-primary" />}
      </span>
      <span>
        <span className="block font-medium">{title}</span>
        <span className="block text-xs text-muted-foreground">{description}</span>
      </span>
    </button>
  )
}

// ---------- 4 · Matrículas (uma ou mais) ----------
type CreatePayload = Parameters<ReturnType<typeof useCreateStudent>['mutate']>[0]

function EnrollmentsStep({
  blocks,
  onBlocksChange,
  onBack,
  buildPayload,
}: {
  blocks: Block[]
  onBlocksChange: (blocks: Block[]) => void
  onBack: () => void
  buildPayload: (drafts: EnrollmentDraft[]) => CreatePayload
}) {
  const navigate = useNavigate()
  const { offered, isLoading } = useAcademyModalities()
  const { mutate, isPending } = useCreateStudent()
  // Os blocos entregam os dados por aqui (collect/snapshot)
  const handles = useRef(new Map<number, EnrollmentBlockHandle>())
  // Primeira vez na etapa: um bloco com a primeira modalidade oferecida
  const current =
    blocks.length > 0 || offered.length === 0
      ? blocks
      : [{ key: 0, draft: newDraft(offered[0].id) }]
  // Modalidade escolhida em cada bloco (para não repetir nos outros)
  const [chosen, setChosen] = useState<Record<number, string>>({})
  // Contador de chaves: nunca reaproveita a de um bloco removido
  const nextKey = useRef(Math.max(0, ...blocks.map((block) => block.key)) + 1)
  const modalityOf = (block: Block) =>
    chosen[block.key] ?? block.draft.values.modality_id
  const used = current.map(modalityOf)

  function snapshots(): Block[] {
    return current.map((block) => ({
      key: block.key,
      draft: handles.current.get(block.key)?.snapshot() ?? block.draft,
    }))
  }

  function addBlock() {
    const free = offered.find((item) => !used.includes(item.id))
    if (!free) return
    const key = nextKey.current
    nextKey.current += 1
    onBlocksChange([...snapshots(), { key, draft: newDraft(free.id) }])
  }

  function removeBlock(key: number) {
    setChosen((state) => {
      const next = { ...state }
      delete next[key]
      return next
    })
    onBlocksChange(snapshots().filter((block) => block.key !== key))
  }

  async function submit() {
    const drafts: EnrollmentDraft[] = []
    for (const block of current) {
      const draft = await handles.current.get(block.key)?.collect()
      if (!draft) {
        toast.error('Revise os campos das matrículas.')
        return
      }
      drafts.push(draft)
    }

    const modalityIds = drafts.map((draft) => draft.values.modality_id)
    const repeated = modalityIds.findIndex(
      (id, index) => modalityIds.indexOf(id) !== index,
    )
    if (repeated >= 0) {
      toast.error(
        `A matrícula ${repeated + 1} repete uma modalidade. Troque ou remova.`,
      )
      return
    }

    try {
      const student = await mutate(buildPayload(drafts))
      // Faixa atual escolhida em cada matrícula (exemplo, só na tela)
      for (const draft of drafts) {
        setMockCurrentBelt(
          student.id,
          draft.values.modality_id,
          draft.belt ? { belt: draft.belt, graduatedOn: draft.since } : null,
        )
      }
      toast.success('Aluno cadastrado')
      navigate(`/app/alunos/${student.id}`)
    } catch (error) {
      // As regras dos formulários são as mesmas do backend, então um 422
      // (lista de erros por campo) aqui é raro: avisa e deixa revisar
      const isValidation =
        typeof error === 'object' &&
        error !== null &&
        'detail' in error &&
        Array.isArray(error.detail)
      if (isValidation) {
        toast.error('Não foi possível cadastrar. Revise os dados.')
      } else {
        showApiError(error)
      }
    }
  }

  if (!isLoading && offered.length === 0) {
    return (
      <div className="space-y-3">
        <p className="rounded-xl bg-status-pending-soft p-3 text-sm">
          A academia ainda não oferece nenhuma modalidade. Adicione em{' '}
          <Link to="/app/configuracoes" className="font-medium underline">
            Configurações
          </Link>{' '}
          antes de cadastrar alunos.
        </p>
        <StepNav onBack={onBack} next={null} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {current.map((block, index) => (
        <EnrollmentBlock
          key={block.key}
          ref={(handle) => {
            if (handle) handles.current.set(block.key, handle)
            else handles.current.delete(block.key)
          }}
          index={index}
          initial={block.draft}
          modalities={offered
            .filter(
              (item) => item.id === modalityOf(block) || !used.includes(item.id),
            )
            .map((item) => ({ id: item.id, name: item.name }))}
          onModalityChange={(modalityId) =>
            setChosen((state) => ({ ...state, [block.key]: modalityId }))
          }
          onRemove={current.length > 1 ? () => removeBlock(block.key) : undefined}
        />
      ))}

      {offered.some((item) => !used.includes(item.id)) && (
        <Button
          type="button"
          variant="outline"
          className="rounded-full"
          onClick={addBlock}
        >
          <Plus /> Outra modalidade
        </Button>
      )}

      <p className="text-xs text-muted-foreground">
        Tudo é gravado junto ao clicar em Cadastrar. Faixas com valores de
        exemplo nesta etapa.
      </p>

      <StepNav
        onBack={() => {
          onBlocksChange(snapshots())
          onBack()
        }}
        next={
          <Button
            type="button"
            className="rounded-full"
            disabled={isPending || current.length === 0}
            onClick={() => void submit()}
          >
            {isPending ? 'Cadastrando…' : 'Cadastrar aluno'}
          </Button>
        }
      />
    </div>
  )
}
