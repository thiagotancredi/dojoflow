import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/useAuth'
import { ModalitiesSection } from '@/features/modalities/components/ModalitiesSection'
import { AppearanceSetting } from '@/features/settings/components/AppearanceSetting'
import { BillingSettingsSection } from '@/features/settings/components/BillingSettingsSection'
import { ChangePasswordForm } from '@/features/settings/components/ChangePasswordForm'
import { TelegramConnect } from '@/features/settings/components/TelegramConnect'
import { formatPhone } from '@/lib/format'

// Configurações da academia: dados (só leitura por enquanto), modalidades,
// cobrança e conta (trocar senha, conectar Telegram, sair).
export function SettingsPage() {
  const navigate = useNavigate()
  const { master, signOut } = useAuth()

  async function handleSignOut() {
    try {
      await signOut()
    } catch {
      // Se a API falhar, a sessão local já foi limpa pelo signOut
    }
    navigate('/login', { replace: true })
  }

  // Dentro do /app sempre há sessão (RequireAuth); isto só satisfaz o tipo
  if (!master) return null

  const { academy } = master

  return (
    <div className="space-y-4">
      <PageHeader title="Configurações" />

      <section className="space-y-4 rounded-3xl bg-card p-5">
        <h2 className="font-semibold">Academia</h2>
        <div className="flex items-center gap-4">
          {/* Sem imagem por enquanto: mostra as iniciais */}
          <Avatar size="lg" className="size-14">
            <AvatarFallback className="text-base font-semibold">
              {initials(academy.name)}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            <p className="text-lg font-semibold">{academy.name}</p>
            {/* Só avisa quando há problema */}
            {academy.status === 'blocked' && (
              <Badge variant="destructive">Bloqueada</Badge>
            )}
          </div>
        </div>
      </section>

      {/* Modo suporte: "Mestre" e "Conta" seriam os dados e a conta do
          administrador, não do mestre da academia */}
      {!master.support_mode && (
        <section className="space-y-4 rounded-3xl bg-card p-5">
          <h2 className="font-semibold">Mestre</h2>
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Nome">{master.name}</Field>
            <Field label="E-mail">{master.email ?? 'Não informado'}</Field>
            <Field label="Telefone">
              {master.phone ? formatPhone(master.phone) : 'Não informado'}
            </Field>
            <Field label="Telegram">
              {master.telegram_linked ? 'Conectado' : 'Não conectado'}
            </Field>
          </dl>
        </section>
      )}

      <ModalitiesSection />

      <BillingSettingsSection />

      {!master.support_mode && (
        <section className="space-y-4 rounded-3xl bg-card p-5">
          <h2 className="font-semibold">Conta</h2>

          <AppearanceSetting />

          <ChangePasswordForm />

          {/* Some sozinho quando o bot confirma a conexão */}
          {!master.telegram_linked && <TelegramConnect />}

          <Button variant="ghost" className="rounded-full" onClick={handleSignOut}>
            Sair
          </Button>
        </section>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  )
}

// "Dojo Teste" → "DT"
function initials(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join('')
}

// "62999990000" → "(62) 99999-0000"; outros formatos ficam como vieram
