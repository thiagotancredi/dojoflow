# Redesenho visual: tema claro/escuro, Modalidades e tela de Alunos

Data: 2026-10-21 · Branch: `feat/student-detail-layout` · Protótipos aprovados:
`.superpowers/brainstorm/217162-1792553058/content/` (`modalidades.html`,
`alunos-v2.html`, `grafite-parceira.html`; cópias em `Anexos/` no Obsidian).
Obs.: os protótipos de Modalidades e Alunos foram desenhados nas cores lavanda;
vale o layout, as cores são as do grafite.

## Intenção

O mestre usa o site todo dia e reclamou de três coisas:

1. **Cansa a vista.** Os painéis são branco puro (`#ffffff`), os textos cinza têm
   contraste de 3,2:1 (abaixo dos 4,5:1 recomendados para texto pequeno) e as
   bordas (1,16:1) quase não aparecem, então os quadros se misturam com o painel.
2. **Telas mal dimensionadas.** Na tela de Alunos, a ficha à direita fica vazia
   quando ninguém está selecionado e os dois painéis terminam no meio da tela.
3. **Seção Modalidades confusa.** Cinco botões "Faixas" azuis fortes competem
   entre si, "Remover" tem o mesmo peso ao lado deles e o catálogo parece
   desabilitado.

O sucesso é o mestre abrir o site, à noite ou de dia, sem incômodo, e achar a
informação certa sem procurar.

## Já feito nesta branch (registro)

- **Ficha do aluno, aba Matrículas:** cada modalidade tem o nome no topo e dois
  quadros do mesmo tamanho, **Faixa** e **Mensalidade** (`EnrollmentBeltBlock` e
  `EnrollmentFeeCard`), lado a lado quando o painel tem ≥ 512 px (`@container`),
  um embaixo do outro quando é mais estreito.
- **Filtro da lista de alunos:** Ativos, Inativos e o seletor de modalidade ficam
  sempre na mesma linha; o seletor mostra "Todas" e nomes longos terminam em "…".
- **Janela "Histórico de faixas":** 448 px de largura e linhas que não vazam.

## Objetivos

1. Tema **claro grafite + petróleo** como padrão, com menos branco e contraste
   adequado.
2. Tema **escuro** do grafite como alternativa.
3. **Botão de alternar** claro/escuro, com a escolha lembrada.
4. **Modalidades** (em Configurações) como cartões em grade.
5. **Tela de Alunos** sempre mostrando a ficha de alguém, com painéis na altura
   da tela.

## Fora do escopo

- Os temas extras `verde` e `pastel` (existem no código, não estão em uso):
  continuam só no claro, sem ajuste.
- Dashboard: nenhum dado do dashboard entra na tela de Alunos (decisão explícita
  do Thiago: "misturou listagem com dashboard").
- Avisos por aluno dentro da lista (ex.: "sem faixa"): exigiriam dados novos na
  API da lista; não entram agora.
- Testes automáticos de frontend (decisão da V1).

## Anti-objetivos (falharia mesmo funcionando)

- Algum texto ou borda continuar ilegível em qualquer um dos dois temas.
- A tela de Alunos mostrar números ou pendências da academia.
- Remover modalidade com um clique só, sem confirmação.
- Botão voltar do navegador "preso" na tela de Alunos por causa da seleção
  automática.

## Restrições

- Todas as cores moram em `frontend/src/styles/theme.css`; componentes usam só os
  nomes das cores (tokens). Nenhuma cor direta nos componentes.
- O projeto já tem a variante `dark` do Tailwind ligada à classe `.dark`
  (`@custom-variant dark (&:is(.dark *))` em `index.css`); os componentes do
  shadcn já usam `dark:`.
- Nada depreciado; `tsc` e ESLint verdes.

## Como fica

### 1. Paleta: grafite + petróleo (decidido em 21/10, depois de testar no site)

O lavanda foi descartado ("um pouco infantilizado"); também foram vistas e
descartadas as paletas Avalon (azul jeans + areia), sálvia, terracota, vinho,
cobalto, coral e outras cores de destaque. A escolhida, já aplicada como teste e
aprovada ("ficou bem bonito"), é o tema `[data-theme='grafite']` em
`styles/theme.css`:

- **Base neutra em grafite:** fundo `#e6e6e4 → #efefed`, painéis `#f6f6f5`,
  janelas `#fbfbfa`, texto `#18191c`, texto secundário `#5f5f5c` (≈ 5,8:1),
  bordas `#dadad6`.
- **Botões em grafite** (`--primary: #2a2d33`, texto branco).
- **Petróleo só nos detalhes** (`#155e75`): item ativo do menu
  (`--sidebar-primary`), filtros/abas selecionados (`--chip-active-*`), links de
  ação, gráficos (`--chart-1`) e mensalidade ativa (`--status-active`).
- Avatares neutros (o petróleo só no primeiro tom).
- Status mantêm o significado: verde = apto/isenta, amarelo = pendência,
  cinza = inativa, vermelho = atraso.
- O tema `lavanda` continua no arquivo, mas deixa de ser o padrão
  (`index.html` usa `data-theme="grafite"`).

### 2. Tema escuro do grafite (decidido)

Bloco `[data-theme='grafite'].dark` em `theme.css`: fundo `#101112 → #141516`,
painéis `#1b1c1e`, janelas `#222326`, texto `#ececea`, secundário `#a5a5a0`,
bordas `#2f3034`, botões claros (`#e4e4e2` com texto grafite).

