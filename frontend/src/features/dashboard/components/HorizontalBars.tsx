export type LabelCount = { label: string; count: number }

type HorizontalBarsProps = {
  data: LabelCount[]
}

// Barras horizontais de uma cor: o rótulo identifica, o comprimento mostra
// a quantidade. Reaproveitado em "por modalidade" e "faixa etária".
export function HorizontalBars({ data }: HorizontalBarsProps) {
  const max = Math.max(...data.map((item) => item.count), 1)

  return (
    <ul className="space-y-3">
      {data.map((item) => (
        <li key={item.label} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span>{item.label}</span>
            <span className="font-medium">{item.count}</span>
          </div>
          <div className="h-2.5 rounded-full bg-muted">
            <div
              className="h-2.5 rounded-full bg-chart-1"
              style={{ width: `${(item.count / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}
