import { ShieldCheck } from 'lucide-react'

export function Logo() {
  return (
    <div className="grid size-11 place-items-center rounded-2xl bg-card text-primary shadow-sm shadow-primary/10">
      <ShieldCheck className="size-5" strokeWidth={1.6} />
    </div>
  )
}
