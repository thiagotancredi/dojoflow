// Mensagem como ela chega no WhatsApp: balão verde de mensagem enviada,
// no fundo bege da conversa (cores do WhatsApp de propósito, não do tema).
// Quebras de linha preservadas; *texto* sai em negrito, como lá.
export function WhatsAppMessage({ text }: { text: string }) {
  return (
    <div className="rounded-2xl bg-[#efe7dc] p-3">
      <WhatsAppText
        text={text}
        className="ml-auto w-fit max-w-[92%] rounded-xl rounded-tr-sm bg-[#dcf8c6] px-3 py-2 leading-relaxed text-neutral-900 shadow-sm"
      />
    </div>
  )
}

// Só o texto, com o negrito do WhatsApp (*assim*)
export function WhatsAppText({
  text,
  className,
}: {
  text: string
  className?: string
}) {
  // split com grupo: as partes ímpares são o que estava entre asteriscos
  const parts = text.split(/\*([^*\n]+)\*/g)

  return (
    <p className={`text-sm wrap-anywhere whitespace-pre-wrap ${className ?? ''}`}>
      {parts.map((part, index) =>
        index % 2 === 1 ? <strong key={index}>{part}</strong> : part,
      )}
    </p>
  )
}
