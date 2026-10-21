import { Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  addEnrollmentBelt,
  deleteEnrollmentBelt,
  updateEnrollmentBelt,
} from '@/features/belts/api'
import type {
  Belt,
  BeltRecord,
  EnrollmentBeltPayload,
  EnrollmentBelts,
} from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { BeltPicker } from '@/features/belts/components/BeltPicker'
import { useBelts, useEnrollmentBelts } from '@/features/belts/hooks'
import { nextBeltId, timeSince, todayIso } from '@/features/belts/rules'
import { showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { useMutation } from '@/lib/hooks/useMutation'

type EnrollmentBeltBlockProps = {
  studentId: string
  enrollmentId: string
  modalityId: string
  modalityName: string
}

// Bloco de faixa dentro do card de matrícula: faixa atual, tempo, aptidão,
// registrar graduação e histórico (com editar e excluir)
export function EnrollmentBeltBlock({
  studentId,
  enrollmentId,
  modalityId,
  modalityName,
}: EnrollmentBeltBlockProps) {
  const belts = useBelts(modalityId)
  const state = useEnrollmentBelts(studentId, enrollmentId)
  // 'register' = nova graduação · BeltRecord = editando um registro
  const [form, setForm] = useState<'register' | BeltRecord | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [toDelete, setToDelete] = useState<BeltRecord | null>(null)

  const save = useMutation((payload: EnrollmentBeltPayload) =>
    form && form !== 'register'
      ? updateEnrollmentBelt(studentId, enrollmentId, form.id, payload)
      : addEnrollmentBelt(studentId, enrollmentId, payload),
  )

  // Modalidade sem faixas (ex.: Boxe): nada aparece
  const beltList = belts.data ?? []
  if (beltList.length === 0) return null

  const data = state.data
  const current = data?.current ?? null

  async function submit(payload: EnrollmentBeltPayload) {
    try {
      await save.mutate(payload)
      toast.success(form === 'register' ? 'Graduação registrada' : 'Registro salvo')
      setForm(null)
      state.refetch()
    } catch (error) {
      showApiError(error)
    }
  }

  async function confirmDelete() {
    if (!toDelete) return
    const record = toDelete
    setToDelete(null)
    try {
      await deleteEnrollmentBelt(studentId, enrollmentId, record.id)
      toast.success('Registro excluído')
      state.refetch()
    } catch (error) {
      showApiError(error)
    }
  }

  return (
    <div className="mt-2 space-y-1.5 rounded-lg bg-card p-2.5">
      {!data ? (
        <p className="text-xs text-muted-foreground">
          {state.error ? 'Não foi possível carregar a faixa.' : 'Carregando faixa…'}
        </p>
      ) : current ? (
        <>
          <BeltDrawing belt={current.belt} width={200} height={26} />
          <p>
            <span className="font-medium">{current.belt.name}</span>{' '}
            <span className="text-xs text-muted-foreground">
              · {timeSince(current.graduated_on)}
            </span>
          </p>
          <EligibilityLine data={data} />
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            <Button
              size="sm"
              className="h-7 rounded-full text-xs"
              onClick={() => setForm('register')}
            >
              Registrar graduação
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 rounded-full text-xs"
              onClick={() => setShowHistory(true)}
            >
              Histórico ({data.history.length})
            </Button>
          </div>
        </>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">Sem faixa registrada</p>
          <Button
            size="sm"
            variant="outline"
            className="h-7 rounded-full text-xs"
            onClick={() => setForm('register')}
          >
            Registrar faixa atual
          </Button>
        </>
      )}

      <Dialog open={form !== null} onOpenChange={(open) => !open && setForm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {form && form !== 'register'
                ? 'Editar registro'
                : current
                  ? 'Registrar graduação'
                  : 'Registrar faixa atual'}{' '}
              · {modalityName}
            </DialogTitle>
          </DialogHeader>
          {form !== null && (
            <GraduationForm
              belts={beltList}
              current={current?.belt.id ?? null}
              record={form === 'register' ? null : form}
              isPending={save.isPending}
              onSave={(payload) => void submit(payload)}
              onCancel={() => setForm(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={showHistory} onOpenChange={setShowHistory}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Histórico de faixas · {modalityName}</DialogTitle>
          </DialogHeader>
          <ul className="space-y-2">
            {(data?.history ?? []).map((record) => (
              <li
                key={record.id}
                className="flex items-center justify-between gap-2 rounded-xl border px-3 py-2 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <BeltDrawing belt={record.belt} width={100} height={16} />
                  <span className="truncate">{record.belt.name}</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-xs text-muted-foreground">
                    {formatDate(record.graduated_on)}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Editar registro"
                    onClick={() => {
                      setShowHistory(false)
                      setForm(record)
                    }}
                  >
                    <Pencil />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Excluir registro"
                    className="text-destructive"
                    onClick={() => setToDelete(record)}
                  >
                    <Trash2 />
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title="Excluir este registro do histórico?"
        confirmLabel="Excluir"
        onConfirm={() => void confirmDelete()}
      />
    </div>
  )
}

// Aptidão calculada pela API (com a data de hoje)
function EligibilityLine({ data }: { data: EnrollmentBelts }) {
  if (data.eligibility === 'eligible') {
    return (
      <p className="flex items-center gap-1.5 text-xs">
        <span className="size-2 rounded-full bg-status-exempt" />
        <span className="text-status-exempt">Apto</span>
      </p>
    )
  }

  if (data.eligibility === 'not_yet' && data.eligible_on) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="size-2 rounded-full bg-status-pending" />
        Ainda não · apto a partir de {formatDate(data.eligible_on)}
      </p>
    )
  }

  return <p className="text-xs text-muted-foreground">Sem tempo mínimo</p>
}

type GraduationFormProps = {
  belts: Belt[]
  current: string | null
  // Registro sendo editado (null = nova graduação)
  record: BeltRecord | null
  isPending: boolean
  onSave: (payload: EnrollmentBeltPayload) => void
  onCancel: () => void
}

function GraduationForm({
  belts,
  current,
  record,
  isPending,
  onSave,
  onCancel,
}: GraduationFormProps) {
  const suggested = record ? record.belt.id : nextBeltId(belts, current)
  const [beltId, setBeltId] = useState<string | null>(suggested)
  const [graduatedOn, setGraduatedOn] = useState(
    record?.graduated_on ?? todayIso(),
  )

  const tags: Record<string, string> = {}
  if (current) tags[current] = 'atual'
  if (!record && suggested && suggested !== current) tags[suggested] = 'próxima'

  return (
    <div className="space-y-4">
      <BeltPicker belts={belts} value={beltId} onChange={setBeltId} tags={tags} />
      <div className="space-y-1.5">
        <Label htmlFor="graduated_on" className="text-xs text-muted-foreground">
          Data da graduação
        </Label>
        <Input
          id="graduated_on"
          type="date"
          value={graduatedOn}
          onChange={(event) => setGraduatedOn(event.target.value)}
          className="rounded-xl"
        />
      </div>
      {!record && (
        <p className="text-xs text-muted-foreground">
          {current
            ? 'A próxima faixa já vem marcada; dá para escolher outra (inclusive pular).'
            : 'Aluno antigo: escolha a faixa atual e uma data aproximada.'}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="outline" className="rounded-full" onClick={onCancel}>
          Cancelar
        </Button>
        <Button
          className="rounded-full"
          disabled={!beltId || !graduatedOn || isPending}
          onClick={() =>
            beltId && onSave({ belt_id: beltId, graduated_on: graduatedOn })
          }
        >
          {isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </div>
    </div>
  )
}
