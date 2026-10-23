import { ArrowLeft, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { DateField } from '@/components/DatePicker'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { useGraduationList } from '@/features/belts/hooks'
import { shortTimeSince } from '@/features/belts/rules'
import { EligibilityDot } from '@/features/graduations/components/EligibilityDot'
import { messageFor, showApiError } from '@/lib/api/errors'

// Detalhe da lista de graduação: quem está nela + quem pode entrar.
// "Apto" e tempo são medidos na data do exame (mudar a data recalcula tudo).
export function GraduationListPage() {
  const { listId } = useParams()
  const navigate = useNavigate()
  const { data, error, refetch, isLoading } = useGraduationList(listId)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [saving, setSaving] = useState(false)
  // Aluno sem próxima faixa (já na última): escolher a pretendida antes
  const [choosingFor, setChoosingFor] = useState<GraduationCandidate | null>(null)
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

  return (
    <div className="space-y-4">
      <Link
        to="/app/graduacoes"
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" /> Graduações
      </Link>

      <ListHeader
        detail={data}
        busy={busy}
        onRename={(name) => void run(() => updateGraduationList(id, { name }), 'Nome salvo')}
        onExamDate={(exam_date) =>
          void run(() => updateGraduationList(id, { exam_date }), 'Data do exame salva')
        }
        onDelete={() => setConfirmDelete(true)}
      />

      <section className="space-y-3 rounded-3xl bg-card p-5">
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
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">Aluno</th>
                  <th className="py-2 pr-3 font-medium">Faixa</th>
                  <th className="py-2 pr-3 font-medium">Tempo</th>
                  <th className="py-2 pr-3 font-medium">Situação</th>
                  <th className="py-2 pr-3 font-medium">Vai para</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry) => (
                  <EntryRow
                    key={entry.id}
                    entry={entry}
                    belts={data.belts}
                    examDate={summary.exam_date}
                    busy={busy}
                    onTarget={(beltId) =>
                      void run(() => updateGraduationEntry(id, entry.id, beltId))
                    }
                    onRemove={() =>
                      void run(() => removeGraduationEntry(id, entry.id))
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="space-y-3 rounded-3xl bg-card p-5">
        <div>
          <h2 className="font-semibold">Adicionar alunos</h2>
          <p className="text-xs text-muted-foreground">
            Alunos ativos de {summary.modality.name}. "Ainda não" é só um aviso:
            dá para adicionar mesmo assim.
          </p>
        </div>
        {data.candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Todos os alunos ativos já estão na lista.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">Aluno</th>
                  <th className="py-2 pr-3 font-medium">Faixa</th>
                  <th className="py-2 pr-3 font-medium">Tempo</th>
                  <th className="py-2 pr-3 font-medium">Situação</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.candidates.map((candidate) => (
                  <tr key={candidate.enrollment_id} className="border-b">
                    <td className="py-2 pr-3">{candidate.student_name}</td>
                    <td className="py-2 pr-3">
                      <BeltCell belt={candidate.current?.belt ?? null} />
                    </td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">
                      {candidate.current
                        ? shortTimeSince(candidate.current.graduated_on, summary.exam_date)
                        : '—'}
                    </td>
                    <td className="py-2 pr-3">
                      <EligibilityDot value={candidate.eligibility} />
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 rounded-full text-xs"
                        disabled={busy}
                        onClick={() =>
                          candidate.suggested_target
                            ? void run(() =>
                                addGraduationEntry(
                                  id,
                                  candidate.enrollment_id,
                                  candidate.suggested_target?.id,
                                ),
                              )
                            : setChoosingFor(candidate)
                        }
                      >
                        <Plus /> Adicionar
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Dialog
        open={choosingFor !== null}
        onOpenChange={(open) => !open && setChoosingFor(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Faixa pretendida · {choosingFor?.student_name}
            </DialogTitle>
          </DialogHeader>
          <p className="text-xs text-muted-foreground">
            {choosingFor?.current
              ? 'O aluno já está na última faixa cadastrada: escolha para qual vai.'
              : 'Escolha a faixa pretendida.'}
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
                void run(() =>
                  addGraduationEntry(id, candidate.enrollment_id, beltId),
                )
              }
            }}
          />
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

function ListHeader({
  detail: { summary },
  busy,
  onRename,
  onExamDate,
  onDelete,
}: {
  detail: GraduationListDetail
  busy: boolean
  onRename: (name: string) => void
  onExamDate: (date: string) => void
  onDelete: () => void
}) {
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(summary.name)
  // A data só é salva ao sair do campo (digitar o ano não grava datas no meio)
  const [examDate, setExamDate] = useState(summary.exam_date)

  return (
    <header className="space-y-2 rounded-3xl bg-card p-5">
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
            className="min-w-64 flex-1 rounded-xl"
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
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{summary.name}</h1>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="rounded-full"
              onClick={() => setRenaming(true)}
            >
              <Pencil /> Renomear
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="rounded-full text-destructive"
              onClick={onDelete}
            >
              <Trash2 /> Excluir
            </Button>
          </div>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span>
          {summary.modality.emoji} {summary.modality.name} · exame em
        </span>
        {/* Mudar a data recalcula "apto" e tempo de todos */}
        {/* O calendário já mostra "23/10/2026"; escolheu, salvou */}
        <DateField
          aria-label="Data do exame"
          value={examDate}
          onChange={(date) => {
            setExamDate(date)
            if (date !== summary.exam_date) onExamDate(date)
          }}
          className="w-40"
        />
      </div>
    </header>
  )
}

function EntryRow({
  entry,
  belts,
  examDate,
  busy,
  onTarget,
  onRemove,
}: {
  entry: GraduationEntry
  belts: Belt[]
  examDate: string
  busy: boolean
  onTarget: (beltId: string) => void
  onRemove: () => void
}) {
  const [choosing, setChoosing] = useState(false)

  return (
    <tr className="border-b">
      <td className="py-2 pr-3">{entry.student_name}</td>
      <td className="py-2 pr-3">
        <BeltCell belt={entry.snapshot_belt} />
      </td>
      <td className="py-2 pr-3 text-xs text-muted-foreground">
        {entry.snapshot_graduated_on
          ? shortTimeSince(entry.snapshot_graduated_on, examDate)
          : '—'}
      </td>
      <td className="py-2 pr-3">
        <EligibilityDot value={entry.eligibility} />
      </td>
      <td className="py-2 pr-3">
        {/* Faixa pretendida: o desenho; clicar abre a escolha */}
        <button
          type="button"
          title={`${entry.target_belt.name} (clique para trocar)`}
          aria-label={`Faixa pretendida: ${entry.target_belt.name}. Trocar`}
          disabled={busy}
          onClick={() => setChoosing(true)}
          className="rounded-md p-0.5 hover:bg-accent"
        >
          <BeltDrawing belt={entry.target_belt} width={90} height={16} />
        </button>
        <Dialog open={choosing} onOpenChange={setChoosing}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Faixa pretendida · {entry.student_name}</DialogTitle>
            </DialogHeader>
            <BeltPicker
              belts={belts}
              value={entry.target_belt.id}
              tags={
                entry.snapshot_belt ? { [entry.snapshot_belt.id]: 'atual' } : {}
              }
              onChange={(beltId) => {
                setChoosing(false)
                if (beltId !== entry.target_belt.id) onTarget(beltId)
              }}
            />
          </DialogContent>
        </Dialog>
      </td>
      <td className="py-2 text-right">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 rounded-full text-xs text-destructive"
          disabled={busy}
          onClick={onRemove}
        >
          Remover
        </Button>
      </td>
    </tr>
  )
}

// Só o desenho (nome no tooltip), como pede o visual limpo da spec
function BeltCell({ belt }: { belt: Belt | null }) {
  if (!belt) return <span className="text-xs text-muted-foreground">—</span>

  return (
    <span title={belt.name} className="inline-flex">
      <BeltDrawing belt={belt} width={90} height={16} />
    </span>
  )
}
