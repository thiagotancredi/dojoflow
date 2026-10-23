import { zodResolver } from '@hookform/resolvers/zod'
import { useImperativeHandle, useState } from 'react'
import type { Ref } from 'react'
import { useForm, useWatch } from 'react-hook-form'

import { DateField } from '@/components/DatePicker'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { BeltPicker } from '@/features/belts/components/BeltPicker'
import { useBelts } from '@/features/belts/hooks'
import { EnrollmentFields } from '@/features/students/components/EnrollmentFields'
import { enrollmentSchema } from '@/features/students/schemas'
import type { EnrollmentValues } from '@/features/students/schemas'

// Uma matrícula do cadastro + faixa atual (id da faixa) e desde quando
export type EnrollmentDraft = {
  values: EnrollmentValues
  beltId: string | null
  since: string
}

// O que o cadastro pode pedir a cada bloco
export type EnrollmentBlockHandle = {
  // Valida e devolve os dados (null se tiver erro)
  collect: () => Promise<EnrollmentDraft | null>
  // Dados como estão, sem validar (para "Voltar" sem perder o digitado)
  snapshot: () => EnrollmentDraft
}

type EnrollmentBlockProps = {
  ref: Ref<EnrollmentBlockHandle>
  index: number
  initial: EnrollmentDraft
  // Modalidades que este bloco pode escolher (as dos outros blocos saem)
  modalities: { id: string; name: string }[]
  onModalityChange: (modalityId: string) => void
  onRemove?: () => void
}

export function EnrollmentBlock({
  ref,
  index,
  initial,
  modalities,
  onModalityChange,
  onRemove,
}: EnrollmentBlockProps) {
  const form = useForm<EnrollmentValues>({
    resolver: zodResolver(enrollmentSchema),
    defaultValues: initial.values,
  })
  const modalityId = useWatch({ control: form.control, name: 'modality_id' })
  const modalityName =
    modalities.find((item) => item.id === modalityId)?.name ?? ''
  const belts = useBelts(modalityId || null).data ?? []

  // Faixa escolhida por modalidade (trocar de modalidade não mistura faixas)
  const [beltChoice, setBeltChoice] = useState<Record<string, string>>(
    initial.beltId ? { [initial.values.modality_id]: initial.beltId } : {},
  )
  const [since, setSince] = useState(initial.since)
  const beltId = belts.length
    ? (beltChoice[modalityId] ?? belts[0].id)
    : null

  // React 19: "ref" chega como prop; o pai chama collect/snapshot no clique
  useImperativeHandle(ref, () => ({
    collect: async () => {
      const valid = await form.trigger()
      return valid ? { values: form.getValues(), beltId, since } : null
    },
    snapshot: () => ({ values: form.getValues(), beltId, since }),
  }))

  return (
    <div className="space-y-3 rounded-2xl border p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Matrícula {index + 1}</p>
        {onRemove && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="rounded-full text-destructive"
            onClick={onRemove}
          >
            Remover
          </Button>
        )}
      </div>

      <EnrollmentFields
        form={form}
        modalities={modalities}
        idPrefix={`enrollment-${index}`}
        onModalityChange={onModalityChange}
        showEnrollmentFee
      />

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
          <div className="max-w-xs space-y-1.5">
            <Label
              htmlFor={`belt-since-${index}`}
              className="text-xs text-muted-foreground"
            >
              Desde
            </Label>
            <DateField
              id={`belt-since-${index}`}
              value={since}
              onChange={setSince}
            />
          </div>
        </div>
      ) : (
        modalityName && (
          <p className="text-xs text-muted-foreground">
            Esta modalidade não tem faixas.
          </p>
        )
      )}
    </div>
  )
}
