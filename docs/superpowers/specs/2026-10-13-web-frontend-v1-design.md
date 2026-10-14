# DojoFlow Web — V1 (design)

- **Data:** 2026-10-13
- **Status:** aguardando revisão
- **Escopo:** frontend web (React) + ajustes no backend FastAPI necessários para ele
- **Próxima fase:** V2 — mensalidades e dashboard financeiro (spec própria)

---

## 1. Contexto e objetivo

O DojoFlow é um gerenciador de mensalidades para academias de artes marciais. Hoje o mestre (dono/professor) opera tudo por um bot do Telegram. O backend já tem autenticação por e-mail/senha e rotas REST de alunos e modalidades, mas não existe interface web.

**Objetivo da V1:** um site onde o mestre faz login, vê um dashboard e faz os cadastros e consultas que o backend já suporta (alunos, endereço, responsáveis, matrículas, modalidades).

**Papéis dos canais:**

- **Site** — canal principal: dashboard, cadastros completos, consultas.
- **Bot do Telegram** — atalho rápido para cadastros do dia a dia. Não ganha dashboard nem relatórios.
- Toda regra de negócio fica nos *services* do backend; site e bot chamam o mesmo código.

**Critério de sucesso:** o mestre consegue, só pelo site (celular ou computador), entrar, ver o resumo da academia, cadastrar um aluno completo, editá-lo, consultá-lo e gerenciar as modalidades da academia.

## 2. Escopo

### Dentro da V1

- Login, cadastro de conta, logout, sessão persistente
- Definir/redefinir acesso via link enviado pelo bot do Telegram
- Dashboard simples (sem dados financeiros)
- Alunos: lista com busca/filtros/paginação, ficha, cadastro em etapas, edição
- Endereço (com preenchimento por CEP), responsáveis, matrículas
- Modalidades: ativar/desativar a partir do catálogo
- Configurações: dados do mestre e "Conectar Telegram"
- Preparação barata para um futuro portal do aluno (seção 4.1)

### Fora da V1

| Item | Motivo | Quando |
|---|---|---|
| Mensalidades, pagamentos, dashboard financeiro | Backend ainda não existe | V2 |
| TanStack Query | Mestre está estudando `useState`/`useEffect`; migração planejada | Início da V2 |
| Portal do aluno/responsável | Custo alto agora, barato depois com a preparação | Após V2 |
| Papéis além do mestre (funcionários) | Sem demanda | A definir |
| "Esqueci minha senha" por e-mail | Não há envio de e-mail; substituído pelo fluxo do Telegram | A definir |
| Reaproveitar endereço/responsável de outro aluno no site | O bot já faz; no site cadastra-se novo | Se fizer falta |
| Editar dados de um responsável existente | Na V1: remover vínculo e adicionar outro | Se fizer falta |
| Testes de frontend (unitários e E2E) | Decisão de escopo da V1 | A definir |
| Atualização otimista na interface | Simplicidade | A definir |

## 3. Arquitetura e stack

### 3.1 Estrutura (monorepo)

```
dojoflow/
├── src/dojoflow/            backend (existente)
├── tests/                   testes do backend
├── migrations/
├── frontend/                novo
│   ├── src/
│   │   ├── app/             roteamento, providers, layout (sidebar / barra inferior)
│   │   ├── features/
│   │   │   ├── auth/        login, cadastro, definir acesso, sessão, guarda de rota
│   │   │   ├── dashboard/
│   │   │   ├── students/    lista, ficha, formulários, hooks
│   │   │   ├── modalities/
│   │   │   └── settings/
│   │   ├── components/ui/   componentes shadcn/ui
│   │   ├── lib/             cliente HTTP, refresh, utilitários
│   │   └── api/schema.d.ts  tipos gerados do OpenAPI (não editar à mão)
│   └── package.json
└── compose.yml
```

Organização **por funcionalidade**: tudo de um domínio fica junto.

### 3.2 Stack do frontend

| Camada | Escolha |
|---|---|
| Build | Vite + React + TypeScript |
| Estilo | Tailwind CSS v4 + shadcn/ui |
| Ícones | Lucide (traço fino, vazados) |
| Rotas | React Router |
| Dados do servidor | Hooks próprios com `useState`/`useEffect` (seção 6.3) |
| Formulários | React Hook Form + Zod |
| Tipos da API | `openapi-typescript` + `openapi-fetch` |

