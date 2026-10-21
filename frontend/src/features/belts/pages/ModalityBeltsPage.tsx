import { ArrowDown, ArrowLeft, ArrowUp, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  applyBeltPreset,
  createBelt,
  deleteBelt,
  reorderBelts,
  updateBelt,
} from '@/features/belts/api'
import type { Belt, BeltPayload } from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { BeltForm } from '@/features/belts/components/BeltForm'
import { useBelts } from '@/features/belts/hooks'
import { minTimeLabel } from '@/features/belts/rules'
import { useAcademyModalities } from '@/features/modalities/hooks'
import { isValidationError, showApiError } from '@/lib/api/errors'
import { useMutation } from '@/lib/hooks/useMutation'

// Modalidades com sequência padrão no backend (services/belt_presets.py)
const PRESET_MODALITIES = new Set(['taekwondo', 'kickboxing'])

// Configurações → Modalidades → Faixas (tela 1 da spec das faixas)
export function ModalityBeltsPage() {
  const { modalityId = '' } = useParams()
  const { offered, refetch: refetchModalities } = useAcademyModalities()
  const modality = offered.find((item) => item.id === modalityId)
  const belts = useBelts(modalityId)
  const list = belts.data ?? []

  // null = fechado · 'new' = nova faixa · Belt = editando
  const [editing, setEditing] = useState<Belt | 'new' | null>(null)
  const [toDelete, setToDelete] = useState<Belt | null>(null)

  const save = useMutation((payload: BeltPayload) =>
    editing && editing !== 'new'
      ? updateBelt(editing.id, payload)
      : createBelt(modalityId, payload),
  )
  const reorder = useMutation((ids: string[]) => reorderBelts(modalityId, ids))
  const preset = useMutation(() => applyBeltPreset(modalityId))

  function refresh() {
    belts.refetch()
    refetchModalities()
  }

  async function submitBelt(payload: BeltPayload) {
    try {
      await save.mutate(payload)
      toast.success(editing === 'new' ? 'Faixa criada' : 'Faixa salva')
      setEditing(null)
      refresh()
    } catch (error) {
      // Nome repetido etc. → texto pelo código; 422 (raro: o formulário
      // valida as mesmas regras) → pede para revisar
      if (isValidationError(error)) toast.error('Revise os campos da faixa.')
      else showApiError(error)
    }
  }

  async function move(index: number, direction: -1 | 1) {
    const ids = list.map((belt) => belt.id)
    ;[ids[index], ids[index + direction]] = [ids[index + direction], ids[index]]
    try {
      await reorder.mutate(ids)
      belts.refetch()
    } catch (error) {
      showApiError(error)
      belts.refetch()
    }
  }

  async function confirmDelete() {
    if (!toDelete) return
    const belt = toDelete
    setToDelete(null)
    try {
      await deleteBelt(belt.id)
      toast.success('Faixa excluída')
      refresh()
    } catch (error) {
      showApiError(error)
    }
  }

  async function runPreset() {
    try {
      const created = await preset.mutate()
      toast.success(
        `Sequência do ${modality?.name} criada (${created.length} faixas)`,
      )
      refresh()
    } catch (error) {
      showApiError(error)
    }
  }

  // Trava até salvar E a lista nova chegar (o próximo movimento parte dela)
  const reordering = reorder.isPending || belts.isLoading
  const pending = modality?.pending_belt_count ?? 0
  const hasPreset = PRESET_MODALITIES.has(
    modality?.name.trim().toLowerCase() ?? '',
  )

  return (
    <div className="space-y-4">
      <Link
        to="/app/configuracoes"
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" /> Configurações
      </Link>
      <PageHeader
        title={`Faixas${modality ? ` · ${modality.name}` : ''}`}
        actions={
          list.length > 0 && (
            <Button className="rounded-full" onClick={() => setEditing('new')}>
              <Plus /> Nova faixa
            </Button>
          )
        }
      />

      {list.length > 0 && pending > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-status-pending-soft px-4 py-3 text-sm">
          <span>
            <b>
              {pending} {pending === 1 ? 'aluno' : 'alunos'}
            </b>{' '}
            de {modality?.name} {pending === 1 ? 'está' : 'estão'} sem faixa
            registrada.
          </span>
          <Button asChild size="sm" variant="outline" className="rounded-full">
            <Link to="lancar">Lançar faixas de todos</Link>
          </Button>
        </div>
      )}

      <section className="rounded-3xl bg-card p-5">
        {belts.error ? (
          <div className="space-y-3 text-center text-sm">
            <p role="alert" className="text-destructive">
              Não foi possível carregar as faixas.
            </p>
            <Button variant="outline" className="rounded-full" onClick={belts.refetch}>
              Tentar de novo
            </Button>
          </div>
        ) : !belts.data ? (
          <p className="text-sm text-muted-foreground">Carregando faixas…</p>
        ) : list.length === 0 ? (
          <div className="grid justify-items-center gap-3 rounded-2xl border border-dashed p-8 text-center">
            <p className="font-medium">Nenhuma faixa cadastrada</p>
            <p className="max-w-md text-sm text-muted-foreground">
              Cadastre da menor para a maior. Graus e dans são faixas próprias
              (ex.: Preta 1º Dan).
            </p>
            {hasPreset && (
              <>
                <Button
                  className="rounded-full"
                  disabled={preset.isPending}
                  onClick={() => void runPreset()}
                >
                  {preset.isPending
                    ? 'Criando…'
                    : `Usar a sequência padrão do ${modality?.name}`}
                </Button>
                <p className="text-xs text-muted-foreground">
                  Cria as faixas da Branca até a Preta 9º Dan. Tudo editável
                  depois.
                </p>
              </>
            )}
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => setEditing('new')}
            >
              <Plus /> Cadastrar faixa por faixa
            </Button>
          </div>
        ) : (
          <ol className="divide-y">
            {list.map((belt, index) => (
              <li key={belt.id} className="flex items-center gap-3 py-2.5">
                <span className="w-6 text-right text-xs text-muted-foreground">
                  {belt.position}
                </span>
                <BeltDrawing belt={belt} width={150} height={24} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {belt.name}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {minTimeLabel(belt.min_time_amount, belt.min_time_unit)}
                  </span>
                </span>
                {/* Um movimento por vez: os botões travam até salvar */}
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Subir ${belt.name}`}
                  disabled={index === 0 || reordering}
                  onClick={() => void move(index, -1)}
                >
                  <ArrowUp />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Descer ${belt.name}`}
                  disabled={index === list.length - 1 || reordering}
                  onClick={() => void move(index, 1)}
                >
                  <ArrowDown />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Editar ${belt.name}`}
                  onClick={() => setEditing(belt)}
                >
                  <Pencil />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Excluir ${belt.name}`}
                  className="text-destructive"
                  onClick={() => setToDelete(belt)}
                >
                  <Trash2 />
                </Button>
              </li>
            ))}
          </ol>
        )}
      </section>

      <Dialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
      >
        <DialogContent className="max-h-[90dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editing === 'new' ? 'Nova faixa' : 'Editar faixa'}
            </DialogTitle>
          </DialogHeader>
          {editing !== null && (
            <BeltForm
              belt={editing === 'new' ? null : editing}
              isPending={save.isPending}
              onSubmit={(payload) => void submitBelt(payload)}
              onCancel={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title={`Excluir a faixa ${toDelete?.name ?? ''}?`}
        description="Faixas que já aparecem no histórico de algum aluno ou numa lista de graduação não podem ser excluídas."
        confirmLabel="Excluir"
        onConfirm={() => void confirmDelete()}
      />
    </div>
  )
}
