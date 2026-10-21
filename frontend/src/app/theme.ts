// Claro/escuro: a classe "dark" no <html> troca as cores (styles/theme.css).
// A escolha fica guardada no navegador; sem escolha, segue o sistema.
const STORAGE_KEY = 'dojoflow-theme'

export type ColorMode = 'light' | 'dark'

function savedMode(): ColorMode | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    // Navegador bloqueando o armazenamento (ex.: janela anônima restrita)
    return null
  }
}

export function currentMode(): ColorMode {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

export function applyMode(mode: ColorMode) {
  document.documentElement.classList.toggle('dark', mode === 'dark')
}

export function saveMode(mode: ColorMode) {
  applyMode(mode)
  try {
    localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    // Sem armazenamento: vale só até fechar a aba
  }
}

// Chamado uma vez ao abrir o site, antes de desenhar a tela
export function applyInitialMode() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  applyMode(savedMode() ?? (prefersDark ? 'dark' : 'light'))
}
