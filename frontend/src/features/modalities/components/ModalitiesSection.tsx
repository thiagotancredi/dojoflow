import { useEffect, useState } from 'react'

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
import { listAcademyModalities, toggleModality } from '@/features/modalities/api'
import type { ModalityOption } from '@/features/modalities/api'
import { ModalityCard } from '@/features/modalities/components/ModalityCard'

type LoadStatus = 'loading' | 'ready' | 'error'

// Seção "Modalidades" das Configurações: o que a academia oferece × catálogo.
// Só as oferecidas podem receber matrícula (site e bot do Telegram).
export function ModalitiesSection() {
  const [options, setOptions] = useState<ModalityOption[]>([])
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading')
  // Mudar este número faz o useEffect buscar a lista de novo ("Tentar de novo")
  const [reloadKey, setReloadKey] = useState(0)
  // Modalidade cujo clique está esperando a API (desabilita o botão dela)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [toggleError, setToggleError] = useState<string | null>(null)
  // Modalidade aguardando confirmação de remoção (abre o diálogo)
  const [toRemove, setToRemove] = useState<ModalityOption | null>(null)

  // Busca a lista ao abrir a tela (e a cada "Tentar de novo")
  useEffect(() => {
    const controller = new AbortController()

    listAcademyModalities(controller.signal)
      .then((data) => {
        setOptions(data)
        setLoadStatus('ready')
      })
      .catch(() => {
        // Cancelado porque a tela fechou: não é erro, só ignora
        if (!controller.signal.aborted) setLoadStatus('error')
      })

    // Ao sair da tela antes da resposta, cancela a requisição
    return () => controller.abort()
  }, [reloadKey])

  function retry() {
    setLoadStatus('loading')
    setReloadKey((current) => current + 1)
  }

  async function toggle(modalityId: string) {
    setPendingId(modalityId)
    setToggleError(null)

    try {
      const isSelected = await toggleModality(modalityId)
      // Novo array com só o item trocado: é assim que o React percebe a mudança
      setOptions((current) =>
        current.map((option) =>
          option.id === modalityId
            ? { ...option, is_selected: isSelected }
            : option,
        ),
      )
    } catch {
      setToggleError('Não foi possível alterar a modalidade. Tente novamente.')
    } finally {
      setPendingId(null)
    }
  }

  function confirmRemove() {
    if (toRemove) void toggle(toRemove.id)
    setToRemove(null)
  }

  const offered = options.filter((option) => option.is_selected)
  const catalog = options.filter((option) => !option.is_selected)

  return (
    <section className="space-y-4 rounded-3xl bg-card p-5">
      <div className="space-y-1">
        <h2 className="font-semibold">Modalidades</h2>
        <p className="text-sm text-muted-foreground">
          Escolha quais modalidades sua academia oferece. Só as oferecidas
          aparecem na hora de matricular um aluno, no site e no bot do
          Telegram.
        </p>
      </div>

      {loadStatus === 'loading' && (
        <p className="text-sm text-muted-foreground">Carregando modalidades…</p>
      )}

      {loadStatus === 'error' && (
        <div className="space-y-3">
          <p role="alert" className="text-sm text-destructive">
            Não foi possível carregar as modalidades.
          </p>
          <Button variant="outline" className="rounded-full" onClick={retry}>
            Tentar de novo
          </Button>
        </div>
      )}

      {loadStatus === 'ready' && (
        <>
          {toggleError && (
            <p role="alert" className="text-sm text-destructive">
              {toggleError}
            </p>
          )}

          <div className="space-y-2">
            <SectionLabel>Oferecidas pela academia ({offered.length})</SectionLabel>
            {offered.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Nenhuma modalidade ainda. Adicione abaixo.
              </p>
            ) : (
              // @container: as colunas seguem a largura da seção, não da tela
              <div className="@container">
                <div className="grid gap-3 @md:grid-cols-2 @3xl:grid-cols-3">
                  {offered.map((option) => (
                    <ModalityCard
                      key={option.id}
                      option={option}
                      onRemove={() => setToRemove(option)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {catalog.length > 0 && (
            <div className="space-y-2">
              <SectionLabel>Adicionar à academia</SectionLabel>
              <div className="flex flex-wrap gap-2">
                {catalog.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    // Trava todas enquanto uma espera a API: clique duplo não
                    // adiciona e remove em seguida
                    disabled={pendingId !== null}
                    onClick={() => void toggle(option.id)}
                    className="rounded-full border border-dashed px-3 py-1.5 text-sm transition-colors hover:border-ring hover:bg-muted disabled:opacity-50"
                  >
                    <span className="font-semibold text-sidebar-primary">+</span>{' '}
                    {option.emoji} {option.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Confirmação ao remover: aberto enquanto houver uma modalidade em toRemove */}
      <AlertDialog
        open={toRemove !== null}
        onOpenChange={(open) => {
          if (!open) setToRemove(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover {toRemove?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Alunos já matriculados continuam matriculados; só não será
              possível fazer novas matrículas nesta modalidade.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmRemove}>
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  )
}

function SectionLabel({ children }: { children: string | (string | number)[] }) {
  return (
    <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
      {children}
    </h3>
  )
}
