import type { StudentDetail } from '@/features/students/api'
import { EnrollmentCard } from '@/features/students/components/EnrollmentCard'

export type StudentTabProps = {
  student: StudentDetail
  // Chamado depois de salvar algo: a ficha busca os dados de novo
  onChanged: () => void
}

export function EnrollmentsTab({ student }: StudentTabProps) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {student.enrollments.map((enrollment) => (
        <EnrollmentCard key={enrollment.id} enrollment={enrollment} />
      ))}
    </div>
  )
}
