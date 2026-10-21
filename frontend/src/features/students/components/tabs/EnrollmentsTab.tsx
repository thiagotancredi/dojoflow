import { zodResolver } from '@hookform/resolvers/zod'
import { Pencil, Plus } from 'lucide-react'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { BeltPicker } from '@/features/belts/components/BeltPicker'
import { EnrollmentBeltBlock } from '@/features/belts/components/EnrollmentBeltBlock'
import { useBelts } from '@/features/belts/hooks'
import { todayIso } from '@/features/belts/rules'
import { useAcademyModalities } from '@/features/modalities/hooks'
import type { Enrollment, StudentDetail } from '@/features/students/api'
import { EnrollmentFeeCard } from '@/features/students/components/EnrollmentFeeCard'
import { EnrollmentFields } from '@/features/students/components/EnrollmentFields'
import { FormActions } from '@/features/students/components/tabs/BasicDataTab'
import {
  useAddEnrollment,
  useUpdateEnrollment,
} from '@/features/students/hooks'
import {
  emptyEnrollment,
  enrollmentSchema,
  toEnrollmentPayload,
} from '@/features/students/schemas'
import type { EnrollmentValues } from '@/features/students/schemas'
import { applyFieldErrors, showApiError } from '@/lib/api/errors'
import { moneyToInput } from '@/lib/money'
import { cn } from '@/lib/utils'

export type StudentTabProps = {
  student: StudentDetail
  // Chamado depois de salvar algo: a ficha busca os dados de novo
  onChanged: () => void
}

export function EnrollmentsTab({ student: detail, onChanged }: StudentTabProps) {
  const studentId = detail.student.id
  // null = fechado · 'new' = nova matrícula · Enrollment = editando
  const [editing, setEditing] = useState<Enrollment | 'new' | null>(null)
  const { offered } = useAcademyModalities()
  const enrolledIds = new Set(detail.enrollments.map((item) => item.modality_id))
  const available = offered.filter((item) => !enrolledIds.has(item.id))

  return (
    <div className="space-y-3">
      {/* @container: as colunas dependem da largura do painel da ficha,
          não da tela inteira (a lista de alunos divide o espaço com ela) */}
      <div className="@container space-y-5">
        {detail.enrollments.map((enrollment) => (
          <section
            key={enrollment.id}
            className={cn(
              'space-y-2',
              enrollment.status === 'inactive' && 'opacity-70',
            )}
          >
            <h3 className="flex items-center gap-2 font-semibold">
              {enrollment.modality_name}
              {enrollment.status === 'inactive' && (
                <span className="text-xs font-normal text-muted-foreground">
                  Inativa
                </span>
              )}
            </h3>
            {/* Faixa e Mensalidade lado a lado (um embaixo do outro se estreito) */}
            <div className="grid gap-2.5 @lg:grid-cols-2">
              <EnrollmentBeltBlock
                studentId={studentId}
                enrollmentId={enrollment.id}
                modalityId={enrollment.modality_id}
                modalityName={enrollment.modality_name}
              />
              <EnrollmentFeeCard
                enrollment={enrollment}
                actions={
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 rounded-full text-xs"
                    onClick={() => setEditing(enrollment)}
                  >
                    <Pencil /> Editar
                  </Button>
                }
              />
            </div>
          </section>
        ))}
      </div>

      <Button
        variant="outline"
        className="rounded-full"
        onClick={() => setEditing('new')}
      >
        <Plus /> Nova matrícula
      </Button>

      <Dialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing === 'new'
                ? 'Nova matrícula'
                : `Editar matrícula · ${editing?.modality_name ?? ''}`}
            </DialogTitle>
          </DialogHeader>
          {editing === 'new' &&
            (available.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                O aluno já está em todas as modalidades oferecidas pela
                academia.
              </p>
            ) : (
              <NewEnrollmentForm
                studentId={studentId}
                modalities={available}
                onClose={() => setEditing(null)}
                onSaved={onChanged}
              />
            ))}
          {editing && editing !== 'new' && (
            <EditEnrollmentForm
              studentId={studentId}
              enrollment={editing}
              onClose={() => setEditing(null)}
              onSaved={onChanged}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

type FormProps = {
  studentId: string
  onClose: () => void
  onSaved: () => void
}

function EditEnrollmentForm({
  studentId,
  enrollment,
  onClose,
  onSaved,
}: FormProps & { enrollment: Enrollment }) {
  const { mutate, isPending } = useUpdateEnrollment(studentId)
  const form = useForm<EnrollmentValues>({
    resolver: zodResolver(enrollmentSchema),
    defaultValues: {
      modality_id: enrollment.modality_id,
      status: enrollment.status,
      is_exempt: enrollment.is_exempt,
      monthly_fee: moneyToInput(enrollment.monthly_fee),
      due_day: enrollment.due_day?.toString() ?? '',
    },
  })

  async function save(values: EnrollmentValues) {
    try {
      await mutate(enrollment.id, toEnrollmentPayload(values))
      toast.success('Matrícula salva')
      onSaved()
      onClose()
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <EnrollmentFields form={form} showStatus />
      <FormActions isPending={isPending} onCancel={onClose} />
    </form>
  )
}

function NewEnrollmentForm({
  studentId,
  modalities,
  onClose,
  onSaved,
}: FormProps & { modalities: { id: string; name: string }[] }) {
  const { mutate, isPending } = useAddEnrollment(studentId)
  const form = useForm<EnrollmentValues>({
    resolver: zodResolver(enrollmentSchema),
    defaultValues: emptyEnrollment(modalities[0].id),
  })
  const modalityId = useWatch({ control: form.control, name: 'modality_id' })
  const belts = useBelts(modalityId || null).data ?? []
  // Faixa atual escolhida por modalidade; padrão a primeira (Branca)
  const [beltChoice, setBeltChoice] = useState<Record<string, string>>({})
  const [since, setSince] = useState(todayIso())
  const beltId = belts.length ? (beltChoice[modalityId] ?? belts[0].id) : null

  async function save(values: EnrollmentValues) {
    try {
      // Matrícula e faixa atual numa gravação só (tudo ou nada)
      await mutate({
        modality_id: values.modality_id,
        ...toEnrollmentPayload(values),
        current_belt: beltId ? { belt_id: beltId, graduated_on: since } : null,
      })
      toast.success('Matrícula criada')
      onSaved()
      onClose()
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) showApiError(error)
    }
  }

  return (
    <form noValidate onSubmit={form.handleSubmit(save)} className="space-y-4">
      <EnrollmentFields form={form} modalities={modalities} />
      {belts.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Faixa atual (aluno começando agora: a primeira faixa e hoje)
          </p>
          <BeltPicker
            belts={belts}
            value={beltId}
            onChange={(id) =>
              setBeltChoice((current) => ({ ...current, [modalityId]: id }))
            }
          />
          <div className="space-y-1.5">
            <Label htmlFor="belt_since" className="text-xs text-muted-foreground">
              Desde
            </Label>
            <Input
              id="belt_since"
              type="date"
              value={since}
              onChange={(event) => setSince(event.target.value)}
              className="rounded-xl"
            />
          </div>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          Esta modalidade não tem faixas.
        </p>
      )}
      <FormActions isPending={isPending} onCancel={onClose} />
    </form>
  )
}
