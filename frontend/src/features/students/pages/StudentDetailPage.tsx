import { useState } from 'react'
import { ArrowLeft, MessageCircle, Phone } from 'lucide-react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { StudentBillingTab } from '@/features/billing/components/StudentBillingTab'
import { StudentAvatar } from '@/features/students/components/StudentAvatar'
import { AddressTab } from '@/features/students/components/tabs/AddressTab'
import { BasicDataTab } from '@/features/students/components/tabs/BasicDataTab'
import { EnrollmentsTab } from '@/features/students/components/tabs/EnrollmentsTab'
import { ResponsiblesTab } from '@/features/students/components/tabs/ResponsiblesTab'
import {
  STUDENT_SECTIONS,
  SectionMenuProvider,
  type StudentSection,
} from '@/features/students/components/tabs/sections'
import { TabHeader } from '@/features/students/components/tabs/TabParts'
import { useStudent } from '@/features/students/hooks'
import { formatPhone } from '@/lib/format'
import { callHref, whatsappHref } from '@/lib/phone'

// Ficha do aluno: lê o ":studentId" da URL (/app/alunos/<uuid>).
export function StudentDetailPage() {
  const { studentId } = useParams()
  const { search, state } = useLocation()
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
    // @container/ficha: as abas decidem o formato pela largura da ficha
    // (não da tela); no tablet a ficha fica estreita ao lado da lista
    <article className="@container/ficha space-y-6 rounded-3xl bg-card p-5 md:p-6">
      {/* "Voltar" só no celular, onde a lista está escondida */}
      <Link
        to={backToList}
        className="flex items-center gap-1 text-sm text-muted-foreground md:hidden"
      >
        <ArrowLeft className="size-4" /> Alunos
      </Link>

      {/* Ficha estreita (celular, tablet): tudo numa linha só. Número em
          texto embaixo do nome e Ligar/WhatsApp como botões redondos à
          direita. Ficha larga: número e WhatsApp como pílulas, como antes */}
      <div className="flex items-center gap-4 @max-xl/ficha:gap-3">
        {/* Ficha bem estreita (tablet, ao lado da lista): sem avatar, para
            sobrar espaço para o nome */}
        <div className="@max-[18rem]/ficha:hidden">
          <StudentAvatar size="lg" />
        </div>
        <div className="min-w-0 flex-1 space-y-2 @max-xl/ficha:space-y-0">
          <h2 className="truncate text-xl font-semibold tracking-tight @max-xl/ficha:text-lg">
            {student.name}
          </h2>
          {student.phone && (
            <p className="truncate text-sm whitespace-nowrap text-muted-foreground tabular-nums @xl/ficha:hidden">
              {formatPhone(student.phone)}
            </p>
          )}
          {student.phone && (
            <div className="flex flex-wrap items-center gap-2 @max-xl/ficha:hidden">
              {/* O próprio número liga (no celular; no computador abre o
                  app de chamadas, se houver) */}
              <a
                href={callHref(student.phone)}
                title="Ligar"
                className="inline-flex h-8 items-center gap-1.5 rounded-full bg-muted px-3 text-sm tabular-nums transition-colors hover:bg-accent"
              >
                <Phone className="size-3.5" />
                {formatPhone(student.phone)}
              </a>
              {/* Conversa em branco (a cobrança fica na aba Mensalidades) */}
              {student.phone_is_whatsapp && (
                <a
                  href={whatsappHref(student.phone)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-8 items-center gap-1.5 rounded-full border border-status-active/30 bg-status-active-soft px-3 text-sm font-medium text-status-active transition-colors hover:brightness-95"
                >
                  <MessageCircle className="size-3.5" />
                  WhatsApp
                </a>
              )}
            </div>
          )}
        </div>
        {student.phone && (
          <div className="flex shrink-0 gap-2 @xl/ficha:hidden">
            <a
              href={callHref(student.phone)}
              aria-label="Ligar"
              className="grid size-10 place-items-center rounded-full bg-muted transition-colors hover:bg-accent"
            >
              <Phone className="size-4" />
            </a>
            {student.phone_is_whatsapp && (
              <a
                href={whatsappHref(student.phone)}
                target="_blank"
                rel="noreferrer"
                aria-label="Abrir conversa no WhatsApp"
                className="grid size-10 place-items-center rounded-full border border-status-active/30 bg-status-active-soft text-status-active transition-colors hover:brightness-95"
              >
                <MessageCircle className="size-4" />
              </a>
            )}
          </div>
        )}
      </div>

      {/* key: ao trocar de aluno, as abas voltam ao estado inicial */}
      <StudentSections
        key={student.id}
        student={data}
        initial={initialTab(state)}
        onChanged={onChanged}
      />
    </article>
  )
}

