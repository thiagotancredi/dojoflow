import { ArrowLeft, Pencil, Phone } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EnrollmentCard } from '@/features/students/components/EnrollmentCard'
import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import { mockStudents } from '@/features/students/mock-data'

// Ficha do aluno: lê o ":studentId" da URL (/app/alunos/ana-lima).
export function StudentDetailPage() {
  const { studentId } = useParams()
  const student = mockStudents.find((item) => item.id === studentId)

  if (!student) {
    return (
      <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
        Aluno não encontrado.
      </div>
    )
  }

  return (
    <article className="space-y-4 rounded-3xl bg-card p-5">
      {/* "Voltar" só no celular, onde a lista está escondida */}
      <Link
        to="/app/alunos"
        className="flex items-center gap-1 text-sm text-muted-foreground md:hidden"
      >
        <ArrowLeft className="size-4" /> Alunos
      </Link>

      <div className="flex items-center gap-3">
        <StudentAvatar size="lg" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-semibold">{student.name}</h2>
          {student.phone && (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Phone className="size-3.5" />
              {student.phone}
              {student.phoneIsWhatsapp && ' · WhatsApp'}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" className="rounded-full">
          <Pencil /> Editar
        </Button>
      </div>

      <Tabs defaultValue="enrollments">
        <TabsList variant="line">
          <TabsTrigger value="enrollments">Matrículas</TabsTrigger>
          <TabsTrigger value="data">Dados</TabsTrigger>
          <TabsTrigger value="address">Endereço</TabsTrigger>
          <TabsTrigger value="responsibles">Responsáveis</TabsTrigger>
        </TabsList>

        <TabsContent value="enrollments">
          <div className="grid gap-2.5 sm:grid-cols-2">
            {student.enrollments.map((enrollment) => (
              <EnrollmentCard key={enrollment.id} enrollment={enrollment} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="data" className="space-y-1 text-sm">
          <p>Telefone: {student.phone ?? '—'}</p>
          <p>E-mail: {student.email ?? '—'}</p>
        </TabsContent>

        <TabsContent value="address" className="text-sm">
          {student.address
            ? `${student.address.street}, ${student.address.number} — ${student.address.neighborhood}, ${student.address.city}/${student.address.state}`
            : 'Sem endereço cadastrado.'}
        </TabsContent>

        <TabsContent value="responsibles" className="space-y-1 text-sm">
          {student.responsibles.length === 0
            ? 'Nenhum responsável.'
            : student.responsibles.map((responsible) => (
                <p key={responsible.id}>
                  {responsible.name} ({responsible.relationship}) ·{' '}
                  {responsible.phone}
                </p>
              ))}
        </TabsContent>
      </Tabs>
    </article>
  )
}
