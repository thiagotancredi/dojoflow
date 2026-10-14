import { Link } from 'react-router'

import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <div className="grid min-h-dvh place-items-center p-6">
      <div className="space-y-4 rounded-3xl bg-card p-8 text-center">
        <h1 className="text-2xl font-semibold">Página não encontrada</h1>
        <Button asChild>
          <Link to="/app">Voltar ao início</Link>
        </Button>
      </div>
    </div>
  )
}
