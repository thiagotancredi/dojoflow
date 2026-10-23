// Links de contato a partir de um telefone brasileiro guardado só com
// números (ex.: "62999990000")

function digits(phone: string) {
  return phone.replace(/\D/g, '')
}

// Ligar: no celular abre a discagem; no computador, o app de chamadas
export function callHref(phone: string) {
  return `tel:+55${digits(phone)}`
}

// Conversa em branco no WhatsApp
export function whatsappHref(phone: string) {
  return `https://wa.me/55${digits(phone)}`
}
