// Balão com o texto da mensagem, como ela vai aparecer no WhatsApp
// (quebras de linha preservadas; *texto* sai em negrito, como lá)
export function WhatsAppMessage({ text }: { text: string }) {
  return (
    <div className="rounded-2xl bg-muted p-3">
      <WhatsAppText
        text={text}
        className="w-fit max-w-full rounded-2xl rounded-tl-sm bg-card px-3 py-2 shadow-sm"
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
