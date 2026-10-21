import { Plus, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Outlet, useMatch, useSearchParams } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAcademyModalities } from '@/features/modalities/hooks'
import { PAGE_SIZE } from '@/features/students/api'
import type { StudentFilters } from '@/features/students/api'
import { StudentListItem } from '@/features/students/components/StudentListItem'
import { useStudents } from '@/features/students/hooks'
import { useDebouncedValue } from '@/lib/hooks/useDebouncedValue'
import { cn } from '@/lib/utils'

const ALL_MODALITIES = 'todas'

// Filtros vivem na URL (?busca=&status=&modalidade=&pagina=): recarregar a
// página ou compartilhar o link mantém a mesma lista.
function readFilters(params: URLSearchParams): StudentFilters {
  const page = Number(params.get('pagina'))

  return {
    search: params.get('busca') ?? '',
    status: params.get('status') === 'inativos' ? 'inactive' : 'active',
    modalityId: params.get('modalidade'),
    // "abc", "0" ou vazio viram a página 1
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  }
}

// Tela mestre-detalhe: lista à esquerda + ficha (rota filha) à direita.
export function StudentsPage() {
  const [params, setParams] = useSearchParams()
  const filters = readFilters(params)
  const students = useStudents(filters)
  const { offered } = useAcademyModalities()

  // O campo de busca muda na hora; a URL (e a consulta) só 300 ms depois
  const [searchText, setSearchText] = useState(filters.search)
  const debouncedSearch = useDebouncedValue(searchText)

  // Há um aluno aberto? (no celular, a lista some e a ficha ocupa a tela)
  const hasSelection = useMatch('/app/alunos/:studentId') !== null

  // Muda um filtro na URL; qualquer filtro novo volta para a página 1
  function updateParams(changes: Record<string, string | null>) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const [name, value] of Object.entries(changes)) {
          if (value) next.set(name, value)
          else next.delete(name)
        }
        if (!('pagina' in changes)) next.delete('pagina')
        return next
      },
      { replace: true },
    )
  }

  useEffect(() => {
    if (debouncedSearch.trim() !== filters.search.trim()) {
      updateParams({ busca: debouncedSearch.trim() || null })
    }
    // Só reage à busca já "parada"; o resto dos filtros vem da URL
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  function clearFilters() {
    setSearchText('')
    updateParams({ busca: null, modalidade: null })
  }

  const page = students.data
  const totalPages = page ? Math.max(1, Math.ceil(page.total / PAGE_SIZE)) : 1
  const hasFilter = Boolean(filters.search || filters.modalityId)

  return (
    <div>
      <PageHeader
        title="Alunos"
        actions={
          <Button asChild className="rounded-full">
            <Link to="/app/alunos/novo">
              <Plus /> <span className="hidden sm:inline">Novo aluno</span>
            </Link>
          </Button>
        }
      />

      <div className="flex gap-4">
        <section
          className={cn(
            'w-full shrink-0 space-y-2 rounded-3xl bg-card p-3 md:w-80',
            hasSelection && 'hidden md:block',
          )}
        >
          <div className="relative">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Buscar aluno"
              aria-label="Buscar aluno"
              className="rounded-full pl-9"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {(['active', 'inactive'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() =>
                  updateParams({
                    status: option === 'inactive' ? 'inativos' : null,
                  })
                }
                className={cn(
                  'rounded-full border px-3 py-1 text-xs',
                  filters.status === option
                    ? 'border-chip-active-border bg-chip-active text-chip-active-foreground'
                    : 'text-muted-foreground',
                )}
              >
                {option === 'active' ? 'Ativos' : 'Inativos'}
              </button>
            ))}

            <Select
              value={filters.modalityId ?? ALL_MODALITIES}
              onValueChange={(value) =>
                updateParams({
                  modalidade: value === ALL_MODALITIES ? null : value,
                })
              }
            >
              <SelectTrigger size="sm" className="h-7 rounded-full text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_MODALITIES}>
                  Todas as modalidades
                </SelectItem>
                {offered.map((modality) => (
                  <SelectItem key={modality.id} value={modality.id}>
                    {modality.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <StudentsList
            filters={filters}
            hasFilter={hasFilter}
            state={students}
            onClearFilters={clearFilters}
          />

          {page && page.total > 0 && (
            <div className="flex items-center justify-between gap-2 pt-1 text-xs text-muted-foreground">
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                disabled={filters.page <= 1}
                onClick={() => updateParams({ pagina: String(filters.page - 1) })}
              >
                Anterior
              </Button>
              <span>
                Página {Math.min(filters.page, totalPages)} de {totalPages} ·{' '}
                {page.total} {page.total === 1 ? 'aluno' : 'alunos'}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                disabled={filters.page >= totalPages}
                onClick={() => updateParams({ pagina: String(filters.page + 1) })}
              >
                Próxima
              </Button>
            </div>
          )}
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

type StudentsListProps = {
  filters: StudentFilters
  hasFilter: boolean
  state: ReturnType<typeof useStudents>
  onClearFilters: () => void
}

// Conteúdo da lista: carregando, erro, vazio ou os alunos
function StudentsList({
  filters,
  hasFilter,
  state,
  onClearFilters,
}: StudentsListProps) {
  const { data, isLoading, error, refetch } = state

  if (error) {
    return (
      <div className="space-y-3 p-4 text-center text-sm">
        <p role="alert" className="text-destructive">
          Não foi possível carregar os alunos.
        </p>
        <Button variant="outline" className="rounded-full" onClick={refetch}>
          Tentar de novo
        </Button>
      </div>
    )
  }

  if (!data) {
    // Primeira carga: linhas "fantasma" no lugar dos alunos
    return (
      <div className="space-y-1" aria-busy>
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="flex items-center gap-3 p-2">
            <div className="size-9 rounded-full bg-muted" />
            <div className="h-3 flex-1 rounded-full bg-muted" />
          </div>
        ))}
      </div>
    )
  }

  if (data.items.length === 0) {
    return (
      <div className="space-y-2 p-4 text-center text-sm">
        {hasFilter ? (
          <>
            <p className="font-medium">Nenhum aluno encontrado</p>
            <p className="text-xs text-muted-foreground">
              Tente outra busca ou limpe os filtros.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="rounded-full"
              onClick={onClearFilters}
            >
              Limpar filtros
            </Button>
          </>
        ) : filters.page > 1 ? (
          <p className="text-muted-foreground">Esta página não tem alunos.</p>
        ) : filters.status === 'inactive' ? (
          <p className="text-muted-foreground">Nenhum aluno inativo.</p>
        ) : (
          <>
            <p className="font-medium">Nenhum aluno ainda</p>
            <Button asChild size="sm" className="rounded-full">
              <Link to="/app/alunos/novo">
                <Plus /> Novo aluno
              </Link>
            </Button>
          </>
        )}
      </div>
    )
  }

  return (
    // Enquanto busca a próxima página/filtro, a lista atual fica esmaecida
    <div className={cn('space-y-1', isLoading && 'opacity-60')}>
      {data.items.map((student) => (
        <StudentListItem key={student.id} student={student} />
      ))}
    </div>
  )
}
