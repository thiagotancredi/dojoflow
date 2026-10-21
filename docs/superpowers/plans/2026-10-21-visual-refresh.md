# Redesenho visual (restante) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Terminar o redesenho: "Aparência" em Configurações, contorno das faixas no escuro, Modalidades em cartões (com `belt_count` na API) e tela de Alunos sempre com uma ficha aberta, na altura da tela.

**Architecture:** Frontend React + Tailwind v4 com tokens em `styles/theme.css` (tema `grafite`, já aplicado). O modo claro/escuro vira um pequeno "store" em `app/theme.ts` lido com `useSyncExternalStore`, para o botão da barra lateral e o de Configurações ficarem sincronizados. No backend, só um campo novo em `ModalityOptionApiRead`.

**Tech Stack:** React 19, React Router 7, Tailwind v4 (`@container`), shadcn/ui (Radix), FastAPI + SQLAlchemy async, pytest.

**Spec:** `docs/superpowers/specs/2026-10-21-visual-refresh-design.md`

## Global Constraints

- Cores só por tokens de `styles/theme.css`; nenhuma cor direta em componente.
- Texto secundário ≥ 4,5:1 e bordas visíveis nos dois temas (claro e `.dark`).
- Nada depreciado; `npx tsc -b --noEmit` e `npm run lint` verdes em cada tarefa.
- Nunca escrever arquivos do frontend com `cat >` enquanto o Vite roda (use Write/Edit ou arquivo temporário + `mv`).
- Textos da interface em português; código em inglês.
- Frontend sem testes automáticos (decisão da V1): a verificação de cada tarefa de tela é `tsc` + lint + o Vite compilar o módulo (`curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/src/<arquivo>` → `200`) + o roteiro manual da tarefa.
- Backend: rodar só o teste da tarefa; a suíte completa roda uma vez na Tarefa 5.

## Review Focus

1. **Salvar a ficha não pode "pular" de aluno:** editar um aluno ativo para inativo com o filtro "Ativos" faz a lista recarregar sem ele; a ficha aberta deve continuar a mesma (a troca automática só reage a mudança de busca/filtro, nunca a recarga da lista). → Tarefa 4, passo de verificação manual 3.
2. **Botão voltar:** abrir `/app/alunos` (seleção automática) e apertar voltar deve sair da tela de Alunos, não voltar para ela mesma. → Tarefa 4, verificação 2.
3. **Dois botões de tema sincronizados:** trocar o tema em Configurações atualiza o ícone sol/lua da barra lateral na hora, e vice-versa. → Tarefa 1, verificação 2.
4. **Armazenamento bloqueado:** com `localStorage` lançando erro, alternar o tema funciona (só não é lembrado). → Tarefa 1, verificação 3.
5. **Clique duplo no catálogo:** dois cliques rápidos numa etiqueta "+ Judô" não podem alternar duas vezes (adicionar e remover). → Tarefa 3, verificação 3.

---

### Task 0: Commit do que já está pronto na branch

Já estão na árvore de trabalho, sem commit: quadros Faixa | Mensalidade, filtro numa linha, janela de histórico, tema `grafite` (claro/escuro) com botão na barra lateral, spec e este plano.

- [ ] **Step 1: Conferir** `git status` (só arquivos de `frontend/src`, `frontend/index.html` e `docs/superpowers`).
- [ ] **Step 2: Commit**

```bash
git add frontend/index.html frontend/src docs/superpowers
git commit -m "feat: belt and fee side by side, graphite theme with dark mode toggle"
```

---

### Task 1: Modo claro/escuro sincronizado + "Aparência" em Configurações + contorno das faixas

**Files:**
- Modify: `frontend/src/app/theme.ts`
- Modify: `frontend/src/app/components/ThemeToggle.tsx`
- Create: `frontend/src/features/settings/components/AppearanceSetting.tsx`
- Modify: `frontend/src/features/settings/pages/SettingsPage.tsx` (seção "Conta", antes de `<ChangePasswordForm />`)
- Modify: `frontend/src/features/belts/components/BeltDrawing.tsx`

