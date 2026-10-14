import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { StudentAvatar } from '@/features/students/components/StudentAvatar'

type StudentRowProps = {
  studentId: string
  name: string
  detail: string
  // Lado direito da linha: valor, status, data… quem usa decide
  trailing: ReactNode
}

// Linha de aluno clicável, usada nas listas do dashboard. Abre a ficha.
export function StudentRow({ studentId, name, detail, trailing }: StudentRowProps) {
  return (
    <li>
      <Link
        to={`/app/alunos/${studentId}`}
        className="flex items-center gap-3 rounded-2xl p-2 hover:bg-accent"
      >
        <StudentAvatar name={name} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{name}</p>
          <p className="truncate text-xs text-muted-foreground">{detail}</p>
        </div>
        <div className="shrink-0 text-right">{trailing}</div>
      </Link>
    </li>
  )
}
