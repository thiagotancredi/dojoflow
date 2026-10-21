import { ArrowLeft, Phone } from 'lucide-react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StudentBillingTab } from '@/features/billing/components/StudentBillingTab'
import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import { AddressTab } from '@/features/students/components/tabs/AddressTab'
import { BasicDataTab } from '@/features/students/components/tabs/BasicDataTab'
import { EnrollmentsTab } from '@/features/students/components/tabs/EnrollmentsTab'
import { ResponsiblesTab } from '@/features/students/components/tabs/ResponsiblesTab'
import { useStudent } from '@/features/students/hooks'
import { formatPhone } from '@/lib/format'

// Ficha do aluno: lê o ":studentId" da URL (/app/alunos/<uuid>).
export function StudentDetailPage() {
  const { studentId } = useParams()
  const { search } = useLocation()
  const { data, isLoading, error, refetch } = useStudent(studentId)
  const list = useOutletContext<{ refreshList: () => void } | undefined>()
  const backToList = `/app/alunos${search}`

  // Depois de salvar: atualiza a ficha e a lista ao lado
  function onChanged() {
    refetch()
    list?.refreshList()
  }

  // Só a primeira carga mostra "carregando"; recarregar depois de salvar
  // mantém a ficha (e a aba aberta) na tela
  if (isLoading && !data) {
    return (
      <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
        Carregando aluno…
      </div>
    )
  }

  if (!data && error && !isNotFound(error)) {
    // Rede fora, 500…: o aluno existe, só não deu para carregar
    return (
      <div className="space-y-3 rounded-3xl bg-card p-8 text-center text-sm">
        <p role="alert" className="text-destructive">
          Não foi possível carregar o aluno.
        </p>
        <Button variant="outline" className="rounded-full" onClick={refetch}>
          Tentar de novo
        </Button>
      </div>
    )
  }

  if (!data) {
    // UUID inválido (422) ou de outra academia (404): para o mestre, é o mesmo
    return (
      <div className="space-y-3 rounded-3xl bg-card p-8 text-center text-sm">
        <p className="font-medium">Aluno não encontrado.</p>
        <Button asChild variant="outline" className="rounded-full">
          <Link to={backToList}>Voltar para a lista</Link>
        </Button>
      </div>
    )
  }

  const { student } = data

  return (
    <article className="space-y-4 rounded-3xl bg-card p-5">
      {/* "Voltar" só no celular, onde a lista está escondida */}
      <Link
        to={backToList}
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
              {formatPhone(student.phone)}
              {student.phone_is_whatsapp && ' · WhatsApp'}
            </p>
          )}
        </div>
      </div>

      {/* key: ao trocar de aluno, as abas voltam ao estado inicial */}
      <Tabs key={student.id} defaultValue="enrollments">
        {/* 5 abas não cabem no celular: a barra rola para o lado */}
        <TabsList variant="line" className="max-w-full overflow-x-auto">
          <TabsTrigger value="enrollments">Matrículas</TabsTrigger>
          <TabsTrigger value="billing">Mensalidades</TabsTrigger>
          <TabsTrigger value="data">Dados</TabsTrigger>
          <TabsTrigger value="address">Endereço</TabsTrigger>
          <TabsTrigger value="responsibles">Responsáveis</TabsTrigger>
        </TabsList>

        <TabsContent value="enrollments" className="pt-2">
          <EnrollmentsTab student={data} onChanged={onChanged} />
        </TabsContent>
        <TabsContent value="billing" className="pt-2">
          <StudentBillingTab student={data} />
        </TabsContent>
        <TabsContent value="data" className="pt-2">
          <BasicDataTab student={data} onChanged={onChanged} />
        </TabsContent>
        <TabsContent value="address" className="pt-2">
          <AddressTab student={data} onChanged={onChanged} />
        </TabsContent>
        <TabsContent value="responsibles" className="pt-2">
          <ResponsiblesTab student={data} onChanged={onChanged} />
        </TabsContent>
      </Tabs>
    </article>
  )
}

// 404 do aluno ou id que nem é UUID (422): "não encontrado"
function isNotFound(error: unknown) {
  if (typeof error !== 'object' || error === null) return false
  if ('code' in error && error.code === 'STUDENT_NOT_FOUND') return true
  return 'detail' in error && Array.isArray(error.detail)
}
