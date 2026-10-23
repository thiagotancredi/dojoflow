import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { z } from 'zod'

import { DateField } from '@/components/DatePicker'
import { FormField } from '@/components/FormField'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { createGraduationList } from '@/features/belts/api'
import type { GraduationListCreate } from '@/features/belts/api'
import { useGraduationLists } from '@/features/belts/hooks'
import { FormActions } from '@/features/students/components/tabs/BasicDataTab'
import { useAcademyModalities } from '@/features/modalities/hooks'
import { showApiError } from '@/lib/api/errors'
import { formatDate } from '@/lib/format'
import { useMutation } from '@/lib/hooks/useMutation'

const MONTHS = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

// Graduações: listas criadas (tela 3 da spec)
export function GraduationListsPage() {
  const lists = useGraduationLists()
  const [creating, setCreating] = useState(false)

  return (
    <div className="space-y-4">
      <PageHeader
        title="Graduações"
        actions={
          <Button className="rounded-full" onClick={() => setCreating(true)}>
            <Plus /> Nova lista
          </Button>
        }
      />

      <section className="rounded-3xl bg-card p-5">
        {lists.error ? (
          <div className="space-y-3 text-center text-sm">
            <p role="alert" className="text-destructive">
              Não foi possível carregar as listas.
            </p>
            <Button variant="outline" className="rounded-full" onClick={lists.refetch}>
              Tentar de novo
            </Button>
          </div>
        ) : !lists.data ? (
          <p className="text-sm text-muted-foreground">Carregando listas…</p>
        ) : lists.data.length === 0 ? (
          <div className="grid justify-items-center gap-3 rounded-2xl border border-dashed p-8 text-center">
            <p className="font-medium">Nenhuma lista de graduação</p>
            <p className="max-w-md text-sm text-muted-foreground">
              Crie uma lista para conferir quem está apto a graduar no dia do
              exame.
            </p>
            <Button className="rounded-full" onClick={() => setCreating(true)}>
              <Plus /> Nova lista
            </Button>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {lists.data.map((list) => (
              <Link
                key={list.id}
                to={`/app/graduacoes/${list.id}`}
                className="space-y-1 rounded-2xl border p-4 transition-colors hover:bg-accent"
              >
                <p className="font-medium">{list.name}</p>
                <p className="text-xs text-muted-foreground">
                  {list.modality.emoji} {list.modality.name} · exame em{' '}
                  {formatDate(list.exam_date)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {list.entry_count} {list.entry_count === 1 ? 'aluno' : 'alunos'}
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova lista de graduação</DialogTitle>
          </DialogHeader>
          {creating && <NewListForm onClose={() => setCreating(false)} />}
        </DialogContent>
      </Dialog>
    </div>
  )
}

const newListSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, { error: 'Dê um nome à lista.' })
    .max(120, { error: 'Até 120 caracteres.' }),
  modality_id: z.string().min(1, { error: 'Escolha a modalidade.' }),
  exam_date: z.string().min(1, { error: 'Informe a data do exame.' }),
})

function NewListForm({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const { offered, isLoading } = useAcademyModalities()
  // Só modalidades oferecidas que já têm faixas cadastradas
  const withBelts = offered.filter((item) => item.has_belts)
  const now = new Date()
  const create = useMutation((payload: GraduationListCreate) =>
    createGraduationList(payload),
  )
  const form = useForm<GraduationListCreate>({
    resolver: zodResolver(newListSchema),
    defaultValues: {
      name: `Alunos aptos a graduar em ${MONTHS[now.getMonth()]}/${now.getFullYear()}`,
      modality_id: '',
      exam_date: '',
    },
  })
  const {
    register,
    control,
    formState: { errors },
  } = form

  async function save(values: GraduationListCreate) {
    try {
      const created = await create.mutate(values)
      toast.success('Lista criada')
      navigate(`/app/graduacoes/${created.id}`)
    } catch (error) {
      showApiError(error)
    }
  }

  if (!isLoading && withBelts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nenhuma modalidade com faixas cadastradas. Cadastre as faixas em{' '}
        <Link to="/app/configuracoes" className="font-medium underline">
          Configurações
        </Link>{' '}
        primeiro.
      </p>
    )
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <FormField label="Nome *" htmlFor="list-name" error={errors.name?.message}>
        <Input id="list-name" className="rounded-xl" {...register('name')} />
      </FormField>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Modalidade *" error={errors.modality_id?.message}>
          <Controller
            control={control}
            name="modality_id"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger className="w-full rounded-xl">
                  <SelectValue placeholder="Escolha" />
                </SelectTrigger>
                <SelectContent>
                  {withBelts.map((modality) => (
                    <SelectItem key={modality.id} value={modality.id}>
                      {modality.emoji} {modality.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </FormField>
        <FormField
          label="Data do exame *"
          htmlFor="exam-date"
          error={errors.exam_date?.message}
        >
          <Controller
            control={control}
            name="exam_date"
            render={({ field }) => (
              <DateField
                id="exam-date"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FormField>
      </div>
      <p className="text-xs text-muted-foreground">
        "Apto" e o tempo de faixa de cada aluno são medidos na data do exame.
      </p>
      <FormActions
        isPending={create.isPending}
        onCancel={onClose}
        submitLabel="Criar lista"
      />
    </form>
  )
}
