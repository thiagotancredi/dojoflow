import { Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { Outlet, useMatch } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StudentListItem } from '@/features/students/components/StudentListItem'
import { mockStudents } from '@/features/students/mock-data'
import { cn } from '@/lib/utils'

type StatusFilter = 'active' | 'inactive'

// Tela mestre-detalhe: lista à esquerda + ficha (rota filha) à direita.
export function StudentsPage() {
  // Estado local: o que foi digitado na busca e o filtro escolhido.
  // Cada setX(...) faz o React chamar esta função de novo e redesenhar.
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<StatusFilter>('active')

  // Há um aluno aberto? (no celular, a lista some e a ficha ocupa a tela)
  const hasSelection = useMatch('/app/alunos/:studentId') !== null

  const visibleStudents = mockStudents.filter((student) => {
    const matchesSearch = student.name
      .toLowerCase()
      .includes(search.trim().toLowerCase())
    const hasActive = student.enrollments.some(
      (enrollment) => enrollment.status === 'active',
    )
    const matchesStatus = status === 'active' ? hasActive : !hasActive

    return matchesSearch && matchesStatus
  })

  return (
    <div>
      <PageHeader
        title="Alunos"
        actions={
          <Button className="rounded-full">
            <Plus /> <span className="hidden sm:inline">Novo aluno</span>
          </Button>
        }
      />

      <div className="flex gap-4">
        <section
          className={cn(
            'w-full shrink-0 space-y-2 rounded-3xl bg-card p-3 md:w-72',
            hasSelection && 'hidden md:block',
          )}
        >
          <div className="relative">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar aluno"
              className="rounded-full pl-9"
            />
          </div>

          <div className="flex gap-1.5">
            {(['active', 'inactive'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setStatus(option)}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs',
                  status === option
                    ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                    : 'text-muted-foreground',
                )}
              >
                {option === 'active' ? 'Ativos' : 'Inativos'}
              </button>
            ))}
          </div>

          <div className="space-y-1">
            {visibleStudents.map((student) => (
              <StudentListItem key={student.id} student={student} />
            ))}
            {visibleStudents.length === 0 && (
              <p className="p-4 text-center text-sm text-muted-foreground">
                Nenhum aluno encontrado.
              </p>
            )}
          </div>
        </section>

        <section
          className={cn('min-w-0 flex-1', !hasSelection && 'hidden md:block')}
        >
          <Outlet />
        </section>
      </div>
    </div>
  )
}
