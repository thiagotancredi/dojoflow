// O mesmo site serve dois endereços: o app dos mestres e o painel do
// administrador (admin.katsuflow.com.br; em dev, admin.localhost:5173).
export const isAdminHost = window.location.hostname.startsWith('admin.')

// Endereço do app principal visto a partir do painel ("admin." removido)
export function mainAppOrigin(): string {
  const host = window.location.host.replace(/^admin\./, '')
  return `${window.location.protocol}//${host}`
}
