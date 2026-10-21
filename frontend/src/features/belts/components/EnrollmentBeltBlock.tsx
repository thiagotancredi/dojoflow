import { useState } from 'react'
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
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { BeltPicker } from '@/features/belts/components/BeltPicker'
import {
  addMockGraduation,
  findMockBelt,
  mockBeltsFor,
  nextMockBelt,
  useMockBeltHistory,
} from '@/features/belts/mock'
import { eligibility, timeSince, todayIso } from '@/features/belts/rules'
import { formatDate } from '@/lib/format'

type EnrollmentBeltBlockProps = {
  studentId: string
  modalityId: string
  modalityName: string
}

// Bloco de faixa dentro do card de matrícula (dados de exemplo por enquanto)
export function EnrollmentBeltBlock({
  studentId,
  modalityId,
  modalityName,
}: EnrollmentBeltBlockProps) {
  const records = useMockBeltHistory(studentId, modalityId, modalityName)
  const [dialog, setDialog] = useState<'register' | 'history' | null>(null)

  // Modalidade sem faixas (ex.: Boxe): nada aparece
  if (mockBeltsFor(modalityName).length === 0) return null

  const current = records[0] ?? null
  const currentBelt = current && findMockBelt(modalityName, current.belt)

  return (
    <div className="mt-2 space-y-1.5 rounded-lg bg-card p-2.5">
      {current && currentBelt ? (
        <>
          <BeltDrawing belt={currentBelt} width={200} height={26} />
          <p>
            <span className="font-medium">{current.belt}</span>{' '}
            <span className="text-xs text-muted-foreground">
              · {timeSince(current.graduatedOn)}
            </span>
          </p>
          <EligibilityLine
            graduatedOn={current.graduatedOn}
            minMonths={currentBelt.minMonths}
          />
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            <Button
              size="sm"
              className="h-7 rounded-full text-xs"
              onClick={() => setDialog('register')}
            >
              Registrar graduação
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 rounded-full text-xs"
              onClick={() => setDialog('history')}
            >
              Histórico ({records.length})
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
            onClick={() => setDialog('register')}
          >
            Registrar faixa atual
          </Button>
        </>
      )}

      <Dialog
        open={dialog === 'register'}
        onOpenChange={(open) => !open && setDialog(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {current ? 'Registrar graduação' : 'Registrar faixa atual'} ·{' '}
              {modalityName}
            </DialogTitle>
          </DialogHeader>
          {dialog === 'register' && (
            <RegisterGraduation
              modalityName={modalityName}
              current={current?.belt ?? null}
              onSave={(belt, graduatedOn) => {
                addMockGraduation(studentId, modalityId, { belt, graduatedOn })
                toast.success('Graduação registrada')
                setDialog(null)
              }}
              onCancel={() => setDialog(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog
        open={dialog === 'history'}
        onOpenChange={(open) => !open && setDialog(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Histórico de faixas · {modalityName}</DialogTitle>
          </DialogHeader>
          <ul className="space-y-2">
            {records.map((record) => {
              const look = findMockBelt(modalityName, record.belt)
              return (
                <li
                  key={`${record.belt}-${record.graduatedOn}`}
                  className="flex items-center justify-between gap-3 rounded-xl border px-3 py-2 text-sm"
                >
                  <span className="flex items-center gap-2">
                    {look && <BeltDrawing belt={look} width={110} height={16} />}
                    {record.belt}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(record.graduatedOn)}
                  </span>
                </li>
              )
            })}
          </ul>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function EligibilityLine({
  graduatedOn,
  minMonths,
}: {
  graduatedOn: string
  minMonths: number | null
}) {
  const result = eligibility(graduatedOn, minMonths)

  if (result.kind === 'no_requirement') {
    return <p className="text-xs text-muted-foreground">Sem tempo mínimo</p>
  }

  if (result.kind === 'eligible') {
    return (
      <p className="flex items-center gap-1.5 text-xs">
        <span className="size-2 rounded-full bg-status-exempt" />
        <span className="text-status-exempt">Apto</span>
      </p>
    )
  }

  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className="size-2 rounded-full bg-status-pending" />
      Ainda não · apto a partir de {formatDate(result.on)}
    </p>
  )
}

type RegisterGraduationProps = {
  modalityName: string
  current: string | null
  onSave: (belt: string, graduatedOn: string) => void
  onCancel: () => void
}

function RegisterGraduation({
  modalityName,
  current,
  onSave,
  onCancel,
}: RegisterGraduationProps) {
  const suggested = nextMockBelt(modalityName, current)
  const [belt, setBelt] = useState<string | null>(suggested)
  const [graduatedOn, setGraduatedOn] = useState(todayIso())

  const tags: Record<string, string> = {}
  if (current) tags[current] = 'atual'
  if (suggested && suggested !== current) tags[suggested] = 'próxima'

  return (
    <div className="space-y-4">
      <BeltPicker
        belts={mockBeltsFor(modalityName)}
        value={belt}
        onChange={setBelt}
        tags={tags}
      />
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
      <p className="text-xs text-muted-foreground">
        {current
          ? 'A próxima faixa já vem marcada; dá para escolher outra (inclusive pular).'
          : 'Aluno antigo: escolha a faixa atual e uma data aproximada.'}
      </p>
      <div className="flex justify-end gap-2">
        <Button variant="outline" className="rounded-full" onClick={onCancel}>
          Cancelar
        </Button>
        <Button
          className="rounded-full"
          disabled={!belt || !graduatedOn}
          onClick={() => belt && onSave(belt, graduatedOn)}
        >
          Salvar
        </Button>
      </div>
    </div>
  )
}