**Interfaces:**
- Consumes: `ColorMode`, `applyMode`, `applyInitialMode` já existentes em `app/theme.ts`.
- Produces: `useColorMode(): [ColorMode, (mode: ColorMode) => void]` em `app/theme.ts`.

- [ ] **Step 1: Em `app/theme.ts`, transformar o modo num store observável**
  - `saveMode(mode)` passa a disparar `window.dispatchEvent(new Event('dojoflow-theme-change'))` depois de aplicar e salvar.
  - Novo `useColorMode()` com `useSyncExternalStore(subscribe, currentMode)`, onde `subscribe` escuta `'dojoflow-theme-change'`; devolve `[mode, saveMode]`.
  - `localStorage` continua dentro de `try/catch` (leitura e escrita).

- [ ] **Step 2: `ThemeToggle` usa `useColorMode()`** no lugar do `useState` local (mesmo visual e rótulos: "Usar tema escuro" / "Usar tema claro").

- [ ] **Step 3: Criar `AppearanceSetting()`**
  Bloco no padrão do `ChangePasswordForm` (`max-w-xl space-y-2`): título `h3` "Aparência" e dois botões-chip lado a lado, "Claro" e "Escuro", com o selecionado usando as classes de chip ativo já usadas no filtro de alunos (`border-chip-active-border bg-chip-active text-chip-active-foreground`). `aria-pressed` no selecionado. Usa `useColorMode()`.

- [ ] **Step 4: Renderizar `<AppearanceSetting />`** na seção "Conta" de `SettingsPage`, acima de `<ChangePasswordForm />`.

- [ ] **Step 5: Contorno das faixas no escuro**
  No `<svg>` de `BeltDrawing`, acrescentar `className="rounded-[3px] dark:ring-1 dark:ring-white/25"` (a faixa branca e a preta não somem no fundo escuro; no claro nada muda).

- [ ] **Step 6: Verificar**
  Run: `cd frontend && npx tsc -b --noEmit && npm run lint`
  Expected: sem erros. E `curl` dos 5 arquivos acima no Vite → `200`.
  Manual: (1) Configurações → Aparência → Escuro: site inteiro escurece; recarregar mantém. (2) Com a barra lateral visível, trocar em Configurações muda o ícone sol/lua na hora, e o contrário. (3) No console do navegador: `Object.defineProperty(window, 'localStorage', { get() { throw new Error('x') } })` e alternar: troca de tema funciona sem erro. (4) Ficha de um aluno faixa branca/preta no escuro: contorno visível.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/theme.ts frontend/src/app/components/ThemeToggle.tsx frontend/src/features/settings frontend/src/features/belts/components/BeltDrawing.tsx
git commit -m "feat: appearance setting synced with sidebar toggle, belt outline in dark mode"
```

---

### Task 2: `belt_count` nas opções de modalidade (backend + tipos)

**Files:**
- Modify: `src/dojoflow/schemas/modality.py` (`ModalityOptionRead`)
- Modify: `src/dojoflow/schemas/modality_api.py` (`ModalityOptionApiRead` e `from_internal`)
- Modify: `src/dojoflow/services/modality.py` (`list_academy_options`)
- Test: `tests/api/test_belts_api.py` (`test_modality_options_report_has_belts`), `tests/api/test_modalities_api.py` (dicionário esperado da linha ~43)
- Modify (gerado): `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Produces: campo `belt_count: int` em `ModalityOptionApiRead` (JSON `belt_count`), tipo TS `ModalityOption['belt_count']: number`.

- [ ] **Step 1: Escrever o teste que falha**
  Em `test_modality_options_report_has_belts`, criar duas faixas no Taekwondo (`'Branca'`, `'Amarela'`) e acrescentar:

