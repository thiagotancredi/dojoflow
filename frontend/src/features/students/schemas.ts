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
    // Taxa de matrícula: só aparece (e só vale) ao criar a matrícula
    enrollment_fee: z.string(),
    waive_enrollment_fee: z.boolean(),
  })
  // .check: validações que dependem de mais de um campo (isenta desliga as outras)
  .check((context) => {
    const values = context.value
    const issue = (path: keyof EnrollmentValues, message: string) =>
      context.issues.push({
        code: 'custom',
        path: [path],
        message,
        input: values[path],
      })

    // Igual ao backend: ativa e não isenta precisa de valor e dia.
    // Inativa pode ficar sem (matrícula antiga que só vai ser encerrada).
    const needsBilling = !values.is_exempt && values.status === 'active'

    if (!values.is_exempt) {
      const fee = values.monthly_fee.trim()
      const parsed = fee ? parseMoney(fee) : null

      if (fee && parsed === null) {
        issue('monthly_fee', 'Valor inválido. Use o formato 150,00.')
      } else if (needsBilling && !fee) {
        issue('monthly_fee', 'Informe o valor da mensalidade.')
      } else if (needsBilling && Number(parsed) <= 0) {
        issue('monthly_fee', 'A mensalidade precisa ser maior que zero (ou marque Isenta).')
      }

      const day = values.due_day.trim()
      if (day && !(/^\d+$/.test(day) && Number(day) >= 1 && Number(day) <= 28)) {
        issue('due_day', 'O vencimento vai de 1 a 28.')
      } else if (needsBilling && !day) {
        issue('due_day', 'Informe o dia de vencimento.')
      }
    }

    if (!values.waive_enrollment_fee) {
      const fee = values.enrollment_fee.trim()
      if (!fee) {
        issue('enrollment_fee', 'Informe a taxa de matrícula (ou marque Isentar taxa).')
      } else if (parseMoney(fee) === null) {
        issue('enrollment_fee', 'Valor inválido. Use o formato 80,00.')
      }
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
    enrollment_fee: '',
    waive_enrollment_fee: false,
  }
}

// Edição: a taxa já foi lançada na criação, então o campo fica "isento"
// só para não pedir nada (ele nem aparece e não é enviado)
export const NO_ENROLLMENT_FEE = {
  enrollment_fee: '',
  waive_enrollment_fee: true,
} as const

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

// Matrícula nova: o mesmo de cima + a taxa ("Isentar taxa" envia 0)
export function toNewEnrollmentPayload(values: EnrollmentValues) {
  return {
    ...toEnrollmentPayload(values),
    enrollment_fee: values.waive_enrollment_fee
      ? '0.00'
      : parseMoney(values.enrollment_fee),
  }
}
