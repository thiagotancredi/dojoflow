import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toast } from 'sonner'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { registerBeltsInBulk } from '@/features/belts/api'
import type { BulkBeltItem } from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { useBelts, usePendingEnrollments } from '@/features/belts/hooks'
import { useAcademyModalities } from '@/features/modalities/hooks'
import { showApiError } from '@/lib/api/errors'
import { useMutation } from '@/lib/hooks/useMutation'

type Row = { beltId: string; graduatedOn: string }

// Lançar faixas dos alunos antigos de uma vez (tela 2b da spec)
export function BulkBeltsPage() {
  const { modalityId = '' } = useParams()
  const { offered } = useAcademyModalities()
  const modality = offered.find((item) => item.id === modalityId)
  const belts = useBelts(modalityId)
  const pending = usePendingEnrollments(modalityId)
  const [rows, setRows] = useState<Record<string, Row>>({})
  const save = useMutation((items: BulkBeltItem[]) =>
    registerBeltsInBulk(modalityId, items),
  )

  function update(enrollmentId: string, change: Partial<Row>) {
    setRows((current) => ({
      ...current,
      [enrollmentId]: {
        ...(current[enrollmentId] ?? { beltId: '', graduatedOn: '' }),
        ...change,
      },
    }))
  }

  // Só vão as linhas com faixa e data; as outras continuam pendentes
  const items: BulkBeltItem[] = Object.entries(rows)
    .filter(([, row]) => row.beltId && row.graduatedOn)
    .map(([enrollmentId, row]) => ({
      enrollment_id: enrollmentId,
      belt_id: row.beltId,
      graduated_on: row.graduatedOn,
    }))

  async function submit() {
    try {
      const result = await save.mutate(items)
      toast.success(
        `${result.saved} ${result.saved === 1 ? 'faixa lançada' : 'faixas lançadas'}`,
      )
      setRows({})
      pending.refetch()
    } catch (error) {
      // Tudo ou nada: se uma linha falha, nenhuma é gravada
      showApiError(error)
    }
  }

  const list = pending.data ?? []
  const beltList = belts.data ?? []

  return (
    <div className="space-y-4">
      <Link
        to=".."
        relative="path"
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" /> Faixas{modality ? ` · ${modality.name}` : ''}
      </Link>
      <PageHeader
        title={`Lançar faixas${modality ? ` · ${modality.name}` : ''}`}
      />

      <section className="space-y-4 rounded-3xl bg-card p-5">
        {pending.error || belts.error ? (
          <div className="space-y-3 text-center text-sm">
            <p role="alert" className="text-destructive">
              Não foi possível carregar os alunos.
            </p>
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => {
                pending.refetch()
                belts.refetch()
              }}
            >
              Tentar de novo
            </Button>
          </div>
        ) : !pending.data || !belts.data ? (
          <p className="text-sm text-muted-foreground">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="py-6 text-center text-sm font-medium">
            Todos os alunos ativos desta modalidade já têm faixa registrada.
          </p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              {list.length} {list.length === 1 ? 'aluno ativo' : 'alunos ativos'}{' '}
              sem faixa registrada. Preencha só os que souber; os outros
              continuam pendentes. A data pode ser aproximada.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Aluno</th>
                    <th className="py-2 pr-3 font-medium">Faixa atual</th>
                    <th className="py-2 font-medium">Desde</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((item) => {
                    const row = rows[item.enrollment_id]
                    return (
                      <tr key={item.enrollment_id} className="border-b">
                        <td className="py-2 pr-3">{item.student_name}</td>
                        <td className="py-2 pr-3">
                          <Select
                            value={row?.beltId ?? ''}
                            onValueChange={(beltId) =>
                              update(item.enrollment_id, { beltId })
                            }
                          >
                            <SelectTrigger className="w-56 rounded-xl">
                              <SelectValue placeholder="—" />
                            </SelectTrigger>
                            <SelectContent>
                              {beltList.map((belt) => (
                                <SelectItem key={belt.id} value={belt.id}>
                                  <BeltDrawing belt={belt} width={60} height={12} />
                                  {belt.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="py-2">
                          <Input
                            type="date"
                            aria-label={`Desde quando ${item.student_name} tem a faixa`}
                            value={row?.graduatedOn ?? ''}
                            onChange={(event) =>
                              update(item.enrollment_id, {
                                graduatedOn: event.target.value,
                              })
                            }
                            className="w-40 rounded-xl"
                          />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-end gap-3">
              <span className="text-xs text-muted-foreground">
                {items.length} {items.length === 1 ? 'linha pronta' : 'linhas prontas'}
              </span>
              <Button
                className="rounded-full"
                disabled={items.length === 0 || save.isPending}
                onClick={() => void submit()}
              >
                {save.isPending ? 'Salvando…' : 'Salvar faixas'}
              </Button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
