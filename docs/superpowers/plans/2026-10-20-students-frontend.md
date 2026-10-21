# Alunos no site (Fases 7–9) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** As telas de alunos do site passam a usar a API de verdade: lista com busca, filtros e páginas (Fase 7); ficha com as 4 abas editáveis (Fase 8); cadastro em 4 etapas com CEP automático (Fase 9).

**Architecture:** Cada recurso ganha funções de API em `features/students/api.ts` e hooks em `features/students/hooks.ts`: leitura devolve `{ data, isLoading, error, refetch }`, escrita devolve `{ mutate, isPending, error }`, como manda a spec, para a futura troca por TanStack Query mexer só no miolo dos hooks. Formulários com React Hook Form + Zod; 422 vira erro no campo; 404/409/500/rede vira toast em português a partir de uma tabela `code → texto`. Os dados fictícios (`mock-data.ts`, `types.ts`) saem; os tipos vêm do OpenAPI.

**Tech Stack:** React 19 + TypeScript 6 + Vite 8, React Router 8, Tailwind v4 + shadcn/ui, `openapi-fetch` (tipos gerados), React Hook Form + Zod (novos), Sonner para toasts (novo, via shadcn).

**Spec:** `docs/superpowers/specs/2026-10-13-web-frontend-v1-design.md` (seções 2, 3.2, 5, 6.3, 6.4, 7.2). Rotas da spec: `/app/alunos`, `/app/alunos/novo`, `/app/alunos/:id`.

**Protótipo aprovado (20/10):** `docs/superpowers/specs/2026-10-20-students-prototype.html`. Decisões do Thiago sobre ele:
- **Responsável = fluxo do Telegram:** "O próprio aluno é o responsável" (padrão) não grava ninguém; "Outra pessoa" abre o formulário (1 ou mais). Ficha sem responsáveis mostra "O próprio aluno é o responsável". "O próprio aluno" sai da lista de parentesco.
- **Várias matrículas no cadastro** (ex.: Taekwondo + Boxe), gravadas juntas: a API passa a aceitar uma lista (Task 0).
- **Faixa nas telas de aluno com valores fictícios** (card da ficha: desenho, nome, tempo, apto, Registrar graduação, Histórico; cadastro e nova matrícula: "Faixa atual" + "Desde"). Nada de faixa é enviado à API agora; a integração vem com o plano das faixas.
- **Imagem padrão do aluno:** silhueta de traço fino (Lucide) com fundo lavanda, igual para todos, no lugar das iniciais.

## Global Constraints

