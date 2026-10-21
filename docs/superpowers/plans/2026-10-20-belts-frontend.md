# Faixas e graduação no site — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** As telas de faixas passam a existir no site e a usar a API: faixas da modalidade em Configurações, lançar faixas dos alunos antigos, listas de graduação e a faixa real na ficha e no cadastro do aluno (sai o mock).

**Architecture:** Mesmo padrão das telas de alunos: `features/belts/api.ts` + `hooks.ts` (via `useResource`/`useMutation`), formulários com React Hook Form + Zod, erros por `code` na tabela de `lib/api/errors.ts`. O desenho `BeltDrawing` passa a receber a faixa da API (`BeltApiRead`).

**Tech Stack:** o mesmo da branch dos alunos (React 19, RR 8, RHF, Zod 4, Sonner, shadcn).

**Spec:** `docs/superpowers/specs/2026-10-20-graduation-lists-design.md` (Telas 1, 2, 2a, 2b, 3; Desenho da faixa). Protótipo aprovado: `docs/superpowers/specs/2026-10-20-graduation-flow-prototype.html`. Base: branch `feat/students-frontend`.

## Global Constraints

- Tudo de `docs/superpowers/plans/2026-10-20-students-frontend.md` → Global Constraints vale aqui (nada depreciado, tokens de cor, textos em português, Write/Edit com o Vite rodando, sem testes automáticos de frontend, checagem por task = `npx tsc -b && npm run lint`, pipeline completa uma vez no fim).
- Paleta de cores da faixa (spec): branca `#f8fafc`, amarela `#facc15`, laranja `#f97316`, verde `#16a34a`, azul `#1d4ed8`, roxa `#7c3aed`, marrom `#78350f`, preta `#111827`, vermelha `#dc2626`, cinza `#9ca3af` + "outra cor"; marcas: a paleta + dourado `#d4a017` (padrão).
- Marcas 0–10; tempo mínimo número > 0 (até 1200) + `dias`/`meses`/`anos`, os dois juntos ou nenhum.
- Texto de ajuda do cadastro: "Cadastre da menor para a maior. Graus e dans são faixas próprias (ex.: Preta 1º Dan)."
- Listas de graduação, visual limpo: só o **desenho** da faixa (nome no tooltip), tempo curto `3m 12d` medido **na data do exame**, situação discreta (ponto verde "Apto", âmbar "Ainda não", cinza "Sem faixa"), faixa pretendida também como desenho.
- "Apto" nunca impede adicionar um aluno à lista.

## Review Focus

- **Excluir uma faixa usada** (histórico ou lista): toast com a mensagem de `BELT_IN_USE`, faixa continua na lista. → Task 2.
- **Reordenar depressa** (vários ↑ seguidos): a ordem final na tela é a que foi salva; nada de "pular" posição. → Task 2.
- **Lançar faixas com linhas em branco:** só as preenchidas vão; erro de uma linha não grava nenhuma (o backend é tudo ou nada) e o toast explica. → Task 3.
- **Mudar a data do exame:** situação e tempo de todos os alunos recalculam. → Task 5.
- **Modalidade sem faixas** na ficha, no cadastro e em "Nova lista": nada de faixa aparece / a modalidade não é oferecida. → Tasks 4 e 5.

---

### Task 1: API e hooks de faixas

**Files:** `features/belts/api.ts`, `features/belts/hooks.ts`, `features/belts/components/BeltDrawing.tsx` (recebe `Belt` da API), `lib/api/errors.ts` (códigos novos)

**Produces:** tipos `Belt = Schemas['BeltApiRead']`, `BeltPayload`, `EnrollmentBelts`, `GraduationListSummary`, `GraduationListDetail`; funções para todas as rotas de `/academy/modalities/{id}/belts*`, `/academy/belts/{id}`, `/students/{s}/enrollments/{e}/belts*`, `/graduation-lists*`; hooks `useBelts(modalityId)`, `usePendingEnrollments(modalityId)`, `useEnrollmentBelts(studentId, enrollmentId)`, `useGraduationLists()`, `useGraduationList(listId)` + mutations. Textos para: `BELT_NAME_TAKEN`, `BELT_IN_USE`, `BELT_ORDER_MISMATCH`, `BELTS_ALREADY_EXIST`, `PRESET_NOT_AVAILABLE`, `BELT_NOT_FOUND`, `BELT_MODALITY_MISMATCH`, `BELT_RECORD_NOT_FOUND`, `MODALITY_HAS_NO_BELTS`, `GRADUATION_LIST_NOT_FOUND`, `GRADUATION_ENTRY_NOT_FOUND`, `ALREADY_IN_LIST`, `ENROLLMENT_NOT_CANDIDATE`, `TARGET_BELT_REQUIRED`, `ENROLLMENT_MODALITY_MISMATCH`, `DUPLICATE_ENROLLMENT_IN_BATCH`, `ENROLLMENT_NOT_PENDING`.

