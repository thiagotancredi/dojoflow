// Fim da sessão de suporte desta aba, para a faixa mostrar "termina às…".
// sessionStorage: vale só para a aba (sobrevive ao F5). Pode falhar em
// navegação privada; aí a faixa só não mostra o horário.
const KEY = 'katsuflow:support-ends-at'
export const SUPPORT_SESSION_MS = 8 * 60 * 60 * 1000

export function rememberSupportEnd() {
  try {
    sessionStorage.setItem(KEY, String(Date.now() + SUPPORT_SESSION_MS))
  } catch {
    // sem armazenamento: segue sem o horário
  }
}

export function supportEndsAt(): Date | null {
  try {
    const value = Number(sessionStorage.getItem(KEY))
    return value > 0 ? new Date(value) : null
  } catch {
    return null
  }
}
