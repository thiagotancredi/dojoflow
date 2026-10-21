import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'

import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Belt, BeltPayload } from '@/features/belts/api'
import { BeltDrawing } from '@/features/belts/components/BeltDrawing'
import { cn } from '@/lib/utils'

// Paleta da spec; "outra cor" abre o seletor do navegador
const BELT_COLORS: { name: string; hex: string }[] = [
  { name: 'Branca', hex: '#f8fafc' },
  { name: 'Amarela', hex: '#facc15' },
  { name: 'Laranja', hex: '#f97316' },
  { name: 'Verde', hex: '#16a34a' },
  { name: 'Azul', hex: '#1d4ed8' },
  { name: 'Roxa', hex: '#7c3aed' },
  { name: 'Marrom', hex: '#78350f' },
  { name: 'Preta', hex: '#111827' },
  { name: 'Vermelha', hex: '#dc2626' },
  { name: 'Cinza', hex: '#9ca3af' },
]
const GOLD = '#d4a017'
const MAX_MIN_TIME = 1200

const hex = z.string().regex(/^#[0-9a-fA-F]{6}$/, { error: 'Cor inválida.' })
const optionalHex = z.union([z.literal(''), hex])

const beltFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, { error: 'Dê um nome à faixa.' })
    .max(80, { error: 'Até 80 caracteres.' }),
  primary_color: hex,
  stripe_color: optionalHex,
  marks: z.number().int().min(0).max(10, { error: 'De 0 a 10.' }),
  marks_color: hex,
  tip_color: optionalHex,
  min_time_amount: z
    .string()
    .trim()
    .regex(/^(\d+)?$/, { error: 'Só números.' })
    .refine((value) => value === '' || (+value >= 1 && +value <= MAX_MIN_TIME), {
      error: `De 1 a ${MAX_MIN_TIME}.`,
    }),
  min_time_unit: z.enum(['days', 'months', 'years']),
})

type BeltFormValues = z.infer<typeof beltFormSchema>

function toFormValues(belt: Belt | null): BeltFormValues {
  return {
    name: belt?.name ?? '',
    primary_color: belt?.primary_color ?? BELT_COLORS[0].hex,
    stripe_color: belt?.stripe_color ?? '',
    marks: belt?.marks ?? 0,
    marks_color: belt?.marks_color ?? GOLD,
    tip_color: belt?.tip_color ?? '',
    min_time_amount: belt?.min_time_amount?.toString() ?? '3',
    min_time_unit: belt?.min_time_unit ?? 'months',
  }
}

// Tempo vazio = faixa sem tempo mínimo (ex.: a última)
function toPayload(values: BeltFormValues): BeltPayload {
  const amount = values.min_time_amount === '' ? null : Number(values.min_time_amount)

  return {
    name: values.name,
    primary_color: values.primary_color,
    stripe_color: values.stripe_color || null,
    marks: values.marks,
    marks_color: values.marks_color,
    tip_color: values.tip_color || null,
    min_time_amount: amount,
    min_time_unit: amount === null ? null : values.min_time_unit,
  }
}

type BeltFormProps = {
  belt: Belt | null
  isPending: boolean
  onSubmit: (payload: BeltPayload) => void
  onCancel: () => void
}

