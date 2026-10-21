import {
  Ban,
  CircleCheck,
  KeyRound,
  MoreHorizontal,
  Pencil,
  Plus,
  Search,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  listAcademies,
  resetPassword,
  setAcademyStatus,
} from '@/features/admin/api'
import type { AdminAcademy, AdminCredentials } from '@/features/admin/api'
import { AcademyFormDialog } from '@/features/admin/components/AcademyFormDialog'
import { CredentialsDialog } from '@/features/admin/components/CredentialsDialog'
import { EnterAcademyButton } from '@/features/admin/components/EnterAcademyButton'
import type { Credentials } from '@/features/admin/components/CredentialsDialog'
import { showApiError } from '@/lib/api/errors'
import { formatPhone } from '@/lib/format'
import { useDebouncedValue } from '@/lib/hooks/useDebouncedValue'
import { useMutation } from '@/lib/hooks/useMutation'
import { useResource } from '@/lib/hooks/useResource'

// Ação que pede confirmação antes (trocar senha, ativar, desativar)
type PendingAction = {
  kind: 'reset' | 'block' | 'unblock'
  academy: AdminAcademy
}

function createdAt(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR')
}

function StatusChip({ status }: { status: AdminAcademy['status'] }) {
  const active = status === 'active'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        active
          ? 'bg-status-exempt-soft text-status-exempt'
          : 'bg-status-inactive-soft text-status-inactive-foreground'
      }`}
    >
      <span
        className={`size-1.5 rounded-full ${active ? 'bg-status-exempt' : 'bg-status-inactive'}`}
      />
      {active ? 'Ativa' : 'Desativada'}
    </span>
  )
}

function OwnTag() {
  return (
    <span className="mt-1 inline-flex rounded-full border border-chip-active-border bg-chip-active px-2 py-0.5 text-[11px] font-semibold text-chip-active-foreground">
      Sua academia
    </span>
  )
}

type AcademyActionsProps = {
  academy: AdminAcademy
  onEdit: (academy: AdminAcademy) => void
  onAsk: (action: PendingAction) => void
}

function AcademyMenu({ academy, onEdit, onAsk }: AcademyActionsProps) {
  const active = academy.status === 'active'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full"
          aria-label={`Mais ações de ${academy.name}`}
        >
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {/* A sua senha se troca em Configurações → Conta (aqui derrubaria
            a sua própria sessão) */}
        {!academy.is_own && (
          <DropdownMenuItem onSelect={() => onAsk({ kind: 'reset', academy })}>
            <KeyRound className="size-4" />
            Trocar senha
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onSelect={() => onEdit(academy)}>
          <Pencil className="size-4" />
          Editar dados
        </DropdownMenuItem>
        {!academy.is_own && (
          <>
            <DropdownMenuSeparator />
            {active ? (
              <DropdownMenuItem
                variant="destructive"
                onSelect={() => onAsk({ kind: 'block', academy })}
              >
                <Ban className="size-4" />
                Desativar academia
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem
                onSelect={() => onAsk({ kind: 'unblock', academy })}
              >
                <CircleCheck className="size-4" />
                Ativar academia
              </DropdownMenuItem>
            )}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

const CONFIRM_TEXT: Record<
  PendingAction['kind'],
  { title: string; body: (name: string) => string; action: string }
> = {
  reset: {
    title: 'Trocar senha',
    body: (name) =>
      `O sistema gera uma senha nova para o mestre da ${name}. Quem estiver logado com a senha antiga é desconectado.`,
    action: 'Gerar senha nova',
  },
  block: {
    title: 'Desativar academia',
    body: (name) =>
      `A ${name} deixa de entrar no sistema e quem estiver logado cai na próxima ação. Os dados ficam guardados e você pode ativar de novo depois.`,
    action: 'Desativar',
  },
  unblock: {
    title: 'Ativar academia',
    body: (name) => `A ${name} volta a entrar no sistema normalmente.`,
    action: 'Ativar',
  },
}

export function AdminAcademiesPage() {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim())
  const academies = useResource(
    `admin-academies:${debouncedSearch}`,
    (signal) => listAcademies(debouncedSearch, signal),
    { keepPrevious: true },
  )
  const [formTarget, setFormTarget] = useState<AdminAcademy | 'new' | null>(
    null,
  )
  const [credentials, setCredentials] = useState<Credentials | null>(null)
  const [pending, setPending] = useState<PendingAction | null>(null)
  const reset = useMutation(resetPassword)
  const changeStatus = useMutation(setAcademyStatus)
  const busy = reset.isPending || changeStatus.isPending

  const rows = academies.data ?? []
  const activeCount = rows.filter((row) => row.status === 'active').length

  function showCreated(result: AdminCredentials) {
    academies.refetch()
    setCredentials({
      title: 'Academia criada',
      masterName: result.academy.master?.name ?? 'o mestre',
      email: result.academy.master?.email ?? '',
      password: result.password,
    })
  }

  async function confirm() {
    if (!pending) return
    const { kind, academy } = pending

    try {
      if (kind === 'reset') {
        const { password } = await reset.mutate(academy.id)
        setCredentials({
          title: 'Senha trocada',
          masterName: academy.master?.name ?? 'o mestre',
          email: academy.master?.email ?? '',
          password,
        })
      } else {
        await changeStatus.mutate(
          academy.id,
          kind === 'block' ? 'blocked' : 'active',
        )
        toast.success(
          kind === 'block' ? 'Academia desativada' : 'Academia ativada',
        )
      }
      academies.refetch()
    } catch (error) {
      showApiError(error)
    } finally {
      setPending(null)
    }
  }

  const actions = (academy: AdminAcademy) => ({
    academy,
    onEdit: setFormTarget,
    onAsk: setPending,
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Academias</h1>
          <p className="text-sm text-muted-foreground">
            {academies.data
              ? `${rows.length} ${rows.length === 1 ? 'academia' : 'academias'} · ${activeCount} ${activeCount === 1 ? 'ativa' : 'ativas'}`
              : 'Carregando…'}
          </p>
        </div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          <div className="relative min-w-0 flex-1 sm:w-80">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar academia ou mestre"
              aria-label="Buscar academia ou mestre"
              className="h-10 rounded-xl pl-9"
            />
          </div>
          <Button
            className="h-10 rounded-full"
            onClick={() => setFormTarget('new')}
          >
            <Plus className="size-4" />
            Nova academia
          </Button>
        </div>
      </div>

      {academies.error && !academies.data ? (
        <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
          Não foi possível carregar as academias.{' '}
          <button
            type="button"
            className="font-medium text-foreground underline"
            onClick={academies.refetch}
          >
            Tentar de novo
          </button>
        </div>
      ) : academies.data && rows.length === 0 ? (
        <div className="rounded-3xl bg-card p-8 text-center text-sm text-muted-foreground">
          {debouncedSearch
            ? `Nenhuma academia encontrada para "${debouncedSearch}".`
            : 'Nenhuma academia ainda. Crie a primeira em "Nova academia".'}
        </div>
      ) : (
        <>
          {/* Computador: tabela */}
          <div className="hidden overflow-hidden rounded-3xl border bg-card md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-semibold">Academia</th>
                  <th className="px-4 py-3 font-semibold">Mestre</th>
                  <th className="px-4 py-3 font-semibold">Telefone</th>
                  <th className="px-4 py-3 font-semibold">Situação</th>
                  <th className="px-4 py-3 font-semibold">Criada em</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {rows.map((academy) => {
                  const off = academy.status !== 'active'
                  return (
                    <tr key={academy.id} className="border-b last:border-0">
                      <td className={`px-4 py-3 ${off ? 'opacity-60' : ''}`}>
                        <span className="block font-semibold">
                          {academy.name}
                        </span>
                        {academy.is_own && <OwnTag />}
                      </td>
                      <td className={`px-4 py-3 ${off ? 'opacity-60' : ''}`}>
                        {academy.master?.name ?? '—'}
                        <span className="block text-xs text-muted-foreground">
                          {academy.master?.email ?? ''}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {academy.master?.phone
                          ? formatPhone(academy.master.phone)
                          : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusChip status={academy.status} />
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {createdAt(academy.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <EnterAcademyButton academy={academy} />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="rounded-full"
                            aria-label={`Editar ${academy.name}`}
                            onClick={() => setFormTarget(academy)}
                          >
                            <Pencil className="size-4" />
                          </Button>
                          <AcademyMenu {...actions(academy)} />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Celular: cartões */}
          <div className="space-y-3 md:hidden">
            {rows.map((academy) => (
              <div
                key={academy.id}
                className={`rounded-3xl border bg-card p-4 ${academy.status !== 'active' ? 'opacity-75' : ''}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="font-semibold">{academy.name}</span>
                    {academy.is_own && (
                      <div>
                        <OwnTag />
                      </div>
                    )}
                  </div>
                  <StatusChip status={academy.status} />
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {academy.master?.name ?? '—'} · {academy.master?.email ?? ''}
                  <br />
                  {academy.master?.phone
                    ? `${formatPhone(academy.master.phone)} · `
                    : ''}
                  desde {createdAt(academy.created_at)}
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <EnterAcademyButton academy={academy} className="flex-1" />
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 rounded-full"
                    onClick={() => setFormTarget(academy)}
                  >
                    Editar
                  </Button>
                  <AcademyMenu {...actions(academy)} />
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <AcademyFormDialog
        target={formTarget}
        onClose={() => setFormTarget(null)}
        onCreated={showCreated}
        onSaved={academies.refetch}
      />
      <CredentialsDialog
        credentials={credentials}
        onClose={() => setCredentials(null)}
      />
      <AlertDialog
        open={pending !== null}
        onOpenChange={(open) => !open && !busy && setPending(null)}
      >
        <AlertDialogContent>
          {pending && (
            <>
              <AlertDialogHeader>
                <AlertDialogTitle>
                  {CONFIRM_TEXT[pending.kind].title}
                </AlertDialogTitle>
                <AlertDialogDescription>
                  {CONFIRM_TEXT[pending.kind].body(pending.academy.name)}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={busy}>Cancelar</AlertDialogCancel>
                <AlertDialogAction
                  disabled={busy}
                  variant={pending.kind === 'block' ? 'destructive' : 'default'}
                  onClick={(event) => {
                    // Mantém o diálogo aberto até a API responder
                    event.preventDefault()
                    void confirm()
                  }}
                >
                  {CONFIRM_TEXT[pending.kind].action}
                </AlertDialogAction>
              </AlertDialogFooter>
            </>
          )}
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
