import { Link } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function SettingsPage() {
  return (
    <div className="space-y-4">
      <PageHeader title="Configurações" />

      <section className="max-w-xl space-y-4 rounded-3xl bg-card p-5">
        <h2 className="font-semibold">Trocar senha</h2>
        <div className="space-y-1.5">
          <Label htmlFor="current-password">Senha atual</Label>
          <Input id="current-password" type="password" className="rounded-xl" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="new-password">Nova senha</Label>
          <Input id="new-password" type="password" className="rounded-xl" />
        </div>
        <Button className="rounded-full">Salvar</Button>
      </section>

      <section className="max-w-xl space-y-3 rounded-3xl bg-card p-5">
        <h2 className="font-semibold">Telegram</h2>
        <p className="text-sm text-muted-foreground">
          Conecte sua conta ao bot para cadastrar alunos pelo celular.
        </p>
        <Button variant="outline" className="rounded-full">
          Conectar Telegram
        </Button>
      </section>

      <Button asChild variant="ghost" className="rounded-full">
        <Link to="/login">Sair</Link>
      </Button>
    </div>
  )
}
