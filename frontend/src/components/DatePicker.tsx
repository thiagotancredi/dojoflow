import { useState, type ReactNode } from 'react'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import { DayPicker } from 'react-day-picker'
import { ptBR } from 'react-day-picker/locale'

import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  MONTHS_SHORT,
  formatMonthLong,
  parseIsoDate,
  parseIsoMonth,
  toIsoDate,
  toIsoMonth,
} from '@/lib/dates'
import { formatDate } from '@/lib/format'
import { useMediaQuery } from '@/lib/hooks/useMediaQuery'
import { cn } from '@/lib/utils'

// Calendário do sistema, no lugar do <input type="date"> do navegador
// (que muda de cara em cada celular/computador). No computador abre
// colado no campo; no celular sobe de baixo, como uma gaveta.

type FieldProps = {
  // Texto no formato da API: "2026-10-23" (data) ou "2026-10" (mês); "" = vazio
  value: string
  onChange: (value: string) => void
  id?: string
  'aria-label'?: string
  placeholder?: string
  disabled?: boolean
  className?: string
}

// Campo de data: mostra "23/10/2026" e abre o calendário de dias
export function DateField({
  value,
  onChange,
  placeholder = 'Escolher data',
  ...props
}: FieldProps) {
  const [open, setOpen] = useState(false)

  function pick(date: Date) {
    onChange(toIsoDate(date))
    setOpen(false)
  }

  return (
    <PickerShell
      open={open}
      onOpenChange={setOpen}
      title="Escolher data"
      trigger={
        <FieldButton {...props} empty={!value}>
          {value ? formatDate(value) : placeholder}
        </FieldButton>
      }
    >
      <CalendarPanel
        kind="date"
        selected={parseIsoDate(value)}
        onPick={pick}
        onCancel={() => setOpen(false)}
      />
    </PickerShell>
  )
}

// Campo de mês: mostra "outubro 2026" e abre a grade de meses
export function MonthField({
  value,
  onChange,
  max,
  placeholder = 'Escolher mês',
  ...props
}: FieldProps & { max?: string }) {
  const [open, setOpen] = useState(false)
  const selected = parseIsoMonth(value)

  function pick(date: Date) {
    onChange(toIsoMonth(date))
    setOpen(false)
  }

  return (
    <PickerShell
      open={open}
      onOpenChange={setOpen}
      title="Escolher mês"
      trigger={
        <FieldButton {...props} empty={!selected}>
          {selected ? formatMonthLong(selected) : placeholder}
        </FieldButton>
      }
    >
      <CalendarPanel
        kind="month"
        selected={selected}
        max={parseIsoMonth(max)}
        onPick={pick}
        onCancel={() => setOpen(false)}
      />
    </PickerShell>
  )
}

// Botão com cara de campo de texto (mesmas bordas e tamanhos do <Input>)
function FieldButton({
  empty,
  children,
  className,
  ...props
}: Omit<FieldProps, 'value' | 'onChange' | 'placeholder'> & {
  empty: boolean
  children: ReactNode
}) {
  return (
    <button
      type="button"
      className={cn(
        'flex h-8 w-full min-w-0 items-center justify-between gap-2 rounded-xl border border-input bg-transparent px-2.5 text-left text-base whitespace-nowrap outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 md:text-sm dark:bg-input/30',
        empty && 'text-muted-foreground',
        className,
      )}
      {...props}
    >
      <span className="truncate">{children}</span>
      <CalendarDays className="size-4 shrink-0 text-muted-foreground" />
    </button>
  )
}

