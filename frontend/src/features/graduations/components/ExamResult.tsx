import { Check, X } from 'lucide-react'

import { InfoTip } from '@/components/InfoTip'
import { Button } from '@/components/ui/button'
import type { Belt, GraduationEntry } from '@/features/belts/api'
import { dayMonth } from '@/features/graduations/charge'
import { approveBlock } from '@/features/graduations/results'
import { formatDate } from '@/lib/format'

// Coluna "Resultado" da lista de graduação: aprovar / reprovar no exame

export function ResultTip() {
  return (
    <InfoTip label="Sobre o resultado do exame">
      <p className="font-semibold">Resultado do exame</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        Ao aprovar, a faixa nova vai para a ficha do aluno, com a data
        escolhida. Se ele pular faixa, recebe também as faixas do meio, na
        mesma data.
      </p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        Só dá para aprovar quem pagou ou foi isento da graduação.
      </p>
    </InfoTip>
  )
}

export function ApprovedSeal({ entry, long }: { entry: GraduationEntry; long?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-status-exempt-soft px-2.5 py-0.5 text-xs font-medium whitespace-nowrap text-status-exempt">
      <Check className="size-3.5" />
      Aprovado
      {long && entry.result_on && ` em ${formatDate(entry.result_on)}`}
    </span>
  )
}

export function FailedSeal() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-status-critical-soft px-2.5 py-0.5 text-xs font-medium whitespace-nowrap text-status-critical">
      <X className="size-3.5" />
      Reprovado
    </span>
  )
}

// Computador: botões enquanto aguarda; selo depois de decidido
export function ResultCell({
  entry,
  busy,
  onApprove,
  onFail,
}: {
  entry: GraduationEntry
  busy: boolean
  onApprove: () => void
  onFail: () => void
}) {
  if (entry.result === 'approved') {
    return (
      <div className="leading-tight">
        <ApprovedSeal entry={entry} />
        {entry.result_on && (
          <p className="mt-0.5 text-xs text-muted-foreground">em {dayMonth(entry.result_on)}</p>
        )}
      </div>
    )
  }
  if (entry.result === 'failed') return <FailedSeal />

  const blocked = approveBlock(entry)
  return (
    <div className="leading-tight">
      <span className="inline-flex gap-1.5">
        <Button
          variant="outline"
          size="sm"
          className="rounded-full text-status-exempt"
          disabled={busy || blocked !== null}
          onClick={onApprove}
        >
          <Check /> Aprovar
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          title="Reprovar"
          aria-label={`Reprovar ${entry.student_name}`}
          className="rounded-full text-status-critical"
          disabled={busy}
          onClick={onFail}
        >
          <X />
        </Button>
      </span>
      {blocked === 'unpaid' && <p className="mt-0.5 text-xs text-muted-foreground">falta pagar</p>}
    </div>
  )
}

// Embaixo das faixas: "pula 1 faixa (Laranja)" · "pula 2 faixas"
export function SkipHint({ skipped }: { skipped: Belt[] }) {
  if (skipped.length === 0) return null
  return (
    <p className="mt-0.5 text-xs text-status-pending">
      {skipped.length === 1
        ? `pula 1 faixa (${skipped[0].name})`
        : `pula ${skipped.length} faixas`}
    </p>
  )
}
