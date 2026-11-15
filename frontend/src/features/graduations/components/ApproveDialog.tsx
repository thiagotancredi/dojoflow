import { ArrowRight, Check } from 'lucide-react'
import { Fragment, useState } from 'react'

import { DateField } from '@/components/DatePicker'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { Belt, GraduationEntry } from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { beltNames } from '@/features/graduations/results'

// Pop-up "Aprovar Fulano?": caminho das faixas (de → puladas → alvo) e a
// data da aprovação, que já vem com o dia do exame
export function ApproveDialog({
  entry,
  skipped,
  examDate,
  busy,
  onOpenChange,
  onConfirm,
}: {
  entry: GraduationEntry
  skipped: Belt[]
  examDate: string
  busy: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (approvedOn: string) => void
}) {
  const [approvedOn, setApprovedOn] = useState(examDate)
  const path = [...skipped, entry.target_belt]

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Aprovar {entry.student_name}?</DialogTitle>
        </DialogHeader>

        <div className="flex flex-wrap items-center justify-center gap-3 rounded-2xl bg-muted px-3 py-4">
          <BeltStep belt={entry.snapshot_belt} />
          {path.map((belt) => (
            <Fragment key={belt.id}>
              <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
              <BeltStep belt={belt} strong />
            </Fragment>
          ))}
        </div>

        {skipped.length > 0 && (
          <p className="-mt-1 text-center text-xs text-status-pending">
            Pula de faixa: recebe {beltNames(path)} na mesma data.
          </p>
        )}

        <div className="space-y-1.5">
          <label htmlFor="approval-date" className="text-xs text-muted-foreground">
            Data da aprovação
          </label>
          <DateField id="approval-date" value={approvedOn} onChange={setApprovedOn} />
          {approvedOn === examDate && (
            <p className="text-xs text-muted-foreground">Dia do exame</p>
          )}
        </div>

        <p className="text-xs text-muted-foreground">A ficha é atualizada com a faixa nova.</p>

        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            className="h-10 rounded-full"
            onClick={() => onOpenChange(false)}
          >
            Cancelar
          </Button>
          <Button
            className="h-10 rounded-full"
            disabled={busy || !approvedOn}
            onClick={() => onConfirm(approvedOn)}
          >
            <Check /> Aprovar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function BeltStep({ belt, strong }: { belt: Belt | null; strong?: boolean }) {
  if (!belt) return <span className="text-xs text-muted-foreground">Sem faixa</span>
  return (
    <span className="flex flex-col items-center gap-1">
      <BeltDrawing belt={belt} width={90} height={16} className="w-16" />
      <span className={strong ? 'text-xs font-semibold' : 'text-xs text-muted-foreground'}>
        {belt.name}
      </span>
    </span>
  )
}