// Cadastro/edição de uma faixa, com prévia ao vivo do desenho
export function BeltForm({ belt, isPending, onSubmit, onCancel }: BeltFormProps) {
  const form = useForm<BeltFormValues>({
    resolver: zodResolver(beltFormSchema),
    defaultValues: toFormValues(belt),
  })
  const {
    register,
    control,
    formState: { errors },
  } = form
  const preview = useWatch({ control })
  const marks = preview.marks ?? 0

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit((values) => onSubmit(toPayload(values)))}
      className="space-y-4"
    >
      <FormField label="Nome *" htmlFor="belt-name" error={errors.name?.message}>
        <Input
          id="belt-name"
          placeholder="Ex.: Amarela, Azul 2 graus, Preta 1º Dan"
          className="rounded-xl"
          {...register('name')}
        />
      </FormField>

      <ColorField control={control} name="primary_color" label="Cor principal" />
      <ColorField
        control={control}
        name="stripe_color"
        label="Cor da listra (opcional)"
        allowNone
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label="Graus / Dan (marcas na ponta)"
          htmlFor="belt-marks"
          error={errors.marks?.message}
        >
          <Input
            id="belt-marks"
            type="number"
            min={0}
            max={10}
            className="rounded-xl"
            {...register('marks', { valueAsNumber: true })}
          />
        </FormField>
        <FormField
          label="Tempo mínimo na faixa"
          htmlFor="belt-time"
          error={errors.min_time_amount?.message}
          hint="Vazio = sem tempo mínimo (ex.: a última faixa)."
        >
          <div className="flex gap-2">
            <Input
              id="belt-time"
              inputMode="numeric"
              className="w-24 rounded-xl"
              {...register('min_time_amount')}
            />
            <Controller
              control={control}
              name="min_time_unit"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="flex-1 rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="days">dias</SelectItem>
                    <SelectItem value="months">meses</SelectItem>
                    <SelectItem value="years">anos</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </div>
        </FormField>
      </div>

      {marks > 0 && (
        <>
          <ColorField
            control={control}
            name="marks_color"
            label="Cor das marcas"
            extra={[{ name: 'Dourado', hex: GOLD }]}
          />
          <ColorField
            control={control}
            name="tip_color"
            label="Cor da ponta (opcional; ex.: jiu-jitsu usa ponta preta)"
            allowNone
          />
        </>
      )}

      <div className="space-y-2 rounded-2xl bg-muted p-4">
        <p className="text-xs text-muted-foreground">Prévia</p>
        <BeltDrawing
          belt={{
            name: preview.name || 'Nova faixa',
            primary_color: preview.primary_color ?? BELT_COLORS[0].hex,
            stripe_color: preview.stripe_color || null,
            marks: Number.isFinite(marks) ? Math.min(Math.max(marks, 0), 10) : 0,
            marks_color: preview.marks_color ?? GOLD,
            tip_color: preview.tip_color || null,
          }}
          width={280}
          height={40}
        />
        <p className="text-sm">{preview.name || 'Nova faixa'}</p>
      </div>

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          className="rounded-full"
          onClick={onCancel}
        >
          Cancelar
        </Button>
        <Button type="submit" className="rounded-full" disabled={isPending}>
          {isPending ? 'Salvando…' : 'Salvar'}
        </Button>
      </div>
    </form>
  )
}

type ColorName = 'primary_color' | 'stripe_color' | 'marks_color' | 'tip_color'

function ColorField({
  control,
  name,
  label,
  allowNone = false,
  extra = [],
}: {
  control: ReturnType<typeof useForm<BeltFormValues>>['control']
  name: ColorName
  label: string
  allowNone?: boolean
  extra?: { name: string; hex: string }[]
}) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => {
        const options = [...extra, ...BELT_COLORS]
        const isCustom =
          field.value !== '' && !options.some((color) => color.hex === field.value)

        return (
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground">{label}</p>
            <div className="flex flex-wrap items-center gap-2" role="radiogroup">
              {allowNone && (
                <Swatch
                  title="Nenhuma"
                  selected={field.value === ''}
                  onClick={() => field.onChange('')}
                  className="bg-[repeating-linear-gradient(45deg,#fff_0_4px,#e5e7eb_4px_8px)]"
                />
              )}
              {options.map((color) => (
                <Swatch
                  key={color.hex + color.name}
                  title={color.name}
                  selected={field.value === color.hex}
                  onClick={() => field.onChange(color.hex)}
                  style={{ background: color.hex }}
                />
              ))}
              <label
                className={cn(
                  'flex cursor-pointer items-center gap-1 rounded-full border px-2 py-1 text-xs',
                  isCustom && 'border-primary ring-2 ring-primary',
                )}
              >
                <input
                  type="color"
                  value={field.value || '#000000'}
                  onChange={(event) => field.onChange(event.target.value)}
                  className="size-5 cursor-pointer border-0 bg-transparent p-0"
                />
                Outra cor
              </label>
            </div>
          </div>
        )
      }}
    />
  )
}

function Swatch({
  title,
  selected,
  onClick,
  className,
  style,
}: {
  title: string
  selected: boolean
  onClick: () => void
  className?: string
  style?: React.CSSProperties
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      aria-label={title}
      title={title}
      onClick={onClick}
      style={style}
      className={cn(
        'size-7 rounded-full border-2 border-white shadow-[0_0_0_1px_var(--color-border)]',
        selected && 'shadow-[0_0_0_3px_var(--color-primary)]',
        className,
      )}
    />
  )
}
