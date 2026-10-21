// Formatação de dados para exibir na tela (padrão brasileiro).

// "62999990000" → "(62) 99999-0000"
export function formatPhone(phone: string) {
  const digits = phone.replace(/\D/g, '')
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
  }
  return phone
}

// "2026-10-20" → "20/10/2026"
export function formatDate(isoDate: string) {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}

// "74000000" → "74000-000"
export function formatZip(zip: string) {
  return zip.length === 8 ? `${zip.slice(0, 5)}-${zip.slice(5)}` : zip
}