- [ ] Implementar; `tsc` + `lint`; commit `feat: belts api client and hooks`.

### Task 2: Faixas em Configurações

**Files:** `features/belts/pages/ModalityBeltsPage.tsx`, `features/belts/components/BeltForm.tsx`, `features/modalities/components/ModalitiesSection.tsx` (botão **Faixas** no card oferecido), `app/router.tsx` (`/app/configuracoes/modalidades/:modalityId/faixas`)

Comportamento (tela 1 da spec): lista em ordem com posição, desenho, nome, tempo mínimo, ↑ ↓ (salva a ordem completa), Editar, Excluir (confirmação; `BELT_IN_USE` → toast); **Nova faixa** entra no fim; formulário com prévia ao vivo; lista vazia: texto de ajuda e, se a modalidade se chama Taekwondo, **Usar a sequência padrão do Taekwondo**. Aviso "N alunos de <modalidade> estão sem faixa registrada" (de `pending_belt_count`) com link para Lançar faixas.

- [ ] Implementar; `tsc` + `lint`; commit `feat: modality belts settings page`.

### Task 3: Lançar faixas dos alunos antigos (tela 2b)

**Files:** `features/belts/pages/BulkBeltsPage.tsx`, `app/router.tsx` (`.../faixas/lancar`)

Tabela com os alunos de `pending-enrollments`: nome, faixa (seletor com o desenho), desde (data). **Salvar faixas** envia só as linhas com faixa e data; sucesso → toast "N faixas lançadas" e a lista recarrega; erro → toast pelo `code`.

- [ ] Implementar; `tsc` + `lint`; commit `feat: bulk belt registration page`.

### Task 4: Faixa real na ficha e no cadastro (sai o mock)

**Files:** `features/belts/components/EnrollmentBeltBlock.tsx`, `BeltPicker.tsx`, `features/students/components/tabs/EnrollmentsTab.tsx`, `features/students/components/wizard/EnrollmentBlock.tsx`, `features/students/pages/NewStudentPage.tsx`; apagar `features/belts/mock.ts`

- Bloco da ficha lê `GET .../enrollments/{id}/belts` (faixa atual, `eligibility`, `eligible_on`, histórico); **Registrar graduação** = `POST` (próxima faixa marcada); **Histórico** com **Editar** e **Excluir** de cada registro (`PUT`/`DELETE`).
- As faixas da modalidade para o seletor vêm de `useBelts(modalityId)`; modalidade sem faixas → nada aparece.
- Nova matrícula e cadastro enviam `current_belt: { belt_id, graduated_on }` junto (o backend grava tudo ou nada).
- `rules.ts` fica só com `timeSince`/formatação curta; aptidão vem da API.

- [ ] Implementar; `tsc` + `lint`; commit `feat: real belts in student detail and wizard`.

### Task 5: Graduações

**Files:** `features/graduations/pages/GraduationListsPage.tsx`, `features/graduations/pages/GraduationListPage.tsx`, `app/navigation.ts` (item **Graduações**), `app/router.tsx` (`/app/graduacoes`, `/app/graduacoes/:listId`)

- Listas: cards (nome, modalidade, data do exame, nº de alunos); **Nova lista** (`Dialog`: nome, modalidade só com `has_belts`, data do exame).
- Detalhe: cabeçalho com nome e data do exame editáveis (PATCH; avisos recalculam) e Excluir lista; **Na lista**: aluno, desenho do retrato, tempo na data do exame (`3m 12d`), situação, faixa pretendida (desenho; clicar abre o seletor → PATCH), Remover; **Adicionar alunos**: candidatos com desenho, tempo, situação e "+ Adicionar" (faixa pretendida padrão = a próxima).

- [ ] Implementar; `tsc` + `lint`; commit `feat: graduation lists`.

### Task 6: Fechamento

- [ ] Pipeline completa uma vez (frontend `tsc`, `lint`, `build`; backend `ruff`, `typos`, `pytest -n auto`).
- [ ] Revisão final independente do branch; corrigir Critical/Important.
- [ ] Atualizar o Obsidian (spec das faixas, Plano B, DojoFlow.md) e entregar o roteiro do passeio no navegador ao Thiago.
