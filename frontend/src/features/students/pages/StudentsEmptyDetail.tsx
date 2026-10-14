import { Users } from 'lucide-react'

// Aparece no lado direito quando nenhum aluno está aberto (/app/alunos).
export function StudentsEmptyDetail() {
  return (
    <div className="grid h-full min-h-80 place-items-center rounded-3xl bg-card p-8 text-center text-muted-foreground">
      <div className="space-y-2">
        <Users className="mx-auto size-8" strokeWidth={1.4} />
        <p className="text-sm">Selecione um aluno para ver a ficha.</p>
      </div>
    </div>
  )
}