```python
    belt_count = {item['name']: item['belt_count'] for item in response.json()}
    assert belt_count == {'Taekwondo': 2, 'Boxe': 0}
```
  Em `tests/api/test_modalities_api.py`, acrescentar `'belt_count': 0` ao dicionário esperado que já tem `'has_belts': False`.

- [ ] **Step 2: Rodar e ver falhar**
  Run: `poetry run pytest -q tests/api/test_belts_api.py::test_modality_options_report_has_belts tests/api/test_modalities_api.py`
  Expected: FAIL com `KeyError: 'belt_count'` / dicionários diferentes.

- [ ] **Step 3: Implementar**
  - `ModalityOptionRead.belt_count: int = 0`; `ModalityOptionApiRead.belt_count: int`, repassado em `from_internal`.
  - Em `list_academy_options`, trocar o `set` de `distinct(Belt.modality_id)` por uma contagem `select(Belt.modality_id, func.count()).where(Belt.academy_id == academy_id).group_by(Belt.modality_id)` → `dict[int, int]`; `has_belts = count > 0`, `belt_count = count`.

- [ ] **Step 4: Rodar e ver passar**
  Mesmo comando do Step 2. Expected: PASS. E `poetry run ruff check src tests && poetry run ruff format --check src tests`.

- [ ] **Step 5: Regenerar os tipos do frontend** (API rodando em `localhost:8000`)
  Run: `cd frontend && tmp=$(mktemp -p "$TMPDIR") && npx openapi-typescript http://localhost:8000/openapi.json -o "$tmp.d.ts" && mv "$tmp.d.ts" src/lib/api/schema.d.ts && git diff --stat src/lib/api/schema.d.ts`
  Expected: diff pequeno com `belt_count: number;` em `ModalityOptionApiRead`. `npx tsc -b --noEmit` verde.

- [ ] **Step 6: Commit**

```bash
git add src/dojoflow tests frontend/src/lib/api/schema.d.ts
git commit -m "feat: belt_count in academy modality options"
```

---

### Task 3: Modalidades em cartões

**Files:**
- Create (gerado): `frontend/src/components/ui/dropdown-menu.tsx` via `cd frontend && npx shadcn add dropdown-menu`
- Create: `frontend/src/features/modalities/components/ModalityCard.tsx`
- Modify: `frontend/src/features/modalities/components/ModalitiesSection.tsx` (remove o `ModalityCard` antigo e o `SectionLabel` continua)

**Interfaces:**
- Consumes: `ModalityOption` com `belt_count` (Tarefa 2); `toggle(id)`, `pendingId`, `setToRemove` já existentes em `ModalitiesSection`.
- Produces: `ModalityCard({ option, onRemove }: { option: ModalityOption; onRemove: () => void })`.

- [ ] **Step 1: Adicionar o menu do shadcn**
  Run: `cd frontend && npx shadcn add dropdown-menu`
  Expected: cria `src/components/ui/dropdown-menu.tsx` usando o pacote `radix-ui` já instalado (sem dependência nova). Conferir com `git status`.

- [ ] **Step 2: Criar `ModalityCard`** (oferecida)
  - Cartão `rounded-2xl border bg-card p-4`, `relative`, com: emoji num quadrado `size-10 rounded-xl bg-muted`, nome (`font-semibold`), situação das faixas e o botão ⋯ no canto superior direito.
  - Situação: `belt_count > 0` → `"{n} faixa(s)"` (`1 faixa` / `19 faixas`) e, em linha separada, `pending_belt_count > 0` → bolinha `size-2 rounded-full bg-status-pending` + `"{n} aluno(s) sem faixa"` (`1 aluno sem faixa`) em cor de texto normal; sem pendência → `"todos com faixa"` em `text-muted-foreground`. `belt_count === 0` → `"Sem faixas"` + texto `"Cadastrar faixas ›"` em `text-sidebar-primary font-medium`. (Não usar `status-warning`/`status-critical`: reservados para vencimento e atraso.)
  - Clicar no cartão abre `/app/configuracoes/modalidades/${option.id}/faixas`: um `<Link>` "esticado" (`absolute inset-0 rounded-2xl` com `aria-label="Faixas de {nome}"`) e o botão ⋯ acima dele (`relative z-10`), para não aninhar elementos clicáveis.
  - Menu ⋯ (`DropdownMenu`, botão `aria-label="Opções de {nome}"`): "Ver faixas" (mesmo link) e "Remover da academia" (`variant="destructive"`, chama `onRemove`).

