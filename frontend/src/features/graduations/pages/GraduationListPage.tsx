import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Ellipsis,
  MessageCircle,
  Pencil,
  Plus,
  Pointer,
  Trash2,
  Search,
  Star,
} from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { DateField } from '@/components/DatePicker'
import { InfoTip } from '@/components/InfoTip'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  addGraduationEntry,
  deleteGraduationList,
  removeGraduationEntry,
  updateGraduationEntry,
  updateGraduationList,
} from '@/features/belts/api'
import type {
  Belt,
  GraduationCandidate,
  GraduationEntry,
  GraduationListDetail,
  GraduationListUpdate,
} from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { BeltPicker } from '@/features/belts/components/BeltPicker'
import {
  EligibilityBadge,
  EligibilityHelp,
} from '@/features/belts/components/EligibilityBadge'
import { useGraduationList } from '@/features/belts/hooks'
import { eligibleOn, shortTimeSince, timeLeft } from '@/features/belts/rules'
import { PaymentDialog } from '@/features/billing/components/PaymentDialog'
import { WhatsAppDialog } from '@/features/billing/components/WhatsAppButton'
import { openAmount } from '@/features/graduations/charge'
import {
  ChargeActions,
  ChargeCell,
  ChargeShort,
  ChargeStats,
  EntryName,
  Stat,
} from '@/features/graduations/components/GraduationCharge'
import { AddCard } from '@/features/students/components/tabs/TabParts'
import { messageFor, showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { formatMoney } from '@/lib/money'
import { cn } from '@/lib/utils'

// Detalhe da lista de graduação: quem está nela + quem pode entrar.
// "Apto" e tempo são medidos na data do exame (mudar a data recalcula tudo).
// Cada ação grava na hora (não há botão Salvar): o topo avisa isso.
export function GraduationListPage() {
  const { listId } = useParams()
  const navigate = useNavigate()
  const { data, error, refetch, isLoading } = useGraduationList(listId)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [saving, setSaving] = useState(false)
  // Aluno sem próxima faixa (já na última): escolher a pretendida antes
  const [choosingFor, setChoosingFor] = useState<GraduationCandidate | null>(null)
  // Aluno da lista cuja próxima graduação está sendo trocada
  const [retargeting, setRetargeting] = useState<GraduationEntry | null>(null)
  // Travado enquanto salva e até a lista nova chegar
  const busy = saving || isLoading
  // Cobrança da graduação: baixa de um aluno por vez
  const [paying, setPaying] = useState<GraduationEntry | null>(null)
  // Celular: painel do aluno tocado e o WhatsApp aberto a partir dele
  const [detail, setDetail] = useState<GraduationEntry | null>(null)
  const [whatsAppFor, setWhatsAppFor] = useState<GraduationEntry | null>(null)
  // "Adicionar alunos" abre numa janela por cima da lista
  const [adding, setAdding] = useState(false)

  if (!data) {
    return (
      <div className="space-y-3 rounded-3xl bg-card p-8 text-center text-sm">
        {error ? (
          <>
            <p role="alert">{messageFor(error, 'Não foi possível carregar a lista.')}</p>
            <Button asChild variant="outline" className="rounded-full">
              <Link to="/app/graduacoes">Voltar para as listas</Link>
            </Button>
          </>
        ) : (
          <p className="text-muted-foreground">Carregando lista…</p>
        )}
      </div>
    )
  }

  const { summary } = data
  const id = summary.id
  const examDate = summary.exam_date

  // Toda ação: trava os botões, chama a API, recarrega a lista
  async function run(action: () => Promise<unknown>, success?: string) {
    setSaving(true)
    try {
      await action()
      if (success) toast.success(success)
      refetch()
    } catch (caught) {
      showApiError(caught)
    } finally {
      setSaving(false)
    }
  }

  async function removeList() {
    setConfirmDelete(false)
    try {
      await deleteGraduationList(id)
      toast.success('Lista excluída')
      navigate('/app/graduacoes')
    } catch (caught) {
      showApiError(caught)
    }
  }

  function addCandidate(candidate: GraduationCandidate) {
    if (!candidate.suggested_target) {
      setChoosingFor(candidate)
      return
    }
    void run(() =>
      addGraduationEntry(id, candidate.enrollment_id, candidate.suggested_target?.id),
    )
  }

  // Sem data limite a lista não cobra: as colunas de cobrança somem
  const deadline = summary.payment_due_date
  const charging = Boolean(deadline)

  return (
    <div className="space-y-4">
      {/* Voltar como botão de verdade + aviso de que tudo já está salvo */}
      <div className="flex items-center justify-between gap-3">
        <Button asChild variant="outline" className="h-10 rounded-full bg-card px-4">
          <Link to="/app/graduacoes">
            <ArrowLeft /> Graduações
          </Link>
        </Button>
        <SaveStatus saving={busy} />
      </div>

      <ListHeader
        detail={data}
        busy={busy}
        stats={
          <>
            <Stat value={data.entries.length} label="na lista" />
            {deadline && <ChargeStats entries={data.entries} deadline={deadline} />}
          </>
        }
        onSave={(changes) => void run(() => updateGraduationList(id, changes), 'Lista salva')}
        onDelete={() => setConfirmDelete(true)}
      />

      <section className="space-y-3 rounded-3xl bg-card p-4 md:p-5">
        {!charging && data.entries.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Para cobrar a graduação, defina "Pagar até" em Editar.
          </p>
        )}
        {data.entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ninguém na lista ainda.</p>
        ) : (
          <>
            {/* Computador: tabela; o tempo na faixa vai embaixo do nome e o
                valor fica colado nos botões, sem vão no meio */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Aluno</th>
                    <th className="py-2 pr-3 font-medium">
                      <span className="inline-flex items-center gap-1">
                        Faixa → próxima <NextBeltTip />
                      </span>
                    </th>
                    <th className="py-2 pr-3 font-medium">
                      <span className="inline-flex items-center gap-1">
                        Situação <SituationTip />
                      </span>
                    </th>
                    {charging && <th className="py-2 pr-3 font-medium">Graduação</th>}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.entries.map((entry) => (
                    <tr key={entry.id} className="border-b last:border-0">
                      <td className="py-2.5 pr-3">
                        <EntryName entry={entry} />
                        <p className="text-xs text-muted-foreground">
                          {timeInBelt(entry.snapshot_graduated_on, examDate)} na faixa
                        </p>
                      </td>
                      <td className="py-2.5 pr-3">
                        <BeltPath
                          entry={entry}
                          busy={busy}
                          onTarget={() => setRetargeting(entry)}
                        />
                      </td>
                      <td className="py-2.5 pr-3">
                        <EntryBadge entry={entry} examDate={examDate} />
                      </td>
                      {charging && (
                        <td className="py-2.5 pr-3">
                          <ChargeCell entry={entry} />
                        </td>
                      )}
                      <td className="py-2.5">
                        <div className="flex items-center justify-end gap-1.5">
                          {charging && <ChargeActions entry={entry} onPay={setPaying} />}
                          <EntryMenu
                            entry={entry}
                            busy={busy}
                            onTarget={() => setRetargeting(entry)}
                            onRemove={() => void run(() => removeGraduationEntry(id, entry.id))}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Celular: uma linha por aluno (faixas, nome, valor); tocar abre
                o painel com os detalhes e as ações */}
            <div className="md:hidden">
              <p className="flex items-center gap-1.5 border-b pb-2 text-xs text-muted-foreground">
                <Pointer className="size-3.5 shrink-0" />
                Toque no aluno para cobrar, dar baixa ou trocar a faixa.
              </p>
              <ul>
                {data.entries.map((entry) => (
                  <li key={entry.id} className="border-b last:border-0">
                    <button
                      type="button"
                      onClick={() => setDetail(entry)}
                      className="flex w-full items-center gap-3 py-3 text-left"
                    >
                      {/* Faixa de hoje em cima, próxima embaixo */}
                      <span className="flex shrink-0 flex-col gap-1">
                        <BeltCell belt={entry.snapshot_belt} className="w-11" />
                        <BeltDrawing
                          belt={entry.target_belt}
                          width={90}
                          height={16}
                          className="w-11"
                        />
                      </span>
                      <span className="min-w-0 flex-1 truncate font-medium">
                        {entry.student_name}
                        {entry.eligibility === 'not_yet' && (
                          <Star
                            aria-label="Liberado pelo mestre"
                            className="ml-1 inline size-3.5 fill-status-pending align-[-2px] text-status-pending"
                          />
                        )}
                      </span>
                      {charging && <ChargeShort entry={entry} />}
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </section>

      {/* Padrão do sistema: cartão tracejado no fim abre a janela */}
      <AddCard label="Adicionar alunos" onClick={() => setAdding(true)} className="py-5" />
      <AddStudentsDialog
        open={adding}
        onOpenChange={setAdding}
        candidates={data.candidates}
        modalityName={summary.modality.name}
        examDate={examDate}
        busy={busy}
        onAdd={addCandidate}
      />

      {/* Aluno sem próxima faixa automática: escolher antes de adicionar */}
      <Dialog
        open={choosingFor !== null}
        onOpenChange={(open) => !open && setChoosingFor(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Próxima graduação · {choosingFor?.student_name}</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-muted-foreground">
            {choosingFor?.current
              ? 'O aluno já está na última faixa cadastrada: escolha para qual vai.'
              : 'Escolha a faixa que o aluno vai receber.'}
          </p>
          <BeltPicker
            belts={data.belts}
            value={null}
            tags={
              choosingFor?.current ? { [choosingFor.current.belt.id]: 'atual' } : {}
            }
            onChange={(beltId) => {
              const candidate = choosingFor
              setChoosingFor(null)
              if (candidate) {
                void run(() => addGraduationEntry(id, candidate.enrollment_id, beltId))
              }
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Trocar a próxima graduação (inclusive pular faixas) */}
      <Dialog
        open={retargeting !== null}
        onOpenChange={(open) => !open && setRetargeting(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Próxima graduação · {retargeting?.student_name}</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-muted-foreground">
            Já vem marcada a seguinte da sequência; para pular uma faixa,
            escolha outra.
          </p>
          {retargeting && (
            <BeltPicker
              belts={data.belts}
              value={retargeting.target_belt.id}
              tags={
                retargeting.snapshot_belt
                  ? { [retargeting.snapshot_belt.id]: 'atual' }
                  : {}
              }
              onChange={(beltId) => {
                const entry = retargeting
                setRetargeting(null)
                if (beltId !== entry.target_belt.id) {
                  void run(() => updateGraduationEntry(id, entry.id, beltId))
                }
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {detail && (
        <EntrySheet
          entry={detail}
          examDate={examDate}
          charging={charging}
          onClose={() => setDetail(null)}
          onWhatsApp={() => {
            setDetail(null)
            setWhatsAppFor(detail)
          }}
          onPay={() => {
            setDetail(null)
            setPaying(detail)
          }}
          onTarget={() => {
            setDetail(null)
            setRetargeting(detail)
          }}
          onRemove={() => {
            setDetail(null)
            void run(() => removeGraduationEntry(id, detail.id))
          }}
        />
      )}
      {whatsAppFor?.whatsapp_url && (
        <WhatsAppDialog
          url={whatsAppFor.whatsapp_url}
          studentName={whatsAppFor.student_name}
          responsibleName={whatsAppFor.responsible_name}
          open
          onOpenChange={(open) => !open && setWhatsAppFor(null)}
        />
      )}
      {paying && (
        <PaymentDialog
          studentId={paying.student_id}
          studentName={paying.student_name}
          open
          onOpenChange={(open) => !open && setPaying(null)}
          onDone={refetch}
          group="graduation"
          chargeId={paying.charge?.id}
        />
      )}

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={`Excluir a lista "${summary.name}"?`}
        confirmLabel="Excluir"
        onConfirm={() => void removeList()}
      />
    </div>
  )
}

// "✓ Alterações salvas automaticamente" (ou "Salvando…" durante a gravação)
function SaveStatus({ saving }: { saving: boolean }) {
  if (saving) {
    return <span className="text-xs text-muted-foreground">Salvando…</span>
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-status-exempt-soft px-3 py-1 text-xs text-status-exempt">
      <Check className="size-3.5" />
      <span className="hidden sm:inline">Alterações salvas automaticamente</span>
      <span className="sm:hidden">Salvo</span>
    </span>
  )
}

function ListHeader({
  detail: { summary },
  busy,
  stats,
  onSave,
  onDelete,
}: {
  detail: GraduationListDetail
  busy: boolean
  stats: ReactNode
  onSave: (changes: GraduationListUpdate) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const deadline = summary.payment_due_date

  return (
    <header className="space-y-3 rounded-3xl bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">{summary.name}</h1>
          <p className="text-sm text-muted-foreground">
            {summary.modality.emoji} {summary.modality.name}
          </p>
        </div>
        {/* Editar no canto do cartão, como na ficha; Excluir no "⋯" */}
        <div className="flex shrink-0 items-center gap-1">
          <Button
            variant="outline"
            className="h-9 rounded-full px-4"
            disabled={busy}
            onClick={() => setEditing(true)}
          >
            <Pencil /> Editar
          </Button>
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                aria-label="Opções da lista"
                className="size-9 rounded-full"
              >
                <Ellipsis />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem variant="destructive" onSelect={onDelete}>
                <Trash2 /> Excluir lista
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Datas só para ler; mudar é pelo "Editar" */}
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        <DateInfo label="Data do exame">{formatDate(summary.exam_date)}</DateInfo>
        <DateInfo label="Pagar até">
          {deadline ? (
            formatDate(deadline)
          ) : (
            <span className="font-normal text-muted-foreground">Sem data · não cobra</span>
          )}
        </DateInfo>
      </dl>

      {/* Computador: números grandes lado a lado; celular: lista de valores */}
      <div className="flex flex-col divide-y border-t md:flex-row md:divide-x md:divide-y-0 md:pt-3 md:[&>*]:px-6">
        {stats}
      </div>

      {editing && (
        <EditListDialog
          summary={summary}
          busy={busy}
          onClose={() => setEditing(false)}
          onSave={(changes) => {
            setEditing(false)
            onSave(changes)
          }}
        />
      )}
    </header>
  )
}

function DateInfo({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  )
}

// Janela "Editar lista": nome e as duas datas; grava só o que mudou
function EditListDialog({
  summary,
  busy,
  onClose,
  onSave,
}: {
  summary: GraduationListDetail['summary']
  busy: boolean
  onClose: () => void
  onSave: (changes: GraduationListUpdate) => void
}) {
  const [name, setName] = useState(summary.name)
  const [examDate, setExamDate] = useState(summary.exam_date)
  const [deadline, setDeadline] = useState(summary.payment_due_date ?? '')

  function save() {
    const changes: GraduationListUpdate = {}
    if (name.trim() !== summary.name) changes.name = name.trim()
    if (examDate !== summary.exam_date) changes.exam_date = examDate
    if (deadline !== (summary.payment_due_date ?? '')) {
      // Sem data = a lista para de cobrar
      changes.payment_due_date = deadline || null
    }
    if (Object.keys(changes).length === 0) onClose()
    else onSave(changes)
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar lista</DialogTitle>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (name.trim()) save()
          }}
        >
          <EditField label="Nome">
            <Input
              aria-label="Nome da lista"
              value={name}
              maxLength={120}
              onChange={(event) => setName(event.target.value)}
              className="rounded-xl"
            />
          </EditField>
          <EditField label="Data do exame" hint='Mudar recalcula o "apto" e o tempo na faixa.'>
            <DateField aria-label="Data do exame" value={examDate} onChange={setExamDate} />
          </EditField>
          <EditField label="Pagar até" hint="Sem data, a lista não cobra a graduação.">
            <div className="flex items-center gap-2">
              <DateField
                aria-label="Pagar até"
                value={deadline}
                onChange={setDeadline}
                className="flex-1"
              />
              {deadline && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="rounded-full"
                  onClick={() => setDeadline('')}
                >
                  Tirar data
                </Button>
              )}
            </div>
          </EditField>
          <div className="grid grid-cols-2 gap-2">
            <Button type="button" variant="outline" className="h-10 rounded-full" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" className="h-10 rounded-full" disabled={busy || !name.trim()}>
              Salvar
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function EditField({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

// Faixa que tinha ao entrar → próxima graduação (clicar troca)
function BeltPath({
  entry,
  busy,
  onTarget,
  beltClassName = 'w-[84px]',
}: {
  entry: GraduationEntry
  busy: boolean
  onTarget: () => void
  beltClassName?: string
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <BeltCell belt={entry.snapshot_belt} className={beltClassName} />
      <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" />
      <button
        type="button"
        title={`${entry.target_belt.name} (clique para trocar)`}
        aria-label={`Próxima graduação: ${entry.target_belt.name}. Trocar`}
        disabled={busy}
        onClick={onTarget}
        className="rounded-md p-0.5 transition-colors hover:bg-accent"
      >
        <BeltDrawing belt={entry.target_belt} width={90} height={16} className={beltClassName} />
      </button>
    </span>
  )
}

function EntryMenu({
  entry,
  busy,
  onTarget,
  onRemove,
}: {
  entry: GraduationEntry
  busy: boolean
  onTarget: () => void
  onRemove: () => void
}) {
  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Opções de ${entry.student_name}`}
          disabled={busy}
          className="size-8 shrink-0 rounded-full"
        >
          <Ellipsis />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={onTarget}>
          <Pencil /> Trocar próxima graduação
        </DropdownMenuItem>
        <DropdownMenuItem variant="destructive" onSelect={onRemove}>
          <Trash2 /> Remover da lista
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// Celular: painel do aluno (sobe de baixo) com cobrança, faixa e ações
function EntrySheet({
  entry,
  examDate,
  charging,
  onClose,
  onWhatsApp,
  onPay,
  onTarget,
  onRemove,
}: {
  entry: GraduationEntry
  examDate: string
  charging: boolean
  onClose: () => void
  onWhatsApp: () => void
  onPay: () => void
  onTarget: () => void
  onRemove: () => void
}) {
  const charge = entry.charge
  const owes = openAmount(entry) > 0

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent showCloseButton={false}>
        <DialogHeader className="flex-row items-start justify-between gap-3 text-left">
          <div className="min-w-0">
            <DialogTitle className="leading-snug">{entry.student_name}</DialogTitle>
            {charging && (
              <p className="text-xs text-muted-foreground">
                {entry.responsible_name
                  ? `Cobrança vai para ${entry.responsible_name} (responsável)`
                  : 'Cobrança vai para o próprio aluno'}
              </p>
            )}
          </div>
          <Link
            to={`/app/alunos/${entry.student_id}`}
            className="shrink-0 text-xs font-semibold whitespace-nowrap underline"
          >
            Ver ficha ›
          </Link>
        </DialogHeader>

        {charging && (
          <SheetBlock title="Cobrança">
            {!charge ? (
              <p className="text-sm text-muted-foreground">Sem cobrança</p>
            ) : charge.status === 'paid' ? (
              <>
                <SheetRow label="Valor da graduação">{formatMoney(charge.amount)}</SheetRow>
                <SheetRow label="Situação">
                  <span className="font-semibold text-sidebar-primary">
                    ✓ Pago{charge.paid_at ? ` em ${formatDate(charge.paid_at.slice(0, 10))}` : ''}
                  </span>
                </SheetRow>
              </>
            ) : charge.status === 'waived' ? (
              <SheetRow label="Situação">Dispensada</SheetRow>
            ) : (
              <>
                <SheetRow label="Valor da graduação">{formatMoney(charge.amount)}</SheetRow>
                <SheetRow label="Já pago">{formatMoney(charge.paid)}</SheetRow>
                <SheetRow label="Em aberto">
                  <span className="font-semibold text-status-pending">
                    {formatMoney(charge.open_amount)}
                  </span>
                </SheetRow>
                <SheetRow label="Prazo">
                  {formatDate(charge.due_date)} ·{' '}
                  {charge.days_late > 0 ? (
                    <span className="text-status-critical">
                      {charge.days_late} {charge.days_late === 1 ? 'dia' : 'dias'} de atraso
                    </span>
                  ) : (
                    <span className="text-muted-foreground">a vencer</span>
                  )}
                </SheetRow>
              </>
            )}
          </SheetBlock>
        )}

        <SheetBlock title="Faixa">
          <div className="flex items-start gap-3">
            <BeltWithName belt={entry.snapshot_belt} />
            <ArrowRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <BeltWithName belt={entry.target_belt} />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <EntryBadge entry={entry} examDate={examDate} />
            <span className="text-xs text-muted-foreground">
              {timeInBelt(entry.snapshot_graduated_on, examDate)} na faixa
            </span>
          </div>
        </SheetBlock>

        {charging && owes && (
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              className="h-11 rounded-full"
              disabled={!entry.whatsapp_url}
              onClick={onWhatsApp}
            >
              <MessageCircle /> WhatsApp
            </Button>
            <Button className="h-11 rounded-full" onClick={onPay}>
              <Check /> Dar baixa
            </Button>
          </div>
        )}
        <div className="flex justify-around gap-2">
          <Button variant="ghost" size="sm" className="rounded-full" onClick={onTarget}>
            <Pencil /> Trocar próxima faixa
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="rounded-full text-destructive hover:text-destructive"
            onClick={onRemove}
          >
            <Trash2 /> Remover da lista
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function SheetBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border bg-card p-3">
      <p className="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
        {title}
      </p>
      {children}
    </section>
  )
}

function SheetRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  )
}

function BeltWithName({ belt }: { belt: Belt | null }) {
  if (!belt) return <span className="text-xs text-muted-foreground">Sem faixa</span>

  return (
    <span className="flex flex-col items-center gap-1">
      <BeltDrawing belt={belt} width={90} height={16} className="w-16" />
      <span className="text-xs text-muted-foreground">{belt.name}</span>
    </span>
  )
}

// Janela "Adicionar alunos": busca, filtro Aptos/Todos e um botão por aluno.
// Quem entra continua na janela como "✓ Adicionado" até fechar.
function AddStudentsDialog({
  open,
  onOpenChange,
  candidates,
  modalityName,
  examDate,
  busy,
  onAdd,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  candidates: GraduationCandidate[]
  modalityName: string
  examDate: string
  busy: boolean
  onAdd: (candidate: GraduationCandidate) => void
}) {
  const [search, setSearch] = useState('')
  const [onlyApt, setOnlyApt] = useState(true)
  // Clicados nesta abertura: somem dos candidatos quando entram na lista
  const [clicked, setClicked] = useState<GraduationCandidate[]>([])

  // Fechou: a próxima abertura começa do zero
  function changeOpen(next: boolean) {
    if (!next) {
      setSearch('')
      setOnlyApt(true)
      setClicked([])
    }
    onOpenChange(next)
  }

  const waiting = new Set(candidates.map((candidate) => candidate.enrollment_id))
  const added = clicked.filter((candidate) => !waiting.has(candidate.enrollment_id))
  const addedIds = new Set(added.map((candidate) => candidate.enrollment_id))
  const aptTotal = candidates.filter(isApt).length
  // Ninguém apto: mostra todos em vez de uma lista vazia
  const showApt = onlyApt && aptTotal > 0
  const query = plain(search.trim())

  const rows = [...candidates, ...added]
    .filter((candidate) => !showApt || isApt(candidate))
    .filter((candidate) => plain(candidate.student_name).includes(query))
    .sort((left, right) => left.student_name.localeCompare(right.student_name, 'pt-BR'))

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogContent className="md:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Adicionar alunos</DialogTitle>
        </DialogHeader>
        <p className="-mt-2 text-xs text-muted-foreground">
          Alunos ativos de {modalityName} que ainda não estão na lista. Quem
          não está apto entra como "Liberado pelo mestre".
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1.5">
            <FilterButton active={showApt} onClick={() => setOnlyApt(true)}>
              Aptos ({aptTotal})
            </FilterButton>
            <FilterButton active={!showApt} onClick={() => setOnlyApt(false)}>
              Todos ({candidates.length})
            </FilterButton>
          </div>
          <div className="relative min-w-40 flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              aria-label="Buscar aluno"
              placeholder="Buscar aluno"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="rounded-full pl-9"
            />
          </div>
        </div>

        {rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {candidates.length === 0
              ? 'Todos os alunos ativos já estão na lista.'
              : 'Ninguém encontrado.'}
          </p>
        ) : (
          <ul className="max-h-[50dvh] overflow-y-auto">
            {rows.map((candidate) => (
              <li
                key={candidate.enrollment_id}
                className="flex items-center gap-3 border-b py-2.5 last:border-0"
              >
                {/* Faixa de hoje → próxima (a que ele recebe se entrar) */}
                <span className="inline-flex shrink-0 items-center gap-1.5">
                  <BeltCell belt={candidate.current?.belt ?? null} className="w-12 md:w-[72px]" />
                  <ArrowRight className="size-3.5 text-muted-foreground" />
                  {candidate.suggested_target ? (
                    <BeltCell belt={candidate.suggested_target} className="w-12 md:w-[72px]" />
                  ) : (
                    <span
                      title="Já está na última faixa: escolha ao adicionar"
                      className="w-12 text-center text-xs text-muted-foreground md:w-[72px]"
                    >
                      ?
                    </span>
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{candidate.student_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {timeInBelt(candidate.current?.graduated_on ?? null, examDate)} na faixa
                  </p>
                </div>
                <span className="hidden md:inline-flex">
                  <CandidateBadge candidate={candidate} examDate={examDate} />
                </span>
                {addedIds.has(candidate.enrollment_id) ? (
                  <span className="inline-flex items-center gap-1 text-xs font-semibold whitespace-nowrap text-sidebar-primary">
                    <Check className="size-3.5" /> Adicionado
                  </span>
                ) : (
                  <AddButton
                    busy={busy}
                    onClick={() => {
                      setClicked((current) => [...current, candidate])
                      onAdd(candidate)
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        )}

        <Button className="rounded-full md:justify-self-end md:px-6" onClick={() => changeOpen(false)}>
          Concluir
        </Button>
      </DialogContent>
    </Dialog>
  )
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'shrink-0 rounded-full border px-3 py-1 text-xs',
        active
          ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
          : 'text-muted-foreground',
      )}
    >
      {children}
    </button>
  )
}

function isApt(candidate: GraduationCandidate) {
  return candidate.eligibility === 'eligible' || candidate.eligibility === 'no_requirement'
}

// "Júlia" e "julia" batem na busca
function plain(text: string) {
  return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
}

function AddButton({ busy, onClick }: { busy: boolean; onClick: () => void }) {
  return (
    <Button
      variant="outline"
      size="sm"
      className="h-8 rounded-full text-xs"
      disabled={busy}
      onClick={onClick}
    >
      <Plus /> Adicionar
    </Button>
  )
}

// Quem está na lista sem estar apto entrou por decisão do mestre
function EntryBadge({ entry, examDate }: { entry: GraduationEntry; examDate: string }) {
  return (
    <EligibilityBadge
      value={entry.eligibility}
      master
      left={leftUntilApt(entry.snapshot_belt, entry.snapshot_graduated_on, examDate)}
    />
  )
}

function CandidateBadge({
  candidate,
  examDate,
}: {
  candidate: GraduationCandidate
  examDate: string
}) {
  return (
    <EligibilityBadge
      value={candidate.eligibility}
      left={leftUntilApt(
        candidate.current?.belt ?? null,
        candidate.current?.graduated_on ?? null,
        examDate,
      )}
    />
  )
}

// Quanto falta, na data do exame, para cumprir o tempo mínimo da faixa
function leftUntilApt(belt: Belt | null, graduatedOn: string | null, examDate: string) {
  if (!belt || !graduatedOn) return null
  return timeLeft(
    eligibleOn(graduatedOn, belt.min_time_amount, belt.min_time_unit),
    examDate,
  )
}

function timeInBelt(graduatedOn: string | null, examDate: string) {
  return graduatedOn ? shortTimeSince(graduatedOn, examDate) : '—'
}

function SituationTip() {
  return (
    <InfoTip label="O que significa cada situação">
      <EligibilityHelp />
    </InfoTip>
  )
}

function NextBeltTip() {
  return (
    <InfoTip label="Sobre a próxima graduação">
      <p className="font-semibold">Próxima graduação</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        É a faixa que o aluno recebe no exame. Já vem marcada a seguinte da
        sequência; para pular uma faixa, clique nela e escolha outra.
      </p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        Cada aluno guarda a faixa que tinha ao entrar: a lista não muda se ele
        graduar depois.
      </p>
    </InfoTip>
  )
}

// Só o desenho (nome no tooltip), como pede o visual limpo da spec
function BeltCell({
  belt,
  className = 'w-16 md:w-[90px]',
}: {
  belt: Belt | null
  className?: string
}) {
  if (!belt) return <span className="text-xs text-muted-foreground">—</span>

  return (
    <span title={belt.name} className="inline-flex">
      <BeltDrawing belt={belt} width={90} height={16} className={className} />
    </span>
  )
}