As versões são verificadas na documentação oficial no momento da instalação.

### 3.3 Integração frontend ↔ backend

- **Dev:** o Vite faz proxy de `/api` para o FastAPI (`localhost:8000`). O navegador vê uma única origem, e o cookie do refresh funciona sem CORS.
- **Produção:** um proxy reverso (Nginx/Caddy, no Hetzner) serve o build estático e encaminha `/api` para o FastAPI. O deploy não faz parte desta spec.
- **Tipos:** um script `npm run gen:api` gera `src/api/schema.d.ts` a partir de `/openapi.json`. O arquivo é commitado, e o CI falha se ele estiver dessincronizado.

## 4. Mudanças no backend

### 4.1 Preparação para o portal do aluno (regra dos R$ 10)

1. **`public_id` (UUID) nas URLs e respostas.** Todas as rotas que recebem identificador de recurso (`/students/{id}`, `/academy/modalities/{id}/toggle`, responsáveis etc.) passam a receber o `public_id`, e as respostas expõem `id = public_id`. A conversão para o `id` interno acontece na camada de rotas, por dependency. Os *services* continuam recebendo `int`, então o bot não muda.
2. **Claim `role: "master"` no JWT.** O `CurrentMasterDep` rejeita tokens sem esse papel.
3. **Prefixo `/portal/*` reservado** na API e no site. Nenhum código agora.

Fica de fora, de propósito: generalizar `Master` em uma tabela `User`. O portal futuro terá credenciais próprias ligadas a `Student`/`Responsible`.

### 4.2 Segurança

1. **Remover `GET /api/v1/masters/context/{telegram_user_id}`.** Hoje a rota não exige autenticação e expõe o contexto do mestre e da academia a quem souber um ID de Telegram. O bot usa o service diretamente.
2. **Refresh token em cookie com rotação.**
   - `POST /auth/login`, `/auth/register`, `/auth/refresh` e `/auth/set-credentials` gravam o refresh em cookie `httpOnly`, `Secure` (desligado só em dev), `SameSite=Lax`, `Path=/api/v1/auth`. O corpo da resposta traz só o `access_token`.
   - Nova tabela `refresh_session`: `id`, `master_id`, `token_hash`, `expires_at`, `revoked_at`, `created_at`, `replaced_by_id`.
   - A cada refresh, a sessão atual é revogada e uma nova é emitida.
   - **Detecção de reuso:** apresentar um refresh já revogado revoga todas as sessões do mestre e retorna 401.
   - Novo `POST /auth/logout`: revoga a sessão atual e apaga o cookie.
3. **`set-credentials` exige a senha atual quando a chamada é autenticada.** Com token de setup do Telegram, não exige (o token de uso único prova a identidade). Um token de setup informado tem precedência sobre um bearer token: o bearer é ignorado (mesmo expirado ou inválido). Trocar a senha revoga todas as `refresh_session` do mestre.
4. **Proteção no boot.** Nova configuração `ENVIRONMENT` (`dev` | `prod`). Fora de `dev`, a aplicação não inicia se `JWT_SECRET` estiver no valor padrão.
5. **O header secreto do webhook do Telegram** passa a ser comparado com `secrets.compare_digest`.

### 4.3 API para o site

1. **Toda rota com `response_model` tipado.** O `GET /students/{id}` (hoje `dict[str, Any]`) ganha o schema `StudentDetailRead` (`student`, `address`, `responsibles`, `enrollments`).
2. **Lista paginada:** `GET /students?search=&modality_id=&status=&page=&page_size=` → `{items, total, page, page_size}`. O `modality_id` recebe o `public_id` da modalidade (como todo identificador exposto); `status` é o status da matrícula (`active` | `inactive`); `page` começa em 1; `page_size` vai de 1 a 100, com padrão 20.
3. **`DELETE /students/{id}/responsibles/{responsible_id}`** (o service `remove_responsible_link` já existe).
4. **`GET /dashboard/summary`**, com:
   - `active_students`: alunos com ao menos uma matrícula ativa
   - `students_by_modality`: lista de `{modality, count}`, considerando só matrículas ativas
   - `recent_enrollments`: últimas 5, com aluno, modalidade e data
   - `registration_pending`: matrículas ativas, não isentas, sem `monthly_fee` ou sem `due_day`, com aluno e modalidade
