// Teclado do celular x gavetas presas no rodapé.
//
// No iPhone, abrir o teclado não encolhe a página: ele é desenhado por
// cima, e o que está preso em "bottom: 0" fica escondido atrás dele. O
// navegador informa a área que continua visível (window.visualViewport);
// daqui sai quanto o teclado cobre embaixo, guardado em duas variáveis CSS
// que as janelas (components/ui/dialog.tsx) usam para subir junto:
//
//   --keyboard-inset: altura coberta pelo teclado (0px sem teclado)
//   --visual-height:  altura da área visível

export function trackKeyboardInset() {
  const viewport = window.visualViewport
  if (!viewport) return

  const root = document.documentElement

  function update() {
    if (!viewport) return
    // clientHeight = altura da página "por baixo" (não muda com o teclado);
    // o que passa de height + offsetTop é a parte escondida pelo teclado
    const covered = root.clientHeight - (viewport.height + viewport.offsetTop)
    root.style.setProperty('--keyboard-inset', `${Math.max(0, Math.round(covered))}px`)
    root.style.setProperty('--visual-height', `${Math.round(viewport.height)}px`)
  }

  viewport.addEventListener('resize', update)
  viewport.addEventListener('scroll', update)
  update()
}
