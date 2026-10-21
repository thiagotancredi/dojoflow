import { useSyncExternalStore } from 'react'

import type { BeltLook } from '@/features/belts/components/BeltDrawing'
import { toIsoDate } from '@/features/belts/rules'

// ⚠️ DADOS DE EXEMPLO (decisão do Thiago em 20/10): as telas de aluno já
// mostram a faixa, mas os valores são fictícios e ficam só na memória do
// navegador. Este arquivo sai quando o plano das faixas integrar a API
// (/academy/modalities/{id}/belts e /students/.../belts).

export type MockBelt = BeltLook & { minMonths: number | null }
export type BeltRecord = { belt: string; graduatedOn: string }

const GOLD = '#d4a017'

function belt(
  name: string,
  primaryColor: string,
  minMonths: number | null,
  options: Partial<BeltLook> = {},
): MockBelt {
  return {
    name,
    primary_color: primaryColor,
    stripe_color: null,
    marks: 0,
    marks_color: GOLD,
    tip_color: null,
    minMonths,
    ...options,
  }
}

// Sequências por nome da modalidade (as cores do protótipo aprovado)
const SEQUENCES: Record<string, MockBelt[]> = {
  taekwondo: [
    belt('Branca', '#f8fafc', 3),
    belt('Amarela', '#facc15', 3),
    belt('Laranja', '#f97316', 3),
    belt('Verde', '#16a34a', 3),
    belt('Azul', '#1d4ed8', 3),
    belt('Vermelha', '#dc2626', 6),
    belt('Preta 1º Dan', '#111827', 12, { marks: 1 }),
  ],
  'jiu-jitsu': [
    belt('Branca', '#f8fafc', 12),
    belt('Azul', '#1d4ed8', 24),
    belt('Roxa', '#7c3aed', 24),
    belt('Marrom', '#78350f', 18),
    belt('Preta', '#111827', null),
  ],
}

export function mockBeltsFor(modalityName: string): MockBelt[] {
  return SEQUENCES[modalityName.trim().toLowerCase()] ?? []
}

export function findMockBelt(modalityName: string, beltName: string) {
  return mockBeltsFor(modalityName).find((item) => item.name === beltName)
}

// Próxima faixa da sequência (sem faixa → a primeira; última → ela mesma)
export function nextMockBelt(modalityName: string, current: string | null) {
  const belts = mockBeltsFor(modalityName)
  if (!current) return belts[0]?.name ?? null
  const index = belts.findIndex((item) => item.name === current)
  return belts[Math.min(index + 1, belts.length - 1)]?.name ?? null
}

// ---------- Histórico em memória, por aluno × modalidade ----------
const history = new Map<string, BeltRecord[]>()
const listeners = new Set<() => void>()
const EMPTY: BeltRecord[] = []

const keyOf = (studentId: string, modalityId: string) =>
  `${studentId}:${modalityId}`

// Valor de exemplo estável para quem ainda não tem nada: a faixa e a data
// saem do id (o mesmo aluno mostra sempre a mesma faixa)
function seed(studentId: string, modalityId: string, modalityName: string) {
  const belts = mockBeltsFor(modalityName)
  if (belts.length === 0) return EMPTY

  const hash = [...keyOf(studentId, modalityId)].reduce(
    (total, char) => (total * 31 + char.charCodeAt(0)) % 100_000,
    7,
  )
  const date = new Date()
  date.setDate(date.getDate() - (hash % 240) - 10)

  return [
    { belt: belts[hash % Math.min(belts.length, 4)].name, graduatedOn: toIsoDate(date) },
  ]
}

function emit() {
  for (const listener of listeners) listener()
}

function read(studentId: string, modalityId: string, modalityName: string) {
  const key = keyOf(studentId, modalityId)
  if (!history.has(key)) history.set(key, seed(studentId, modalityId, modalityName))
  return history.get(key) ?? EMPTY
}

export function addMockGraduation(
  studentId: string,
  modalityId: string,
  record: BeltRecord,
) {
  const key = keyOf(studentId, modalityId)
  history.set(key, [...(history.get(key) ?? []), record])
  emit()
}

// Matrícula nova com "Faixa atual" escolhida (ou nenhuma)
export function setMockCurrentBelt(
  studentId: string,
  modalityId: string,
  record: BeltRecord | null,
) {
  history.set(keyOf(studentId, modalityId), record ? [record] : EMPTY)
  emit()
}

// Histórico do aluno na modalidade, mais recente primeiro; a tela
// redesenha sozinha quando uma graduação é registrada
export function useMockBeltHistory(
  studentId: string,
  modalityId: string,
  modalityName: string,
) {
  const records = useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => read(studentId, modalityId, modalityName),
  )

  return [...records].sort((a, b) => b.graduatedOn.localeCompare(a.graduatedOn))
}
