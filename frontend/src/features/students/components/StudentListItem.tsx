import { NavLink, useLocation } from 'react-router'

import type { StudentSummary } from '@/features/students/api'
import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import { cn } from '@/lib/utils'

type StudentListItemProps = {
  student: StudentSummary
}

export function StudentListItem({ student }: StudentListItemProps) {
  // Mantém os filtros (?busca=...) ao abrir a ficha
  const { search } = useLocation()

  return (
    // Clicar muda a URL para /app/alunos/<id>; o roteador então desenha a
    // ficha no <Outlet /> da StudentsPage.
    <NavLink
      to={`/app/alunos/${student.id}${search}`}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-2xl p-2 transition-colors hover:bg-accent',
          isActive && 'bg-accent',
        )
      }
    >
      <StudentAvatar />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{student.name}</p>
        <p className="truncate text-xs text-muted-foreground">
          {student.modalities.join(' · ') || 'Sem matrícula ativa'}
        </p>
      </div>
    </NavLink>
  )
}
