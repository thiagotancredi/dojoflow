// Balão com o texto da mensagem, como ela vai aparecer no WhatsApp
// (quebras de linha preservadas)
export function WhatsAppMessage({ text }: { text: string }) {
  return (
    <div className="rounded-2xl bg-muted p-3">
      <p className="w-fit max-w-full rounded-2xl rounded-tl-sm bg-card px-3 py-2 text-sm break-words whitespace-pre-wrap shadow-sm">
        {text}
      </p>
    </div>
  )
}
