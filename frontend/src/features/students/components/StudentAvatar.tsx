import { UserRound } from 'lucide-react'

import { cn } from '@/lib/utils'

type StudentAvatarProps = {
  size?: 'sm' | 'lg'
}

// Imagem padrão do aluno (aprovada em 20/10): silhueta de traço fino em
// fundo lavanda, igual para todos. Foto de verdade fica para quando houver
// onde guardar arquivos.
export function StudentAvatar({ size = 'sm' }: StudentAvatarProps) {
  return (
    <div
      aria-hidden
      className={cn(
        'grid shrink-0 place-items-center rounded-full bg-chip-active text-chip-active-foreground',
        size === 'sm' ? 'size-9' : 'size-12',
      )}
    >
      <UserRound
        strokeWidth={1.6}
        className={size === 'sm' ? 'size-5' : 'size-7'}
      />
    </div>
  )
}
