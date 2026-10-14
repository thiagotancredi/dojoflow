import { cn } from '@/lib/utils'

// Cores dos avatares (definidas em styles/theme.css). Cada aluno recebe
// sempre a mesma cor, escolhida pela soma das letras do nome.
const palettes = [
  'bg-avatar-1 text-avatar-1-foreground',
  'bg-avatar-2 text-avatar-2-foreground',
  'bg-avatar-3 text-avatar-3-foreground',
  'bg-avatar-4 text-avatar-4-foreground',
  'bg-avatar-5 text-avatar-5-foreground',
]

type StudentAvatarProps = {
  name: string
  size?: 'sm' | 'lg'
}

export function StudentAvatar({ name, size = 'sm' }: StudentAvatarProps) {
  const initials = name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
  const colorIndex =
    [...name].reduce((total, char) => total + char.charCodeAt(0), 0) %
    palettes.length

  return (
    <div
      className={cn(
        'grid shrink-0 place-items-center rounded-full font-semibold',
        size === 'sm' ? 'size-9 text-xs' : 'size-12 text-base',
        palettes[colorIndex],
      )}
    >
      {initials}
    </div>
  )
}
