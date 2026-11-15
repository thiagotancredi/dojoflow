import type { SVGProps } from 'react'

// Ícone "R$" do Financeiro. O lucide não tem um; este é desenhado em traço
// (24×24, currentColor), para ficar com a mesma espessura dos outros ícones.
export function RealIcon({
  strokeWidth = 2,
  ...props
}: SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {/* R */}
      <path d="M2.5 19V5h5a3.5 3.5 0 0 1 0 7h-5" />
      <path d="M7.5 12l3.5 7" />
      {/* $ */}
      <path d="M17.5 3v18" />
      <path d="M21.5 6.5h-5.2a2.7 2.7 0 0 0 0 5.5h2.4a2.7 2.7 0 0 1 0 5.5H13" />
    </svg>
  )
}