type StudentData = NonNullable<ReturnType<typeof useStudent>['data']>

// Abas da ficha. Ficha larga: barra de abas. Ficha estreita (celular,
// tablet): a barra some e o título de cada aba vira o menu de seções
function StudentSections({
  student,
  initial,
  onChanged,
}: {
  student: StudentData
  initial: StudentSection
  onChanged: () => void
}) {
  // Aba aberta num estado nosso (e não só dentro do <Tabs>), para o menu
  // do título também conseguir trocar de aba
  const [section, setSection] = useState<StudentSection>(initial)

  return (
    <SectionMenuProvider value={{ value: section, onChange: setSection }}>
      <Tabs
        value={section}
        onValueChange={(value) => setSection(value as StudentSection)}
      >
        <TabsList className="h-auto max-w-full justify-start gap-1 rounded-full p-1 @max-xl/ficha:hidden">
          {STUDENT_SECTIONS.map(({ value, label }) => (
            <TabsTrigger
              key={value}
              value={value}
              className="rounded-full px-4 py-1.5 focus-visible:border-transparent focus-visible:ring-2 focus-visible:ring-ring/40 data-active:bg-sidebar-primary data-active:text-sidebar-primary-foreground data-active:hover:text-sidebar-primary-foreground dark:data-active:text-sidebar-primary-foreground"
            >
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* pt-0 na ficha estreita: sem a barra de abas, o título da aba
            já fica logo abaixo do cabeçalho do aluno */}
        <TabsContent value="enrollments" className="pt-4 @max-xl/ficha:pt-0">
          <EnrollmentsTab student={student} onChanged={onChanged} />
        </TabsContent>
        <TabsContent
          value="billing"
          className="space-y-4 pt-4 @max-xl/ficha:pt-0"
        >
          {/* As outras abas têm o TabHeader dentro delas; esta, aqui */}
          <TabHeader title="Mensalidades" />
          <StudentBillingTab student={student} />
        </TabsContent>
        <TabsContent value="data" className="pt-4 @max-xl/ficha:pt-0">
          <BasicDataTab student={student} onChanged={onChanged} />
        </TabsContent>
        <TabsContent value="address" className="pt-4 @max-xl/ficha:pt-0">
          <AddressTab student={student} onChanged={onChanged} />
        </TabsContent>
        <TabsContent value="responsibles" className="pt-4 @max-xl/ficha:pt-0">
          <ResponsiblesTab student={student} onChanged={onChanged} />
        </TabsContent>
      </Tabs>
    </SectionMenuProvider>
  )
}

// Aba que abre primeiro: quem vem de uma tela de cobrança pede
// "Mensalidades" (navigate/Link com state { tab: 'billing' }); o resto abre
// em "Matrículas"
function initialTab(state: unknown): StudentSection {
  const tab =
    typeof state === 'object' && state !== null && 'tab' in state
      ? state.tab
      : null
  return tab === 'billing' ? 'billing' : 'enrollments'
}

// 404 do aluno ou id que nem é UUID (422): "não encontrado"
function isNotFound(error: unknown) {
  if (typeof error !== 'object' || error === null) return false
  if ('code' in error && error.code === 'STUDENT_NOT_FOUND') return true
  return 'detail' in error && Array.isArray(error.detail)
}
