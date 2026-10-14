import type { Student } from '@/features/students/types'

// Dados fictícios só para enxergar as telas. Somem quando ligarmos a API.
export const mockStudents: Student[] = [
  {
    id: 'ana-lima',
    name: 'Ana Lima',
    phone: '(62) 99999-0001',
    phoneIsWhatsapp: true,
    email: 'ana@email.com',
    enrollments: [
      { id: 'e1', modalityName: 'Jiu-jitsu', status: 'active', monthlyFee: '150,00', dueDay: 10, isExempt: false },
      { id: 'e2', modalityName: 'Judô', status: 'active', monthlyFee: null, dueDay: null, isExempt: true },
      { id: 'e3', modalityName: 'Muay thai', status: 'active', monthlyFee: null, dueDay: null, isExempt: false },
      { id: 'e4', modalityName: 'Karatê', status: 'inactive', monthlyFee: '120,00', dueDay: 5, isExempt: false },
    ],
    responsibles: [],
    address: {
      street: 'Rua A',
      number: '10',
      neighborhood: 'Centro',
      city: 'Goiânia',
      state: 'GO',
      zipCode: '74000-000',
    },
  },
  {
    id: 'bruno-souza',
    name: 'Bruno Souza',
    phone: '(62) 99999-0002',
    phoneIsWhatsapp: false,
    email: null,
    enrollments: [
      { id: 'e5', modalityName: 'Muay thai', status: 'active', monthlyFee: '130,00', dueDay: 15, isExempt: false },
    ],
    responsibles: [],
    address: null,
  },
  {
    id: 'davi-rocha',
    name: 'Davi Rocha',
    phone: null,
    phoneIsWhatsapp: false,
    email: null,
    enrollments: [
      { id: 'e6', modalityName: 'Judô', status: 'active', monthlyFee: '100,00', dueDay: 20, isExempt: false },
    ],
    responsibles: [
      { id: 'r1', name: 'Paula Rocha', phone: '(62) 99999-0003', relationship: 'Mãe' },
    ],
    address: null,
  },
  {
    id: 'elisa-freitas',
    name: 'Elisa Freitas',
    phone: '(62) 99999-0004',
    phoneIsWhatsapp: true,
    email: 'elisa@email.com',
    enrollments: [
      { id: 'e7', modalityName: 'Karatê', status: 'inactive', monthlyFee: '120,00', dueDay: 5, isExempt: false },
    ],
    responsibles: [],
    address: null,
  },
]
