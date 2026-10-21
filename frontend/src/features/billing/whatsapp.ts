// Mensagem de cobrança do WhatsApp: ler o link da API e montar a prévia

// Lê o número e o texto de um link "https://wa.me/5562999990001?text=..."
export function parseWhatsAppUrl(url: string) {
  const parsed = new URL(url)
  const digits = parsed.pathname.replace(/\D/g, '')

  return {
    // Sem o 55 do Brasil, para mostrar como telefone daqui
    phone: digits.startsWith('55') ? digits.slice(2) : digits,
    text: parsed.searchParams.get('text') ?? '',
  }
}

export type TemplateValues = {
  nome: string
  academia: string
  valor: string
  meses: string
  pix: string
  recebedor: string
}

// Troca {nome}, {valor}... pelos dados, do mesmo jeito que o backend
// (troca simples: chaves que o mestre escrever no texto ficam como estão)
export function fillTemplate(template: string, values: TemplateValues) {
  return Object.entries(values).reduce(
    (text, [marker, value]) => text.replaceAll(`{${marker}}`, value),
    template,
  )
}
