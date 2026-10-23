import { ChevronLeft, UserRound } from 'lucide-react'

import { WhatsAppText } from '@/features/billing/components/WhatsAppMessage'

// Prévia da cobrança dentro de um "celular", como o aluno vai ver no
// WhatsApp. As cores imitam o WhatsApp de propósito (não são do tema).
export function WhatsAppPhone({ contact, text }: { contact: string; text: string }) {
  return (
    <div
      role="img"
      aria-label={`Prévia da mensagem no WhatsApp de ${contact}`}
      className="mx-auto w-full max-w-72 rounded-[2rem] bg-neutral-900 p-2 shadow-lg"
    >
      <div className="overflow-hidden rounded-[1.6rem] bg-[#efe7dc]">
        <div className="flex items-center gap-2 bg-[#075e54] px-3 py-2.5 text-sm text-white">
          <ChevronLeft className="size-4" />
          <span className="grid size-7 place-items-center rounded-full bg-white/25">
            <UserRound className="size-4" />
          </span>
          <span className="font-semibold">{contact}</span>
        </div>
        <div className="min-h-64 p-3">
          <WhatsAppText
            text={text}
            className="ml-auto max-w-full rounded-xl rounded-tr-sm bg-[#dcf8c6] px-3 py-2 text-[13px] leading-relaxed text-neutral-900 shadow-sm"
          />
        </div>
      </div>
    </div>
  )
}