5. **`GET /cep/{zip_code}`**, usando o `CepService` existente.
6. **Formato de erro padronizado:** `{"detail": "...", "code": "STUDENT_NOT_FOUND"}`. As exceções de domínio ganham um `code`. O 422 do Pydantic mantém o formato padrão do FastAPI.
7. **Bot: comando `/web`** passa a enviar um link `https://<site>/definir-acesso?token=<setup_token>` em vez do código cru com o nome do endpoint. A URL base vem de uma nova configuração `WEB_APP_URL`.

### 4.4 Fundação (pré-requisito)

1. **Transações unificadas:** o service é dono da unidade de trabalho; repositórios sem `@transactional`; nenhum `commit()`/`rollback()` manual (remover os de `services/telegram_conversation_state.py`).
2. **Testes do backend rodando em Postgres**, no lugar do SQLite.

## 5. Telas e navegação

### 5.1 Estilo visual

Referência aprovada (mockup `navigation-layout-v2`):

- Fundo em gradiente lavanda suave (`#e2e5fb → #f1f2fe`); painéis brancos "flutuando"
- Cor primária índigo (`#4f46e5`); bordas arredondadas grandes (~24px em painéis, pílula em botões e busca)
- Fonte sans geométrica (Outfit)
- Ícones Lucide vazados, de traço fino (~1.6)
- Status como chips pastel com borda colorida à esquerda: azul = ativa, verde = isenta, amarelo = pendência de cadastro, cinza = inativa
- Avatares com iniciais em fundo pastel
- Abas com sublinhado discreto; ações secundárias como botão-fantasma

### 5.2 Layout responsivo (celular e desktop com o mesmo peso)

- **Desktop:** sidebar fina só com ícones (Dashboard, Alunos, Modalidades; Configurações embaixo). O item ativo fica num círculo índigo preenchido. Telas de lista usam o padrão mestre-detalhe (lista à esquerda, ficha à direita).
- **Celular:** barra inferior com os mesmos ícones. Lista em tela cheia; tocar num item abre a ficha em tela cheia.

### 5.3 Rotas

| Rota | Conteúdo |
|---|---|
| `/login` | E-mail e senha. Links: "Criar conta" e "Esqueceu a senha? Envie /web para o bot". Desktop: painel índigo com a proposta do produto + formulário. Celular: só o cartão |
| `/cadastro` | Criar conta (`/auth/register`) |
| `/definir-acesso?token=` | E-mail e nova senha a partir do link do bot; entra logado ao salvar |
| `/app` | Dashboard: cards de alunos ativos e pendências de cadastro, alunos por modalidade, matrículas recentes |
| `/app/alunos` | Lista com busca, filtros (status, modalidade) e paginação; filtros refletidos na URL |
| `/app/alunos/novo` | Cadastro em 4 etapas: dados → endereço (CEP automático) → responsáveis → matrícula |
| `/app/alunos/:id` | Ficha com abas Matrículas, Dados, Endereço, Responsáveis, cada uma editável |
| `/app/modalidades` | Catálogo com botão de ativar/desativar na academia |
| `/app/configuracoes` | Dados do mestre, trocar senha (exige a atual), "Conectar Telegram" (gera link de vínculo) |
| `/portal/*` | Reservado |

Caminhos em português (visíveis ao usuário); código em inglês.

## 6. Autenticação, dados e erros

### 6.1 Sessão

1. **Login:** o access token fica em memória (contexto React de auth); o refresh fica no cookie `httpOnly`.
2. **Ao carregar o site:** chama `POST /auth/refresh` antes de renderizar a área logada. Sucesso → `/app`; falha → `/login`. Mostra um estado de carregamento enquanto isso.
3. **401 durante o uso:** o cliente HTTP faz **um único** refresh, mesmo com várias requisições simultâneas falhando (todas aguardam a mesma promessa), e repete as requisições originais. Se o refresh falhar, vai para `/login`. Essa lógica fica isolada em `lib/` num módulo pequeno.
4. **Guarda de rota:** `/app/*` exige sessão; `/login` redireciona para `/app` se já houver sessão.
5. **Logout:** `POST /auth/logout`, limpa o estado e vai para `/login`.

