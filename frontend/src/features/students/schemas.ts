import { z } from 'zod'

import { parseMoney } from '@/lib/money'

// Regras dos formulários de aluno, iguais às do backend. Os campos do
// formulário são sempre texto ('' = não informado); as funções to*Payload
// convertem para o formato da API ('' → null).

const text = (max: number) =>
  z.string().trim().max(max, { error: `Até ${max} caracteres.` })

const emptyToNull = (value: string) => (value === '' ? null : value)

// ---------- Dados do aluno ----------
export const basicDataSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, { error: 'O nome precisa de pelo menos 2 letras.' })
    .max(120, { error: 'Até 120 caracteres.' }),
  phone: text(20),
  phone_is_whatsapp: z.boolean(),
  email: text(255).refine(
    (value) => value === '' || z.email().safeParse(value).success,
    { error: 'E-mail inválido.' },
  ),
  birth_date: z.string(),
  sex: z.enum(['', 'male', 'female', 'other']),
  cpf: z
    .string()
    .trim()
    .regex(/^(\d{11})?$/, { error: 'O CPF tem 11 números (sem pontos).' }),
  instagram: text(80),
})

export type BasicDataValues = z.infer<typeof basicDataSchema>

export const emptyBasicData: BasicDataValues = {
  name: '',
  phone: '',
  phone_is_whatsapp: false,
  email: '',
  birth_date: '',
  sex: '',
  cpf: '',
  instagram: '',
}

export function toBasicDataPayload(values: BasicDataValues) {
  return {
    name: values.name,
    phone: emptyToNull(values.phone),
    phone_is_whatsapp: values.phone ? values.phone_is_whatsapp : null,
    email: emptyToNull(values.email),
    birth_date: emptyToNull(values.birth_date),
    sex: values.sex === '' ? null : values.sex,
    cpf: emptyToNull(values.cpf),
    instagram: emptyToNull(values.instagram),
  }
}

// ---------- Endereço ----------
export const addressSchema = z.object({
  zip_code: z
    .string()
    .trim()
    .regex(/^(\d{8})?$/, { error: 'O CEP tem 8 números.' }),
  street: text(160),
  number: text(20),
  complement: text(120),
  neighborhood: text(120),
  city: text(120),
  state: z
    .string()
    .trim()
    .regex(/^([A-Za-z]{2})?$/, { error: 'Use a sigla, ex.: GO.' }),
})

export type AddressValues = z.infer<typeof addressSchema>

export const emptyAddress: AddressValues = {
  zip_code: '',
  street: '',
  number: '',
  complement: '',
  neighborhood: '',
  city: '',
  state: '',
}

export function toAddressPayload(values: AddressValues) {
  return {
    zip_code: emptyToNull(values.zip_code),
    street: emptyToNull(values.street),
    number: emptyToNull(values.number),
    complement: emptyToNull(values.complement),
    neighborhood: emptyToNull(values.neighborhood),
    city: emptyToNull(values.city),
    state: values.state ? values.state.toUpperCase() : null,
  }
}

// Algum campo de endereço foi preenchido?
export function hasAddress(values: AddressValues) {
  return Object.values(values).some((value) => value.trim() !== '')
}

// ---------- Responsável (outra pessoa; "o próprio aluno" não grava nada) ----------
export const responsibleSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, { error: 'O nome precisa de pelo menos 2 letras.' })
    .max(120, { error: 'Até 120 caracteres.' }),
  phone: z
    .string()
    .transform((value) => value.replace(/\D/g, ''))
    .pipe(
      z
        .string()
        .min(10, { error: 'Telefone com DDD: pelo menos 10 números.' })
        .max(20, { error: 'Até 20 números.' }),
    ),
  phone_is_whatsapp: z.boolean(),
  email: text(255).refine(
    (value) => value === '' || z.email().safeParse(value).success,
    { error: 'E-mail inválido.' },
  ),
  relationship: z.enum([
    'father',
    'mother',
    'grandmother',
    'grandfather',
    'uncle',
    'aunt',
    'brother',
    'sister',
  ]),
})

export type ResponsibleInput = z.input<typeof responsibleSchema>
export type ResponsibleValues = z.output<typeof responsibleSchema>

export const emptyResponsible: ResponsibleInput = {
  name: '',
  phone: '',
  phone_is_whatsapp: false,
  email: '',
  relationship: 'mother',
}

export function toResponsiblePayload(values: ResponsibleValues) {
  return { ...values, email: emptyToNull(values.email) }
}

// ---------- Matrícula ----------
export const enrollmentSchema = z
  .object({
    modality_id: z.string().min(1, { error: 'Escolha a modalidade.' }),
    status: z.enum(['active', 'inactive']),
    is_exempt: z.boolean(),
    monthly_fee: z.string(),
    due_day: z.string(),
  })
  // .check: validações que dependem de mais de um campo (isenta desliga as outras)
  .check((context) => {
    const values = context.value
    if (values.is_exempt) return

    if (values.monthly_fee.trim() && parseMoney(values.monthly_fee) === null) {
      context.issues.push({
        code: 'custom',
        path: ['monthly_fee'],
        message: 'Valor inválido. Use o formato 150,00.',
        input: values.monthly_fee,
      })
    }

    const day = values.due_day.trim()
    if (day && !(/^\d+$/.test(day) && Number(day) >= 1 && Number(day) <= 28)) {
      context.issues.push({
        code: 'custom',
        path: ['due_day'],
        message: 'O vencimento vai de 1 a 28.',
        input: values.due_day,
      })
    }
  })

export type EnrollmentValues = z.infer<typeof enrollmentSchema>

export function emptyEnrollment(modalityId = ''): EnrollmentValues {
  return {
    modality_id: modalityId,
    status: 'active',
    is_exempt: false,
    monthly_fee: '',
    due_day: '',
  }
}

export function toEnrollmentPayload(values: EnrollmentValues) {
  const exempt = values.is_exempt

  return {
    monthly_fee:
      exempt || !values.monthly_fee.trim()
        ? null
        : parseMoney(values.monthly_fee),
    due_day: exempt || !values.due_day.trim() ? null : Number(values.due_day),
    is_exempt: exempt,
    status: values.status,
  }
}