- Petróleo **fosco**, não neon (o ciano `#22d3ee` foi rejeitado): `#3d8fa3` no
  item ativo, `#4a9db0` em gráficos e mensalidade ativa, `#8cc8d5` em textos de
  destaque. Verde `#5cb88a` e amarelo `#d9a93a` também suavizados.
- **Cores das faixas não mudam.** *Minha escolha:* toda faixa desenhada ganha um
  contorno sutil no escuro, para a branca e a preta não sumirem.
- Item ativo do menu passou a usar `--sidebar-primary` (no lavanda é igual ao
  `--primary`, então nada muda lá).

### 3. Botão de alternar claro/escuro

- **Feito:** botão sol/lua no rodapé da barra lateral (desktop), acima de
  Configurações (`app/components/ThemeToggle.tsx`, lógica em `app/theme.ts`).
- **Falta:** uma linha "Aparência: Claro / Escuro" na seção Conta de
  Configurações (funciona no celular, onde não há barra lateral).
- *Minha escolha:* a escolha fica no `localStorage` do navegador. Sem escolha
  salva, segue o sistema (`prefers-color-scheme`).
- **Feito:** `applyInitialMode()` no `main.tsx` aplica a classe `.dark` antes do
  React desenhar.
- A tela de login e `/definir-acesso` respeitam o tema escolhido, mas não têm o
  botão.

### 4. Modalidades em cartões (decidido: opção "B · Cartões em grade")

- **Oferecidas:** grade de cartões (3 por linha no computador, 2 em telas médias,
  1 no celular; pela largura do painel). Cada cartão:
  - emoji num quadrado suave, nome;
  - com faixas: "19 faixas" e, se houver, "3 alunos sem faixa" em amarelo; sem
    pendência, "todos com faixa";
  - sem faixas: "Sem faixas" e o link "Cadastrar faixas ›";
  - clicar no cartão abre `/app/configuracoes/modalidades/:id/faixas`;
  - menu ⋯ no canto: "Ver faixas" e "Remover da academia" (abre a confirmação
    que já existe).
- **Catálogo:** etiquetas "+ 🥋 Judô"; um clique adiciona (como o "+ Adicionar"
  de hoje) e a modalidade vira cartão. *Minha escolha:* com todas adicionadas, a
  parte do catálogo some; sem nenhuma oferecida, a grade dá lugar a "Nenhuma
  modalidade ainda. Adicione abaixo."
- **Backend:** *minha escolha* — `ModalityOptionApiRead` ganha `belt_count: int`
  (quantidade de faixas da modalidade na academia), com teste; tipos do OpenAPI
  regenerados.

### 5. Tela de Alunos (decidido: `alunos-v2.html`)

- **Sempre com uma ficha aberta (computador):** ao abrir `/app/alunos` sem aluno na
  URL, abre a ficha do primeiro aluno da página atual da lista. Se uma busca ou
  filtro tirar da lista o aluno aberto, abre o primeiro resultado.
  *Minha escolha:* trocar de página (Anterior/Próxima) **não** troca a ficha — o
  mestre está só folheando a lista.
- A navegação automática usa `replace` (não cria passo no histórico), para o
  botão voltar não prender o usuário.
- **Tamanho:** os dois painéis vão do topo até o fim da tela; a lista rola por
  dentro com a paginação fixa embaixo; a ficha rola por dentro. *Minha escolha:*
  lista com cerca de 360 px, ficha com o resto.
- Item selecionado na lista: fundo de quadro + barra índigo à esquerda.
- **Celular:** sem seleção automática; lista em tela cheia, tocar abre a ficha
  (como hoje).
- **Casos especiais:** filtro sem resultado → à direita "Nenhum aluno com esses
  filtros" + "Mude a busca ou limpe os filtros"; academia sem alunos → "Nenhum
  aluno ainda" + botão "Cadastrar primeiro aluno" (vai para `/app/alunos/novo`).
- `StudentsEmptyDetail` (texto "Selecione um aluno") deixa de aparecer no
  computador; continua como reserva enquanto a lista carrega.

## Ordem sugerida

Status (21/10): **tudo implementado** na branch `feat/student-detail-layout`
(plano `docs/superpowers/plans/2026-10-21-visual-refresh.md`); falta o passeio no
navegador.

1. ~~Paleta grafite + petróleo, claro e escuro, botão na barra lateral~~.
2. ~~"Aparência" em Configurações + contorno das faixas no escuro~~.
3. ~~Modalidades em cartões (+ `belt_count` no backend)~~.
4. ~~Tela de Alunos~~.

Cada parte termina com `tsc` + ESLint verdes; o backend roda o teste da parte
tocada; a suíte completa roda uma vez no fim.

## Deixado para o construtor

- Tons finais de cada token, desde que: texto secundário ≥ 4,5:1 e bordas
  visíveis (≥ 1,25:1) contra o fundo onde aparecem, nos dois temas.
- Nome do token novo de quadro e a lista de componentes que passam a usá-lo.
- Ícones, animação do botão de alternar, detalhes de espaçamento.
- Como detectar "computador" para a seleção automática (ex.: mesma quebra `md`
  que já separa sidebar e barra inferior).

## A conferir pelo Thiago no navegador

Sem navegador na sessão de implementação, ninguém viu as telas renderizadas.
Passeio sugerido depois de cada parte: Dashboard, Alunos (lista + ficha),
Novo aluno, Graduações, Configurações (Modalidades, Faixas, Lançar faixas), nos
dois temas e no celular (DevTools, 390 px).