### 6.2 Redefinir acesso pelo Telegram

O mestre envia `/web` ao bot → recebe o link `/definir-acesso?token=…` (uso único, 15 minutos) → define e-mail e senha → entra logado.

### 6.3 Dados (sem biblioteca de cache na V1)

- Nenhuma tela chama `fetch` diretamente. Cada recurso tem um hook em `features/<domínio>/hooks.ts` (`useStudents`, `useStudent`, `useDashboard`, `useModalities`, `useModalityCatalog`, `useCep`).
- **Contrato dos hooks de leitura:** `{ data, isLoading, error, refetch }`, o mesmo formato do TanStack Query, para que a migração da V2 só altere o miolo dos hooks.
- **Hooks de escrita** (`useCreateStudent`, `useUpdateEnrollment`…) expõem `{ mutate, isPending, error }`. Depois do sucesso, a tela chama `refetch()` do que exibe.
- Toda busca usa `AbortController` na função de limpeza do `useEffect`. Isso cobre a corrida de respostas na busca com digitação, o StrictMode em dev e o componente que sai da tela antes da resposta.
- A busca na lista espera 300ms após a digitação antes de consultar.
- Filtros e página da lista ficam na query string.

### 6.4 Erros

- 422 → erros mapeados para os campos do formulário.
- 401 → fluxo de refresh (6.1).
- 404, 409, 500 e falha de rede → toast com mensagem em português.
- As mensagens em português vêm de uma tabela `code → texto` no frontend, com uma mensagem genérica como fallback. Sem biblioteca de i18n.
- Estados vazios e de erro próprios em cada lista e ficha, com chamada para ação.

## 7. Testes e CI

### 7.1 Backend (pytest em Postgres)

Os testes existentes continuam passando. Testes novos:

- Refresh: rotação; reuso de token revogado derruba todas as sessões; logout
- `set-credentials`: autenticado sem senha atual → 403 (`CURRENT_PASSWORD_INVALID`; um 401 acionaria o fluxo de refresh do 6.4); com senha atual → troca e revoga sessões; token de setup funciona uma única vez
- JWT sem `role` → 401
- `public_id` de outra academia → 404
- Rota `/masters/context/...` removida → 404
- Paginação e filtros da lista de alunos; `dashboard/summary`; remoção de vínculo de responsável; `/cep`
- Contrato: nenhuma rota do `/openapi.json` sem schema de resposta

### 7.2 Frontend

Sem testes na V1 (decisão de escopo). Checagens estáticas no CI:

- `tsc --noEmit`
- ESLint
- Sincronia dos tipos do OpenAPI: o CI regenera o `schema.d.ts` e falha se houver diferença

### 7.3 CI (GitHub Actions)

- **Backend:** `ruff check`, `typos`, `pytest` com Postgres como serviço
- **Frontend:** as checagens de 7.2

## 8. Ordem de implementação sugerida

1. Fundação: testes em Postgres, transações unificadas, CI do backend (4.4)
2. Segurança e auth: remoção da rota aberta, `ENVIRONMENT`, `compare_digest`, `role` no JWT, `refresh_session` + cookie + logout, correção do `set-credentials` (4.1, 4.2)
3. API: `public_id`, schemas tipados, paginação, dashboard, CEP, remoção de responsável, códigos de erro, link do `/web` (4.1, 4.3)
4. Frontend: scaffold, tema e layout, auth e sessão, geração de tipos, CI do frontend
5. Telas: login/cadastro/definir acesso → modalidades → alunos (lista, ficha, edição, cadastro em etapas) → dashboard → configurações

## 9. Prévia da V2 (fora desta spec)

- Backend de mensalidades: gerar cobranças, registrar pagamento (com alocação), listar inadimplentes, resumo do mês
- Migração dos hooks para TanStack Query (primeira tarefa)
- Dashboard financeiro (recebido / pendente / atrasado)
- Decisões de domínio pendentes: geração das cobranças (job, sob demanda ou lazy), status "atrasado" gravado ou calculado, regra de alocação de pagamento parcial, tratamento de `PENDING_CONFIGURATION`
