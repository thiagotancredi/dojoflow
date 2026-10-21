import { Plus, Search, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useOutletContext } from 'react-router'

import { Button } from '@/components/ui/button'
import type { StudentsOutletContext } from '@/features/students/pages/StudentsPage'

// Lado direito quando nenhum aluno está aberto (/app/alunos). No computador
// o primeiro aluno abre sozinho; isto aparece só quando a lista está vazia
// ou ainda carregando.
export function StudentsEmptyDetail() {
  const { listState } = useOutletContext<StudentsOutletContext>()

  if (listState === 'no-results') {
    return (
      <EmptyPanel icon={<Search className="mx-auto size-8" strokeWidth={1.4} />}>
        <p className="font-medium text-foreground">Nenhum aluno com esses filtros</p>
        <p className="text-sm">Mude a busca ou limpe os filtros.</p>
      </EmptyPanel>
    )
  }

  if (listState === 'empty') {
    return (
      <EmptyPanel icon={<Users className="mx-auto size-8" strokeWidth={1.4} />}>
        <p className="font-medium text-foreground">Nenhum aluno ainda</p>
        <p className="text-sm">Cadastre o primeiro para começar.</p>
        <Button asChild className="mt-2 rounded-full">
          <Link to="/app/alunos/novo">
            <Plus /> Cadastrar primeiro aluno
          </Link>
        </Button>
      </EmptyPanel>
    )
  }

  return (
    <EmptyPanel icon={<Users className="mx-auto size-8" strokeWidth={1.4} />}>
      <p className="text-sm">Selecione um aluno para ver a ficha.</p>
    </EmptyPanel>
  )
}

function EmptyPanel({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="grid h-full min-h-80 place-items-center rounded-3xl bg-card p-8 text-center text-muted-foreground">
      <div className="space-y-2">
        {icon}
        {children}
      </div>
    </div>
  )
}
