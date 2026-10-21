// Desenho da faixa a partir das cores do cadastro (spec das faixas):
// retângulo de cantos retos na cor principal, listra central opcional,
// marcas (graus/dan) contadas a partir da ponta, ponta colorida opcional.

// Os mesmos campos da faixa na API (BeltApiRead)
export type BeltLook = {
  name: string
  primary_color: string
  stripe_color: string | null
  marks: number
  marks_color: string
  tip_color: string | null
}

const WHITE = '#f8fafc'

type BeltDrawingProps = {
  belt: BeltLook
  width?: number
  height?: number
}

export function BeltDrawing({ belt, width = 180, height = 28 }: BeltDrawingProps) {
  // Faixa branca ganha borda para não sumir no fundo claro
  const edge = belt.primary_color === WHITE ? '#cbd5e1' : 'rgba(0,0,0,.25)'
  const gap = Math.max(5, width * 0.03)
  const markWidth = Math.max(2, gap * 0.55)
  const firstX = width - gap * 1.6
  const lastX = firstX - (belt.marks - 1) * gap * 1.5

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Faixa ${belt.name}`}
      // No escuro, um contorno claro para a faixa branca e a preta não sumirem
      className="shrink-0 rounded-[3px] dark:ring-1 dark:ring-white/25"
    >
      <title>{belt.name}</title>
      <rect
        x={0.5}
        y={0.5}
        width={width - 1}
        height={height - 1}
        rx={2}
        fill={belt.primary_color}
        stroke={edge}
      />
      {belt.stripe_color && (
        <rect
          x={1}
          y={height * 0.36}
          width={width - 2}
          height={height * 0.28}
          fill={belt.stripe_color}
        />
      )}
      {/* Costuras discretas */}
      {[height * 0.2, height * 0.8].map((y) => (
        <line
          key={y}
          x1={4}
          y1={y}
          x2={width - 4}
          y2={y}
          stroke="rgba(255,255,255,.18)"
          strokeDasharray="3 3"
        />
      ))}
      {belt.marks > 0 && belt.tip_color && (
        <rect
          x={lastX - gap}
          y={1}
          width={width - (lastX - gap) - 1}
          height={height - 2}
          fill={belt.tip_color}
        />
      )}
      {Array.from({ length: belt.marks }, (_, index) => (
        <rect
          key={index}
          x={firstX - index * gap * 1.5}
          y={4}
          width={markWidth}
          height={height - 8}
          rx={1}
          fill={belt.marks_color}
        />
      ))}
    </svg>
  )
}