- [ ] **Step 3: Reescrever o corpo de `ModalitiesSection` (estado `ready`)**
  - Oferecidas: título `SectionLabel` "Oferecidas pela academia (n)"; grade `@container` com `grid gap-3 @md:grid-cols-2 @3xl:grid-cols-3` de `ModalityCard` (`onRemove={() => setToRemove(option)}`). Sem nenhuma: texto `"Nenhuma modalidade ainda. Adicione abaixo."`.
  - Catálogo (só se houver itens): `SectionLabel` "Adicionar à academia"; etiquetas em `flex flex-wrap gap-2`, cada uma um `<button>` `rounded-full border border-dashed px-3 py-1.5 text-sm` com `"+ {emoji} {nome}"`, `disabled={pendingId !== null}`, `onClick={() => toggle(option.id)}`.
  - Diálogo de remoção, carregando, erro e "Tentar de novo" ficam como estão.

- [ ] **Step 4: Verificar**
  Run: `cd frontend && npx tsc -b --noEmit && npm run lint`; `curl` de `ModalitiesSection.tsx`, `ModalityCard.tsx`, `dropdown-menu.tsx` → `200`.
  Manual: (1) Configurações: cartões 3/2/1 por linha conforme a largura; Taekwondo mostra "19 faixas" e, se houver, "N alunos sem faixa"; Boxe "Sem faixas · Cadastrar faixas ›". (2) Clicar no cartão abre as faixas; ⋯ → "Remover da academia" pede confirmação. (3) Clique duplo rápido em "+ Judô": adiciona uma vez só. (4) Adicionar todas: a parte "Adicionar à academia" some. (5) Tema escuro: cartões, menu e etiquetas legíveis.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/dropdown-menu.tsx frontend/src/features/modalities
