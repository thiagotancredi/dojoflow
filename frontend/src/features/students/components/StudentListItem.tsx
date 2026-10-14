import { NavLink } from 'react-router'

import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import type { Student } from '@/features/students/types'
import { cn } from '@/lib/utils'

type StudentListItemProps = {
  student: Student
}

export function StudentListItem({ student }: StudentListItemProps) {
  const activeModalities = student.enrollments
    .filter((enrollment) => enrollment.status === 'active')
    .map((enrollment) => enrollment.modalityName)
    .join(' · ')

  return (
    // Clicar muda a URL para /app/alunos/<id>; o roteador então desenha a
    // ficha no <Outlet /> da StudentsPage.
    <NavLink
      to={`/app/alunos/${student.id}`}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-2xl p-2 transition-colors hover:bg-accent',
          isActive && 'bg-accent',
        )
      }
    >
      <StudentAvatar name={student.name} />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{student.name}</p>
        <p className="truncate text-xs text-muted-foreground">
          {activeModalities || 'Sem matrícula ativa'}
        </p>
      </div>
    </NavLink>
  )
}
