import { useSyncExternalStore } from 'react'

// Claro/escuro: a classe "dark" no <html> troca as cores (styles/theme.css).
// A escolha fica guardada no navegador; sem escolha, segue o sistema.
const STORAGE_KEY = 'dojoflow-theme'
// Avisa quem mostra o tema (botão da barra lateral, Configurações) que mudou
const CHANGE_EVENT = 'dojoflow-theme-change'

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
  window.dispatchEvent(new Event(CHANGE_EVENT))
}

// O tema escuro ainda não foi ajustado: por enquanto o site é sempre claro
// (ignora a escolha antiga e o modo escuro do celular) e os botões de troca
// estão fora da tela. Para religar: true aqui + ThemeToggle/AppearanceSetting
const DARK_MODE_ENABLED = false

// Chamado uma vez ao abrir o site, antes de desenhar a tela
export function applyInitialMode() {
  if (!DARK_MODE_ENABLED) {
    applyMode('light')
    return
  }
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  applyMode(savedMode() ?? (prefersDark ? 'dark' : 'light'))
}

function subscribe(onChange: () => void) {
  window.addEventListener(CHANGE_EVENT, onChange)
  return () => window.removeEventListener(CHANGE_EVENT, onChange)
}

// Tema atual + função para trocar. Todo componente que usa este hook
// redesenha quando o tema muda em qualquer lugar (useSyncExternalStore
// "assina" um valor que mora fora do React, aqui a classe do <html>).
export function useColorMode(): [ColorMode, (mode: ColorMode) => void] {
  const mode = useSyncExternalStore(subscribe, currentMode)
  return [mode, saveMode]
}