git commit -m "feat: modality cards with belt status and catalog chips"
```

---

### Task 4: Tela de Alunos sempre com ficha, na altura da tela

**Files:**
- Create: `frontend/src/lib/hooks/useMediaQuery.ts`
- Modify: `frontend/src/features/students/pages/StudentsPage.tsx`
- Modify: `frontend/src/features/students/pages/StudentsEmptyDetail.tsx`
- Modify (se preciso para rolar por dentro): `frontend/src/features/students/pages/StudentDetailPage.tsx`

**Interfaces:**
- Produces: `useMediaQuery(query: string): boolean` (com `useSyncExternalStore` sobre `window.matchMedia`).
- Produces: contexto do `<Outlet>` passa a ser `{ refreshList: () => void; listState: StudentsListState }`, com `type StudentsListState = 'loading' | 'error' | 'empty' | 'no-results' | 'has-items'` exportado de `StudentsPage.tsx`.

- [ ] **Step 1: Criar `useMediaQuery`.** Sem dependências novas.

- [ ] **Step 2: Altura da tela (só `md+`)**
  - A raiz de `StudentsPage` vira `md:flex md:h-[calc(100dvh-2.5rem)] md:flex-col` (2.5rem = padding `md:p-5` do `AppLayout`, em cima e embaixo); o `PageHeader` fica com a altura natural e o contêiner das duas colunas ganha `md:min-h-0 md:flex-1`.
  - Lista: largura `md:w-[360px]`, `flex flex-col`; a área dos alunos rola por dentro (`min-h-0 flex-1 overflow-y-auto`); busca/filtros no topo e paginação no rodapé ficam fixos.
  - Ficha: `min-h-0 overflow-y-auto` no painel da direita.
  - Celular: tudo como hoje (lista em tela cheia, sem altura fixa).
  - Item selecionado na lista: já existe destaque; trocar para fundo `bg-muted` + `shadow-[inset_3px_0_0_var(--sidebar-primary)]` em `StudentListItem.tsx` se ainda não tiver a barra.

- [ ] **Step 3: Seleção automática (só quando `useMediaQuery('(min-width: 768px)')`)**
  Num `useEffect` de `StudentsPage`, com os dados da lista carregados e itens na página:
  - sem aluno na URL → `navigate(\`/app/alunos/${items[0].id}?${params}\`, { replace: true })`;
  - aluno na URL que não está na página **e** a chave `busca|status|modalidade` mudou desde a última execução (guardar a chave anterior num `useRef`) → mesmo `navigate` para o primeiro;
  - recarga da lista (`refetch`) ou troca de página **não** navega.
  Ler o id aberto com `useMatch('/app/alunos/:studentId')` (já usado em `hasSelection`).

- [ ] **Step 4: Estados vazios à direita**
  `StudentsPage` calcula `listState` (`'no-results'` = `total === 0` com busca/filtro; `'empty'` = `total === 0` sem filtro) e passa no contexto do `<Outlet>`. `StudentsEmptyDetail` lê com `useOutletContext` e mostra:
  - `'no-results'`: ícone de busca, `"Nenhum aluno com esses filtros"`, `"Mude a busca ou limpe os filtros."`;
  - `'empty'`: `"Nenhum aluno ainda"`, `"Cadastre o primeiro para começar."`, botão `"Cadastrar primeiro aluno"` → `/app/alunos/novo`;
  - demais: o texto atual ("Selecione um aluno para ver a ficha.") como reserva enquanto carrega.
  Verificar quem mais usa o contexto do `Outlet` (`grep -rn "useOutletContext" frontend/src`) e atualizar o tipo.

- [ ] **Step 5: Verificar**
  Run: `cd frontend && npx tsc -b --noEmit && npm run lint`; `curl` dos arquivos alterados → `200`.
  Manual: (1) `/app/alunos` no computador abre a ficha do primeiro aluno; os painéis vão até o fim da tela e a paginação fica visível com a lista rolando. (2) Abrir Alunos pelo menu e apertar voltar: sai da tela (não fica preso). (3) Filtro "Ativos", abrir um aluno, mudar o status dele para inativo e salvar: a ficha continua a dele. (4) Buscar um nome que tira o aluno aberto da lista: abre o primeiro resultado. (5) Próxima página: a ficha não muda. (6) Busca sem resultado: direita mostra "Nenhum aluno com esses filtros". (7) DevTools 390 px: lista em tela cheia, sem seleção automática; tocar abre a ficha. (8) Tema escuro conferido.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/hooks/useMediaQuery.ts frontend/src/features/students
git commit -m "feat: students page always shows a student and fills the screen height"
```

---

### Task 5: Fechamento

**Files:**
- Modify: `docs/superpowers/specs/2026-10-21-visual-refresh-design.md` (status/ordem: tudo feito)
- Modify (fora do repo): nota `2 · Especificações/Redesenho visual (design).md` e `DojoFlow.md` no Obsidian

- [ ] **Step 1: Suíte completa do backend**
  Run: `poetry run pytest -q`
  Expected: todos passam (hoje 270 + o teste alterado).

- [ ] **Step 2: Checagens do frontend**
  Run: `cd frontend && npx tsc -b --noEmit && npm run lint`
  Expected: sem erros.

- [ ] **Step 3: Atualizar o status no spec e no Obsidian** (cópia da nota a partir do spec; status "implementado, aguardando passeio no navegador").

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers
git commit -m "docs: visual refresh status"
```
