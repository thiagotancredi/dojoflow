import { ArrowLeft, ArrowRight, Check, Ellipsis, Pencil, Plus, Trash2 } from 'lucide-react'
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
} from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { BeltPicker } from '@/features/belts/components/BeltPicker'
import {
  EligibilityBadge,
  EligibilityHelp,
} from '@/features/belts/components/EligibilityBadge'
import { useGraduationList } from '@/features/belts/hooks'
import { eligibleOn, shortTimeSince, timeLeft } from '@/features/belts/rules'
import { messageFor, showApiError } from '@/lib/api/errors'

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

  const aptCount = data.entries.filter(
    (entry) => entry.eligibility === 'eligible' || entry.eligibility === 'no_requirement',
  ).length

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
        summaryLine={`${data.entries.length} na lista · ${aptCount} ${aptCount === 1 ? 'apto' : 'aptos'}`}
        onRename={(name) => void run(() => updateGraduationList(id, { name }), 'Nome salvo')}
        onExamDate={(exam_date) =>
          void run(() => updateGraduationList(id, { exam_date }), 'Data do exame salva')
        }
        onDelete={() => setConfirmDelete(true)}
      />

      <section className="space-y-3 rounded-3xl bg-card p-4 md:p-5">
        <div>
          <h2 className="font-semibold">Na lista ({data.entries.length})</h2>
          <p className="text-xs text-muted-foreground">
            Cada aluno guarda a faixa que tinha ao entrar: a lista não muda se
            ele graduar depois.
          </p>
        </div>
        {data.entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Adicione alunos abaixo.</p>
        ) : (
          <>
            {/* Computador: tabela */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Aluno</th>
                    <th className="py-2 pr-3 font-medium">
                      <span className="inline-flex items-center gap-1">
                        Faixa → próxima graduação <NextBeltTip />
                      </span>
                    </th>
                    <th className="py-2 pr-3 font-medium">Tempo na faixa</th>
                    <th className="py-2 pr-3 font-medium">
                      <span className="inline-flex items-center gap-1">
                        Situação <SituationTip />
                      </span>
                    </th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.entries.map((entry) => (
                    <tr key={entry.id} className="border-b last:border-0">
                      <td className="py-2.5 pr-3 font-medium">{entry.student_name}</td>
                      <td className="py-2.5 pr-3">
                        <BeltPath
                          entry={entry}
                          busy={busy}
                          onTarget={() => setRetargeting(entry)}
                        />
                      </td>
                      <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                        {timeInBelt(entry.snapshot_graduated_on, examDate)}
                      </td>
                      <td className="py-2.5 pr-3">
                        <EntryBadge entry={entry} examDate={examDate} />
                      </td>
                      <td className="py-2.5 text-right">
                        <EntryMenu
                          entry={entry}
                          busy={busy}
                          onTarget={() => setRetargeting(entry)}
                          onRemove={() => void run(() => removeGraduationEntry(id, entry.id))}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Celular: um cartão por aluno; os "i" ficam numa linha no topo */}
            <div className="space-y-2 md:hidden">
              <Legend />
              <ul className="space-y-2">
                {data.entries.map((entry) => (
                  <li key={entry.id} className="space-y-2 rounded-2xl border bg-popover p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="min-w-0 truncate font-medium">{entry.student_name}</p>
                      <EntryMenu
                        entry={entry}
                        busy={busy}
                        onTarget={() => setRetargeting(entry)}
                        onRemove={() => void run(() => removeGraduationEntry(id, entry.id))}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <BeltPath
                        entry={entry}
                        busy={busy}
                        onTarget={() => setRetargeting(entry)}
                      />
                      <span className="ml-auto text-xs text-muted-foreground">
                        {timeInBelt(entry.snapshot_graduated_on, examDate)}
                      </span>
                    </div>
                    <EntryBadge entry={entry} examDate={examDate} />
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </section>

      <section className="space-y-3 rounded-3xl bg-card p-4 md:p-5">
        <div>
          <h2 className="font-semibold">Adicionar alunos</h2>
          <p className="text-xs text-muted-foreground">
            Alunos ativos de {summary.modality.name} que ainda não estão na
            lista. Dá para adicionar quem não está apto: ele entra como
            "Liberado pelo mestre".
          </p>
        </div>
        {data.candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Todos os alunos ativos já estão na lista.
          </p>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Aluno</th>
                    <th className="py-2 pr-3 font-medium">Faixa</th>
                    <th className="py-2 pr-3 font-medium">Tempo na faixa</th>
                    <th className="py-2 pr-3 font-medium">
                      <span className="inline-flex items-center gap-1">
                        Situação <SituationTip />
                      </span>
                    </th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.candidates.map((candidate) => (
                    <tr key={candidate.enrollment_id} className="border-b last:border-0">
                      <td className="py-2.5 pr-3">{candidate.student_name}</td>
                      <td className="py-2.5 pr-3">
                        <BeltCell belt={candidate.current?.belt ?? null} />
                      </td>
                      <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                        {timeInBelt(candidate.current?.graduated_on ?? null, examDate)}
                      </td>
                      <td className="py-2.5 pr-3">
                        <CandidateBadge candidate={candidate} examDate={examDate} />
                      </td>
                      <td className="py-2.5 text-right">
                        <AddButton busy={busy} onClick={() => addCandidate(candidate)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-2 md:hidden">
              <ul className="space-y-2">
                {data.candidates.map((candidate) => (
                  <li
                    key={candidate.enrollment_id}
                    className="space-y-2 rounded-2xl border border-dashed p-3"
                  >
                    <p className="truncate font-medium">{candidate.student_name}</p>
                    <div className="flex items-center gap-2">
                      <BeltCell belt={candidate.current?.belt ?? null} />
                      <span className="ml-auto text-xs text-muted-foreground">
                        {timeInBelt(candidate.current?.graduated_on ?? null, examDate)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <CandidateBadge candidate={candidate} examDate={examDate} />
                      <AddButton busy={busy} onClick={() => addCandidate(candidate)} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </section>

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
  summaryLine,
  onRename,
  onExamDate,
  onDelete,
}: {
  detail: GraduationListDetail
  busy: boolean
  summaryLine: string
  onRename: (name: string) => void
  onExamDate: (date: string) => void
  onDelete: () => void
}) {
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(summary.name)
  const [examDate, setExamDate] = useState(summary.exam_date)

  return (
    <header className="space-y-2 rounded-3xl bg-card p-4 md:p-5">
      {renaming ? (
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (!name.trim()) return
            onRename(name.trim())
            setRenaming(false)
          }}
        >
          <Input
            aria-label="Nome da lista"
            value={name}
            maxLength={120}
            onChange={(event) => setName(event.target.value)}
            className="min-w-0 flex-1 rounded-xl sm:min-w-64"
          />
          <Button type="submit" className="rounded-full" disabled={busy}>
            Salvar
          </Button>
          <Button
            type="button"
            variant="outline"
            className="rounded-full"
            onClick={() => {
              setName(summary.name)
              setRenaming(false)
            }}
          >
            Cancelar
          </Button>
        </form>
      ) : (
        <div className="flex items-start justify-between gap-2">
          <h1 className="min-w-0 text-xl font-semibold tracking-tight md:text-2xl">
            {summary.name}
          </h1>
          {/* Renomear e Excluir no "⋯", como nos cartões da ficha */}
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                aria-label="Opções da lista"
                className="size-9 shrink-0 rounded-full"
              >
                <Ellipsis />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => setRenaming(true)}>
                <Pencil /> Renomear
              </DropdownMenuItem>
              <DropdownMenuItem variant="destructive" onSelect={onDelete}>
                <Trash2 /> Excluir lista
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span>
          {summary.modality.emoji} {summary.modality.name} · exame em
        </span>
        {/* Mudar a data recalcula "apto" e tempo de todos; escolheu, salvou */}
        <DateField
          aria-label="Data do exame"
          value={examDate}
          onChange={(date) => {
            setExamDate(date)
            if (date !== summary.exam_date) onExamDate(date)
          }}
          className="w-40"
        />
        <span className="text-xs">· {summaryLine}</span>
      </div>
    </header>
  )
}

// Faixa que tinha ao entrar → próxima graduação (clicar troca)
function BeltPath({
  entry,
  busy,
  onTarget,
}: {
  entry: GraduationEntry
  busy: boolean
  onTarget: () => void
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <BeltCell belt={entry.snapshot_belt} />
      <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" />
      <button
        type="button"
        title={`${entry.target_belt.name} (clique para trocar)`}
        aria-label={`Próxima graduação: ${entry.target_belt.name}. Trocar`}
        disabled={busy}
        onClick={onTarget}
        className="rounded-md p-0.5 transition-colors hover:bg-accent"
      >
        <BeltDrawing belt={entry.target_belt} width={90} height={16} className="w-16 md:w-[90px]" />
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
    </InfoTip>
  )
}

// Celular (sem cabeçalho de tabela): os dois "i" numa linha só
function Legend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <LegendItem tip={<SituationTip />}>Situação</LegendItem>
      <LegendItem tip={<NextBeltTip />}>Próxima graduação</LegendItem>
    </div>
  )
}

function LegendItem({ tip, children }: { tip: ReactNode; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1">
      {children}
      {tip}
    </span>
  )
}

// Só o desenho (nome no tooltip), como pede o visual limpo da spec
function BeltCell({ belt }: { belt: Belt | null }) {
  if (!belt) return <span className="text-xs text-muted-foreground">—</span>

  return (
    <span title={belt.name} className="inline-flex">
      <BeltDrawing belt={belt} width={90} height={16} className="w-16 md:w-[90px]" />
    </span>
  )
}
