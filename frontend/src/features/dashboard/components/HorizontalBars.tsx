export type LabelCount = {
  label: string
  count: number
  // Texto do lado direito (padrão: o próprio número)
  display?: string
  // Barra cheia = total (padrão: o maior da lista)
  total?: number
}

type HorizontalBarsProps = {
  data: LabelCount[]
}

// Barras horizontais de uma cor: o rótulo identifica, o comprimento mostra
// a quantidade. Usado no Financeiro (formas de pagamento, modalidades) e nas
// Estatísticas (modalidade, faixa etária).
export function HorizontalBars({ data }: HorizontalBarsProps) {
  const max = Math.max(...data.map((item) => item.count), 1)

  return (
    <ul className="space-y-3">
      {data.map((item) => {
        const total = item.total ?? max
        const width = total > 0 ? Math.min(item.count / total, 1) * 100 : 0
        return (
          <li key={item.label} className="space-y-1">
            <div className="flex justify-between gap-3 text-sm">
              <span>{item.label}</span>
              <span className="font-medium whitespace-nowrap">
                {item.display ?? item.count}
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-muted">
              <div
                className="h-2.5 rounded-full bg-chart-1"
                style={{ width: `${width}%` }}
              />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