- **Nada depreciado** (regra do Thiago): `npx tsc -b` (com `reportsDeprecated`) e `npm run lint` limpos ao fim de cada task.
- Antes de instalar qualquer lib ou componente, conferir a versão atual na documentação oficial.
- Nenhuma tela chama `api.*` direto: tudo passa por `features/students/api.ts` + `hooks.ts`.
- Toda leitura usa `AbortController` na limpeza do `useEffect`.
- Busca espera **300 ms** após a digitação. Filtros e página ficam na URL (`?busca=&status=&modalidade=&pagina=`).
- Textos da interface em português; código em inglês. Cores só pelos tokens de `styles/theme.css` (nunca `bg-indigo-50` direto).
- Regras dos campos (iguais às do backend): nome 2–120; telefone até 20 (responsável: 10–20); CPF 11 dígitos; Instagram até 80; e-mail até 255; CEP 8 dígitos; UF 2 letras; número até 20; complemento até 120; vencimento **1 a 28**; mensalidade ≥ 0.
- Mensalidade: o mestre digita `150,00`; a API recebe `"150.00"`; a tela mostra `R$ 150,00`.
- Sem testes automáticos de frontend na V1 (spec 7.2). A verificação de cada task é `npx tsc -b && npm run lint` + a checagem manual no navegador descrita nela. A pipeline completa (`npm run build` + backend) roda **uma vez, no final**.
- Modo de execução combinado: Claude aplica o código e, ao fim de cada task, explica só os conceitos novos de React/TS em poucas linhas, comparando com Python. Sem perguntas de fixação.
- Nunca sobrescrever arquivos do frontend com `cat >` com o Vite rodando (módulo vazio → tela branca): usar Write/Edit.
- Branch `feat/students-frontend`; um commit por task (`tipo: descrição` em inglês, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`).

## Review Focus

- **Cadastro com 2 modalidades em que a 2ª é inválida** (modalidade não oferecida): esperado que nada seja gravado (nem aluno, nem a 1ª matrícula). → Task 0.

- **Digitar rápido na busca:** "an", "ana", "ana l". Esperado: só o resultado da última busca aparece; respostas atrasadas de buscas antigas nunca sobrescrevem a lista. → Task 3 (AbortController + checagem manual).
- **URL estranha** (`?pagina=abc`, `?pagina=999`, `?modalidade=<uuid inexistente>`): esperado lista vazia com mensagem e caminho de volta, nunca tela quebrada. → Task 3.
- **Mensalidade com vírgula** (`150,00`, `1.500,50`, `abc`): esperado salvar `150.00` / `1500.50`, e erro no campo para `abc`, nunca 422 genérico. → Task 1 (`parseMoney`) + Tasks 7 e 8.
- **CEP inexistente ou serviço fora:** esperado aviso discreto e os campos livres para preencher à mão; nunca travar o formulário. → Task 5.
- **Clique duplo em "Salvar"/"Cadastrar":** esperado uma única gravação (botão desabilitado enquanto `isPending`). → Tasks 5–8.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `frontend/src/lib/api/errors.ts` (criar) | Tabela `code → texto`, `showApiError()`, `applyFieldErrors()` (422 → campos) |
| `frontend/src/lib/money.ts` (criar) | `parseMoney('1.500,50') → '1500.50'`, `formatMoney('150.00') → 'R$ 150,00'` |
| `frontend/src/lib/hooks/useDebouncedValue.ts` (criar) | Valor que só muda 300 ms depois da última digitação |
| `frontend/src/components/ui/{select,dialog,checkbox,sonner}.tsx` (criar via shadcn) | Componentes base |
| `frontend/src/main.tsx` (modificar) | `<Toaster />` |
| `frontend/src/features/students/api.ts` (criar) | Chamadas tipadas da API de alunos e CEP |
| `frontend/src/features/students/hooks.ts` (criar) | `useStudents`, `useStudent`, `useCep`, hooks de escrita |
| `frontend/src/features/students/labels.ts` (criar) | Textos de parentesco, sexo e status |
| `frontend/src/features/students/schemas.ts` (criar) | Schemas Zod dos formulários (reaproveitados no cadastro e na ficha) |
| `frontend/src/features/students/pages/StudentsPage.tsx` (reescrever) | Lista com dados reais |
| `frontend/src/features/students/pages/StudentDetailPage.tsx` (reescrever) | Ficha com dados reais |
| `frontend/src/features/students/components/tabs/*.tsx` (criar) | Uma aba por arquivo: `EnrollmentsTab`, `BasicDataTab`, `AddressTab`, `ResponsiblesTab` |
| `frontend/src/features/students/components/AddressFields.tsx` (criar) | Campos de endereço + CEP automático (ficha e cadastro) |
| `frontend/src/features/students/components/ResponsibleForm.tsx` (criar) | Campos de responsável (ficha e cadastro) |
| `frontend/src/features/students/pages/NewStudentPage.tsx` (criar) | Cadastro em 4 etapas |
| `frontend/src/features/students/components/{StudentListItem,EnrollmentCard}.tsx` (modificar) | Passam a receber os tipos da API |
| `frontend/src/features/students/{mock-data,types}.ts` (apagar) | Saem os dados fictícios |
| `frontend/src/features/belts/components/BeltDrawing.tsx` (criar) | Desenho SVG da faixa (spec das faixas) |
| `frontend/src/features/belts/mock.ts` (criar) | Faixas e histórico fictícios por matrícula, em memória (sai na integração das faixas) |
| `frontend/src/features/students/components/StudentAvatar.tsx` (modificar) | Silhueta Lucide em fundo lavanda |
| `frontend/src/app/router.tsx` (modificar) | Rota `/app/alunos/novo` |
| `frontend/src/lib/api/schema.d.ts` (regenerar) | Tipos do OpenAPI atual (inclui faixas, sem uso ainda) |

---

### Task 0: Backend · cadastro com várias matrículas

**Files:** `src/dojoflow/schemas/student_api.py`, `src/dojoflow/api/routes/students.py`, `tests/api/test_students_api.py`, `tests/api/test_students_belt.py`

**Interfaces — Produces:** `StudentCreateApiRequest.enrollments: list[EnrollmentApiPayload]` (1 a 10 itens, modalidades distintas; repetida → 422) **no lugar** de `enrollment`. A rota cria o aluno com a primeira e adiciona as outras (`add_enrollment`), com a faixa atual opcional de cada uma, tudo num único `unit_of_work` (qualquer erro desfaz tudo). O bot não muda (usa o schema interno).

- [ ] **Step 1:** Testes: criar com 2 matrículas → ficha com as 2; 2ª modalidade não oferecida → 404 `MODALITY_NOT_ENABLED` e `GET /students` com total 0; modalidade repetida → 422; lista vazia → 422. Ajustar os testes existentes para `enrollments: [...]`.
- [ ] **Step 2:** Rodar e ver falhar; implementar; rodar os arquivos de alunos e ver passar.
- [ ] **Step 3:** Commit `feat: create a student with several enrollments`.

---

### Task 1: Base: bibliotecas, componentes, erros e dinheiro

**Files:** `package.json`, `components/ui/{select,dialog,checkbox,sonner}.tsx`, `main.tsx`, `lib/api/errors.ts`, `lib/money.ts`, `lib/api/schema.d.ts`

**Interfaces — Produces:**
- `showApiError(error: unknown, fallback?: string): void` — toast com o texto da tabela pelo `code`; sem `code` (rede/500) → "Não foi possível falar com o servidor. Tente de novo."
- `applyFieldErrors<T extends FieldValues>(error: unknown, setError: UseFormSetError<T>): boolean` — se for 422 do FastAPI, marca cada campo (`loc` → nome do campo) e devolve `true`.
- `ERROR_MESSAGES: Record<string, string>` com pelo menos: `STUDENT_NOT_FOUND`, `ENROLLMENT_NOT_FOUND`, `ENROLLMENT_ALREADY_EXISTS`, `MODALITY_NOT_FOUND`, `MODALITY_NOT_ENABLED`, `RESPONSIBLE_LINK_NOT_FOUND`, `CEP_NOT_FOUND`, `CONFLICT`, `NOT_FOUND`.
- `parseMoney(text: string): string | null` (`'150,00'`→`'150.00'`, `'1.500,50'`→`'1500.50'`, `'150'`→`'150.00'`, `'abc'`/`'-1'`→`null`) e `formatMoney(value: string | null): string` (`'150.00'`→`'R$ 150,00'`, `null`→`'—'`).

- [ ] **Step 1:** Conferir versões atuais e instalar `react-hook-form`, `zod`, `@hookform/resolvers`; adicionar via `npx shadcn@latest add select dialog checkbox sonner`.
- [ ] **Step 2:** Com a API rodando (`poetry run task run`), `npm run gen:api`.
- [ ] **Step 3:** Criar `errors.ts` e `money.ts`; `<Toaster />` em `main.tsx`.
- [ ] **Step 4:** Verificar: `npx tsc -b && npm run lint` limpos; `npm run dev`, login e tudo como antes.
- [ ] **Step 5:** Commit `chore: form libraries, toasts and api error helpers`.

---

### Task 2: Fase 7 · Dados da lista (API + hook)

**Files:** `features/students/api.ts`, `features/students/hooks.ts`, `lib/hooks/useDebouncedValue.ts`

**Interfaces — Produces:**
- `type StudentFilters = { search: string; status: 'active' | 'inactive' | null; modalityId: string | null; page: number }`
- `listStudents(filters: StudentFilters, signal?: AbortSignal): Promise<Schemas['StudentPageRead']>` (`page_size` 20; `search` vazio não é enviado)
- `useStudents(filters: StudentFilters): { data: Schemas['StudentPageRead'] | null; isLoading: boolean; error: unknown; refetch: () => void }` — cancela a requisição anterior quando os filtros mudam.
- `useDebouncedValue<T>(value: T, delayMs = 300): T`

- [ ] **Step 1:** Implementar os três.
- [ ] **Step 2:** Verificar: `npx tsc -b && npm run lint`.
- [ ] **Step 3:** Commit `feat: students list api and hook`.

---

### Task 3: Fase 7 · Tela da lista com dados reais

**Files:** `pages/StudentsPage.tsx`, `components/StudentListItem.tsx`

**Interfaces — Consumes:** `useStudents`, `useDebouncedValue` (Task 2); `listAcademyModalities` (já existe).

Comportamento:
- Filtros lidos de `useSearchParams`: `busca`, `status` (`ativos` padrão | `inativos`), `modalidade` (UUID), `pagina` (inteiro ≥ 1; inválido → 1).
- O campo de busca tem estado local; o valor com 300 ms de espera vai para a URL e zera a `pagina`.
- Chips Ativos/Inativos (mantém o visual atual) e seletor de modalidade (só as oferecidas pela academia, + "Todas").
- Paginação: "Anterior / Próxima" e "página X de Y" a partir de `total` e `page_size`.
- Estados: carregando (esqueleto simples), erro (mensagem + "Tentar de novo" → `refetch`), vazio sem filtro ("Nenhum aluno ainda" + botão Novo aluno), vazio com filtro ("Nenhum aluno encontrado" + "Limpar filtros").
- `StudentListItem` recebe `Schemas['StudentListItemRead']` e mostra `modalities.join(' · ')`.
- A ficha (rota filha) ainda usa os dados fictícios até a Task 4.

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** Verificar `npx tsc -b && npm run lint`. No navegador: os alunos do banco aparecem; digitar rápido "an"→"ana" mostra só o último resultado (aba Rede: requisições antigas *canceladas*); `?pagina=abc` e `?pagina=999` não quebram; recarregar a página mantém os filtros.
- [ ] **Step 3:** Commit `feat: students list with search, filters and pagination`.

---

### Task 4: Fase 8 · Ficha com dados reais (leitura) e fim dos dados fictícios

**Files:** `api.ts`, `hooks.ts`, `labels.ts`, `pages/StudentDetailPage.tsx`, `components/tabs/*.tsx`, `components/EnrollmentCard.tsx`; apagar `mock-data.ts` e `types.ts`

**Interfaces — Produces:**
- `getStudent(id: string, signal?: AbortSignal): Promise<Schemas['StudentDetailRead']>`; `useStudent(id: string)` no contrato de leitura; 404 → `error.code === 'STUDENT_NOT_FOUND'`.
- `RELATIONSHIP_LABELS` (`self` "O próprio aluno", `father` "Pai", `mother` "Mãe", `grandmother` "Avó", `grandfather` "Avô", `uncle` "Tio", `aunt` "Tia", `brother` "Irmão", `sister` "Irmã"), `SEX_LABELS` (`male` "Masculino", `female` "Feminino", `other` "Outro").
- Cada aba é um componente que recebe `student: Schemas['StudentDetailRead']` e `onChanged: () => void` (a ficha passa `refetch`).

- [ ] **Step 1:** Implementar a leitura das 4 abas (mesmo visual de hoje; `EnrollmentCard` com `formatMoney`); `StudentAvatar` vira a silhueta Lucide (`UserRound`) em fundo `bg-chip-active`; estado de "Aluno não encontrado" com link para a lista; apagar os dados fictícios.
- [ ] **Step 2:** Verificar `npx tsc -b && npm run lint`; no navegador, abrir alunos reais; uma URL com UUID inválido mostra "Aluno não encontrado".
- [ ] **Step 3:** Commit `feat: student detail with real data`.

---

### Task 5: Fase 8 · Editar Dados e Endereço (com CEP automático)

**Files:** `api.ts`, `hooks.ts`, `schemas.ts`, `components/AddressFields.tsx`, `tabs/BasicDataTab.tsx`, `tabs/AddressTab.tsx`

**Interfaces — Produces:**
- `basicDataSchema` e `addressSchema` (Zod, regras dos Global Constraints; strings vazias viram `null` antes de enviar).
- `useUpdateStudent(id)`, `useSaveAddress(id)`, `useRemoveAddress(id)` no contrato de escrita.
- `lookupCep(zip: string, signal?: AbortSignal)` e `useCep()`: ao completar 8 dígitos, preenche rua, bairro, cidade e UF; CEP inexistente/erro → aviso "CEP não encontrado, preencha à mão" sem bloquear.
- `<AddressFields form={...} />`: os campos de endereço + CEP automático, usados aqui e na Task 9.

Comportamento: cada aba mostra os dados e um botão **Editar**; editando, vira formulário com **Salvar** (desabilitado durante `isPending`) e **Cancelar**. 422 → erro no campo; outros erros → toast. Sucesso → toast "Salvo" + `onChanged()`. Endereço tem **Remover endereço** com confirmação (`AlertDialog`).

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** Verificar `npx tsc -b && npm run lint`; no navegador: editar nome e telefone; nome com 1 letra mostra erro no campo; CEP válido preenche; CEP `00000000` mostra o aviso e deixa digitar; remover endereço pede confirmação.
- [ ] **Step 3:** Commit `feat: edit student data and address`.

---

### Task 6: Fase 8 · Responsáveis (adicionar e remover)

**Files:** `api.ts`, `hooks.ts`, `schemas.ts`, `components/ResponsibleForm.tsx`, `tabs/ResponsiblesTab.tsx`

**Interfaces — Produces:** `responsibleSchema`; `useAddResponsible(studentId)`, `useRemoveResponsible(studentId)`; `<ResponsibleForm form={...} />` (nome, telefone, WhatsApp, e-mail, parentesco), usado aqui e na Task 9.

Comportamento: lista com nome, parentesco (texto de `RELATIONSHIP_LABELS`, sem `self`), telefone e "WhatsApp"; sem responsáveis → "O próprio aluno é o responsável"; **Adicionar outra pessoa** abre um `Dialog` com o formulário; **Remover** pede confirmação. Editar um responsável existente está fora da V1 (spec): remove e adiciona de novo.

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** Verificar `npx tsc -b && npm run lint`; no navegador: adicionar e remover; telefone com 9 dígitos dá erro no campo.
- [ ] **Step 3:** Commit `feat: add and remove student responsibles`.

---

### Task 7: Fase 8 · Matrículas (editar e adicionar)

**Files:** `api.ts`, `hooks.ts`, `schemas.ts`, `tabs/EnrollmentsTab.tsx`

**Interfaces — Produces:** `enrollmentSchema` (modalidade, mensalidade em texto via `parseMoney`, vencimento 1–28 ou vazio, isenta, status); `useUpdateEnrollment(studentId)`, `useAddEnrollment(studentId)`.

Comportamento: cada card ganha **Editar** (`Dialog`: mensalidade, vencimento, isenta, ativa/inativa); **Nova matrícula** abre o mesmo formulário com o seletor de modalidade (só as oferecidas pela academia e em que o aluno ainda não está matriculado) e, se a modalidade tiver faixas no mock, "Faixa atual" + "Desde" (só no mock). Cada card mostra o bloco de faixa do mock: `BeltDrawing`, nome, "há X meses e Y dias", Apto / Ainda não · apto a partir de…, **Registrar graduação** (próxima faixa marcada) e **Histórico**; sem faixa → **Registrar faixa atual**. Isenta marcada → mensalidade e vencimento desabilitados. `ENROLLMENT_ALREADY_EXISTS` → toast.

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** Verificar `npx tsc -b && npm run lint`; no navegador: editar mensalidade com `150,00` salva e mostra `R$ 150,00`; `abc` dá erro no campo; vencimento 29 dá erro; nova matrícula numa modalidade que ele já tem não aparece na lista.
- [ ] **Step 3:** Commit `feat: edit and add student enrollments`.

---

### Task 8: Fase 9 · Cadastro em 4 etapas

**Files:** `api.ts`, `hooks.ts`, `pages/NewStudentPage.tsx`, `app/router.tsx`, `pages/StudentsPage.tsx` (botão vira link)

**Interfaces — Consumes:** `basicDataSchema`, `addressSchema`, `responsibleSchema`, `enrollmentSchema`, `<AddressFields>`, `<ResponsibleForm>` (Tasks 5–7). **Produces:** `useCreateStudent()`.

Comportamento:
- Rota `/app/alunos/novo` em **tela própria**, fora do mestre-detalhe (o formulário precisa de espaço); o botão "Novo aluno" leva para ela.
- Um único formulário (React Hook Form) dividido em etapas: **1 Dados** → **2 Endereço** (opcional, com CEP automático e "Pular") → **3 Responsáveis** (escolha: "O próprio aluno é o responsável" padrão, ou "Outra pessoa" com 1 ou mais) → **4 Matrículas** (um bloco por modalidade, "+ Outra modalidade", remover bloco; cada bloco: modalidade, mensalidade, vencimento, isenta e, se houver faixas no mock, "Faixa atual" + "Desde").
- "Próximo" valida só os campos da etapa atual; "Voltar" mantém o que foi digitado. Indicador "Etapa X de 4".
- "Cadastrar" envia tudo num único `POST /students` (com `enrollments: [...]`; a faixa do mock não vai), desabilitado enquanto `isPending`; sucesso → toast + vai para `/app/alunos/:id`. 422 → volta para a etapa do campo com erro.
- Academia sem modalidade oferecida: a etapa 4 avisa e aponta para Configurações.
- Recarregar a página no meio do cadastro perde o que foi digitado (aceito na V1).

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** Verificar `npx tsc -b && npm run lint`; no navegador: cadastro completo; cadastro pulando endereço e sem responsável; "Próximo" com nome vazio não avança; clique duplo em "Cadastrar" cria um aluno só; o aluno novo aparece na lista.
- [ ] **Step 3:** Commit `feat: new student wizard`.

---

### Task 9: Fechamento

- [ ] **Step 1:** Pipeline completa, uma vez: `npx tsc -b && npm run lint && npm run build` no frontend; no backend nada mudou, mas rodar `poetry run task test` para garantir.
- [ ] **Step 2:** Passeio no navegador, celular (DevTools, 390 px) e desktop: lista → ficha → editar cada aba → novo aluno. Este passeio é do Thiago: o Claude não tem navegador nesta sessão; as checagens manuais das tasks entram neste roteiro.
- [ ] **Step 3:** Atualizar o Obsidian: checkboxes do Plano B (Fases 4 e 6 já feitas; 7, 8 e 9 agora) e o diário de sessões.
- [ ] **Step 4:** Commit final (se houver ajustes) e avisar o Thiago para revisar e decidir o PR.
