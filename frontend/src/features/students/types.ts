// Formato provisório, espelhando a resposta da API (StudentDetailRead).
// Na Fase 3 estes tipos passam a ser gerados do OpenAPI do backend.

export type EnrollmentStatus = 'active' | 'inactive'

export type Enrollment = {
  id: string
  modalityName: string
  status: EnrollmentStatus
  monthlyFee: string | null
  dueDay: number | null
  isExempt: boolean
}

export type Responsible = {
  id: string
  name: string
  phone: string
  relationship: string
}

export type Address = {
  street: string
  number: string
  neighborhood: string
  city: string
  state: string
  zipCode: string
}

export type Student = {
  id: string
  name: string
  phone: string | null
  phoneIsWhatsapp: boolean
  email: string | null
  enrollments: Enrollment[]
  responsibles: Responsible[]
  address: Address | null
}
