// Dados fictícios do dashboard. Inadimplentes e vencimentos dependem do
// backend de pagamentos (V2); o resto virá de GET /api/v1/dashboard/summary.

export type LabelCount = { label: string; count: number }

export type OverdueStudent = {
  id: string
  name: string
  modality: string
  amount: string
  daysLate: number
}

export type DueSoonStudent = {
  id: string
  name: string
  modality: string
  amount: string
  dueDate: string
}

export type Birthday = {
  id: string
  name: string
  day: number
  turningAge: number
}

// Novas matrículas por mês e por modalidade, últimos 12 meses (do mais
// antigo para o mais recente). O "geral" é a soma das modalidades.
export type MonthlyEnrollments = {
  month: string
  byModality: Record<string, number>
}

export const enrollmentsByMonth: MonthlyEnrollments[] = [
  { month: 'nov', byModality: { 'Jiu-jitsu': 2, 'Muay thai': 1, 'Judô': 0, 'Karatê': 0 } },
  { month: 'dez', byModality: { 'Jiu-jitsu': 1, 'Muay thai': 0, 'Judô': 0, 'Karatê': 0 } },
  { month: 'jan', byModality: { 'Jiu-jitsu': 3, 'Muay thai': 2, 'Judô': 1, 'Karatê': 0 } },
  { month: 'fev', byModality: { 'Jiu-jitsu': 4, 'Muay thai': 2, 'Judô': 2, 'Karatê': 1 } },
  { month: 'mar', byModality: { 'Jiu-jitsu': 3, 'Muay thai': 1, 'Judô': 2, 'Karatê': 1 } },
  { month: 'abr', byModality: { 'Jiu-jitsu': 1, 'Muay thai': 2, 'Judô': 1, 'Karatê': 0 } },
  { month: 'mai', byModality: { 'Jiu-jitsu': 2, 'Muay thai': 1, 'Judô': 1, 'Karatê': 1 } },
  { month: 'jun', byModality: { 'Jiu-jitsu': 1, 'Muay thai': 1, 'Judô': 0, 'Karatê': 1 } },
  { month: 'jul', byModality: { 'Jiu-jitsu': 4, 'Muay thai': 2, 'Judô': 1, 'Karatê': 1 } },
  { month: 'ago', byModality: { 'Jiu-jitsu': 2, 'Muay thai': 2, 'Judô': 2, 'Karatê': 0 } },
  { month: 'set', byModality: { 'Jiu-jitsu': 1, 'Muay thai': 1, 'Judô': 1, 'Karatê': 1 } },
  { month: 'out', byModality: { 'Jiu-jitsu': 2, 'Muay thai': 1, 'Judô': 1, 'Karatê': 1 } },
]

export const studentsByModality: LabelCount[] = [
  { label: 'Jiu-jitsu', count: 24 },
  { label: 'Muay thai', count: 15 },
  { label: 'Judô', count: 11 },
  { label: 'Karatê', count: 6 },
]

export const ageGroups: LabelCount[] = [
  { label: 'Kids (até 12)', count: 14 },
  { label: 'Juvenil (13–17)', count: 9 },
  { label: 'Adulto (18–39)', count: 25 },
  { label: 'Master (40+)', count: 8 },
]

export const overdueStudents: OverdueStudent[] = [
  { id: 'bruno-souza', name: 'Bruno Souza', modality: 'Muay thai', amount: '130,00', daysLate: 18 },
  { id: 'carla-mendes', name: 'Carla Mendes', modality: 'Jiu-jitsu', amount: '150,00', daysLate: 9 },
  { id: 'elisa-freitas', name: 'Elisa Freitas', modality: 'Karatê', amount: '120,00', daysLate: 3 },
]

export const dueSoonStudents: DueSoonStudent[] = [
  { id: 'ana-lima', name: 'Ana Lima', modality: 'Jiu-jitsu', amount: '150,00', dueDate: '16/10' },
  { id: 'davi-rocha', name: 'Davi Rocha', modality: 'Judô', amount: '100,00', dueDate: '18/10' },
  { id: 'felipe-costa', name: 'Felipe Costa', modality: 'Muay thai', amount: '130,00', dueDate: '20/10' },
  { id: 'gabi-nunes', name: 'Gabi Nunes', modality: 'Jiu-jitsu', amount: '150,00', dueDate: '20/10' },
]

export const birthdaysThisMonth: Birthday[] = [
  { id: 'davi-rocha', name: 'Davi Rocha', day: 9, turningAge: 11 },
  { id: 'ana-lima', name: 'Ana Lima', day: 22, turningAge: 27 },
  { id: 'helena-dias', name: 'Helena Dias', day: 30, turningAge: 15 },
]

export const activeStudents = 56