// Computador: balão (Popover) colado no campo.
// Celular: gaveta que sobe de baixo (um Dialog preso no rodapé da tela).
function PickerShell({
  open,
  onOpenChange,
  title,
  trigger,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  trigger: ReactNode
  children: ReactNode
}) {
  const isDesktop = useMediaQuery('(min-width: 768px)')

  if (isDesktop) {
    return (
      <Popover open={open} onOpenChange={onOpenChange}>
        <PopoverTrigger asChild>{trigger}</PopoverTrigger>
        <PopoverContent aria-label={title}>{children}</PopoverContent>
      </Popover>
    )
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
        <DialogPrimitive.Content
          // Sem texto de descrição: avisa o Radix que é de propósito
          aria-describedby={undefined}
          className="fixed inset-x-0 bottom-0 z-50 rounded-t-3xl bg-popover px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))] text-popover-foreground shadow-2xl outline-none data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom data-[state=closed]:animate-out data-[state=closed]:slide-out-to-bottom"
        >
          {/* Alça: só um sinal visual de que é uma gaveta */}
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" />
          <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
          <div className="mx-auto max-w-sm">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

type View = 'days' | 'months' | 'years'

// O miolo do calendário, com três telas:
// dias (outubro 2026) → toca no nome → meses (2026) → toca no ano → anos.
// Assim a data de nascimento não obriga a voltar mês a mês.
function CalendarPanel({
  kind,
  selected,
  max,
  onPick,
  onCancel,
}: {
  kind: 'date' | 'month'
  selected: Date | undefined
  max?: Date
  onPick: (date: Date) => void
  onCancel: () => void
}) {
  const today = new Date()
  const [view, setView] = useState<View>(kind === 'date' ? 'days' : 'months')
  // Mês que o calendário está mostrando (sempre dia 1)
  const [cursor, setCursor] = useState(() => {
    const base = selected ?? today
    return new Date(base.getFullYear(), base.getMonth(), 1)
  })

  const year = cursor.getFullYear()
  const month = cursor.getMonth()
  const decadeStart = Math.floor(year / 12) * 12

  // Setas ‹ › andam um mês, um ano ou 12 anos, conforme a tela
  function step(direction: -1 | 1) {
    if (view === 'days') setCursor(new Date(year, month + direction, 1))
    else if (view === 'months') setCursor(new Date(year + direction, month, 1))
    else setCursor(new Date(year + direction * 12, month, 1))
  }

  const title =
    view === 'days'
      ? formatMonthLong(cursor)
      : view === 'months'
        ? String(year)
        : `${decadeStart} – ${decadeStart + 11}`

  const isAfterMax = (y: number, m: number) =>
    max !== undefined &&
    (y > max.getFullYear() || (y === max.getFullYear() && m > max.getMonth()))

  function pickMonth(m: number) {
    if (kind === 'month') {
      onPick(new Date(year, m, 1))
      return
    }
    setCursor(new Date(year, m, 1))
    setView('days')
  }

  function pickToday() {
    onPick(kind === 'month' ? new Date(today.getFullYear(), today.getMonth(), 1) : today)
  }

  return (
    <div className="w-full md:w-[18rem]">
      {/* Cabeçalho: ‹  outubro 2026  › */}
      <div className="flex items-center justify-between gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full"
          aria-label="Anterior"
          onClick={() => step(-1)}
        >
          <ChevronLeft />
        </Button>
        <button
          type="button"
          disabled={view === 'years'}
          onClick={() => setView(view === 'days' ? 'months' : 'years')}
          className="rounded-full px-3 py-1 text-sm font-semibold capitalize transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/40 disabled:hover:bg-transparent"
        >
          {title}
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full"
          aria-label="Próximo"
          onClick={() => step(1)}
        >
          <ChevronRight />
        </Button>
      </div>

      <div className="mt-2 min-h-[17rem]">
        {view === 'days' && (
          <DayPicker
            mode="single"
            locale={ptBR}
            month={cursor}
            onMonthChange={setCursor}
            selected={selected}
            onSelect={(date) => date && onPick(date)}
            hideNavigation
            showOutsideDays
            classNames={{
              root: 'w-full',
              month_caption: 'sr-only',
              month_grid: 'w-full border-collapse',
              weekday: 'pb-1 text-[11px] font-normal text-muted-foreground uppercase',
              day: 'p-0.5 text-center',
              day_button:
                'mx-auto grid size-10 place-items-center rounded-full text-sm transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/40 md:size-9',
              selected:
                'font-semibold [&>button]:bg-sidebar-primary [&>button]:text-sidebar-primary-foreground [&>button]:hover:bg-sidebar-primary',
              today: 'font-semibold [&>button]:ring-1 [&>button]:ring-chip-active-border',
              outside: 'text-muted-foreground/50',
              disabled: 'opacity-40',
            }}
          />
        )}

        {view === 'months' && (
          <Grid>
            {MONTHS_SHORT.map((label, m) => (
              <GridButton
                key={label}
                active={
                  selected?.getFullYear() === year && selected.getMonth() === m
                }
                current={today.getFullYear() === year && today.getMonth() === m}
                disabled={isAfterMax(year, m)}
                onClick={() => pickMonth(m)}
              >
                {label}
              </GridButton>
            ))}
          </Grid>
        )}

        {view === 'years' && (
          <Grid>
            {Array.from({ length: 12 }, (_, i) => decadeStart + i).map((y) => (
              <GridButton
                key={y}
                active={selected?.getFullYear() === y}
                current={today.getFullYear() === y}
                disabled={max !== undefined && y > max.getFullYear()}
                onClick={() => {
                  setCursor(new Date(y, month, 1))
                  setView('months')
                }}
              >
                {y}
              </GridButton>
            ))}
          </Grid>
        )}
      </div>

      {/* Rodapé: atalho para hoje e fechar sem mudar nada */}
      <div className="mt-2 flex items-center justify-between gap-2">
        <Button
          variant="outline"
          size="sm"
          className="rounded-full"
          disabled={kind === 'month' && isAfterMax(today.getFullYear(), today.getMonth())}
          onClick={pickToday}
        >
          {kind === 'month' ? 'Este mês' : 'Hoje'}
        </Button>
        <Button size="sm" variant="ghost" className="rounded-full" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </div>
  )
}

function Grid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-3 gap-2 pt-2">{children}</div>
}

function GridButton({
  active,
  current,
  disabled,
  onClick,
  children,
}: {
  active: boolean
  current: boolean
  disabled?: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'h-11 rounded-full text-sm transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/40 disabled:pointer-events-none disabled:opacity-35',
        current && !active && 'ring-1 ring-chip-active-border',
        active &&
          'bg-sidebar-primary font-semibold text-sidebar-primary-foreground hover:bg-sidebar-primary',
      )}
    >
      {children}
    </button>
  )
}
