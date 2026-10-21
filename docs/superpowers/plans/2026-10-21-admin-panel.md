# Painel administrativo — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Painel só do Thiago em `admin.katsuflow.com.br` (listar, criar,
editar, trocar senha, ativar/desativar academias) + modo suporte (entrar nos
dados de uma academia como o próprio Thiago, até 8 h).

**Architecture:** Backend FastAPI ganha `ADMIN_EMAIL`, rotas `/api/v1/admin/*`
e um "contexto de suporte": a sessão de refresh e o token de acesso carregam a
academia vista, e `_get_current_master` troca a academia do contexto num ponto
só. O site (um único build React) monta o roteador do painel quando aberto em
`admin.*`. O Caddy separa os dois endereços e fecha o cadastro público.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL 17, pytest;
React 19 + Vite + react-router + openapi-fetch + shadcn/ui; Caddy 2.10.

**Spec:** `docs/superpowers/specs/2026-10-21-admin-panel-design.md`

## Global Constraints

- Branch `feat/admin-panel` (criada da `feat/deploy`). Commits em inglês, com
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Banco de teste: `docker compose up -d postgres` (porta 5434) antes de rodar
  testes; banco local de dev em dia com `poetry run alembic upgrade head`.
- Ferramentas: `poetry run …` (nunca `uv run`, que recria a `.venv`).
- Rodar os testes da própria tarefa ao longo dela; suíte inteira
  (`poetry run task test`, `ruff check`, `ruff format --check`, `typos .`,
  `npm run build`, `npm run lint`) só uma vez, no fim (Tarefa 7).
- Nunca `cat >` em arquivo do frontend com o Vite rodando (usar Edit/Write).
- Administrador: `settings.ADMIN_EMAIL` (padrão `''` = ninguém), comparado com
  o e-mail do mestre já normalizado (`strip().lower()`).
- Sessão de suporte: **8 horas** de prazo máximo, sem renovar além disso.
  Código de entrada: uso único, **60 segundos**.
- Textos do site em português; mensagem de bloqueio exata:
  **"Academia desativada. Fale com o suporte."**
- Telegram congelado: nenhuma mudança no bot.

## Review Focus

1. **Refresh da sessão de suporte** precisa manter a academia vista **e** o
   prazo original (não pode ganhar mais 8 h nem 14 dias a cada renovação) →
   teste na Tarefa 4.
2. **ADMIN_EMAIL muda (ou some) com uma sessão de suporte aberta** → a próxima
   chamada é recusada → teste na Tarefa 4.
3. **Academia desativada com mestre logado**: próxima chamada 401
   `ACADEMY_BLOCKED`, refresh também; mas o Thiago **entra** nela em modo
   suporte → testes nas Tarefas 1 e 4.
4. **Código de entrada reaproveitado, vencido, ou de outro tipo** (um
   `setup_token` do Telegram usado no lugar) → 401 `SUPPORT_CODE_INVALID` →
   teste na Tarefa 4.
5. **E-mail digitado com maiúsculas/espaços** na criação/edição, e e-mail que
   já existe → normaliza e devolve 409 `EMAIL_ALREADY_REGISTERED` no campo →
   testes na Tarefa 2.

---

### Task 1: Academia desativada não entra (backend)

**Files:**
- Modify: `src/dojoflow/services/auth.py` (`login`, `_create_session`)
- Modify: `src/dojoflow/api/dependencies/auth.py` (`_get_current_master`,
  `resolve_optional_master`)
- Test: `tests/api/test_academy_blocked.py`

**Interfaces:**
- Produces: erro `UnauthorizedError('Academy is blocked.',
  code='ACADEMY_BLOCKED')` em login, refresh e qualquer rota autenticada
  quando `academy_status == AcademyStatus.BLOCKED`.
- Produces: `async def resolve_master_context(master_service: MasterService,
  token: str) -> MasterContextRead` em `api/dependencies/auth.py` — ponto
  único que decodifica o token e monta o contexto; usado por
  `_get_current_master` e `resolve_optional_master` (a Tarefa 4 estende).

- [ ] **Step 1: Write the failing tests** (`tests/api/test_academy_blocked.py`;
  bloquear com `UPDATE academy SET status='blocked' WHERE id=SEED.academy_id`)

```python
async def test_login_refused_when_academy_blocked(client, db_session):
    # login com SEED.email / SEED.password
    assert response.status_code == 401
    assert response.json()['code'] == 'ACADEMY_BLOCKED'

async def test_refresh_refused_when_academy_blocked(client, db_session):
    # login ok → bloqueia → POST /auth/refresh com o cookie
    assert response.json()['code'] == 'ACADEMY_BLOCKED'

async def test_authenticated_call_refused_when_academy_blocked(client, db_session):
    # GET /api/v1/auth/me com auth_headers depois de bloquear
    assert response.status_code == 401
    assert response.json()['code'] == 'ACADEMY_BLOCKED'

async def test_reactivated_academy_logs_in_again(client, db_session):
    # bloqueia → login 401 → status='active' → login 200
```

- [ ] **Step 2:** `poetry run pytest tests/api/test_academy_blocked.py -q` →
  4 FAIL (hoje o login passa).
- [ ] **Step 3:** Checar o status em `login` (depois da senha conferir, para
  não revelar a situação a quem erra a senha), em `_create_session` (cobre
  refresh e `_start_session`) e em `resolve_master_context`.
- [ ] **Step 4:** Rodar de novo → PASS; `poetry run pytest
  tests/api/test_auth.py tests/api/test_auth_sessions.py -q` → PASS.
- [ ] **Step 5: Commit** `feat: blocked academies cannot log in or use the API`

---

### Task 2: Administrador e API do painel — listar e criar (+ comando)

**Files:**
- Modify: `src/dojoflow/core/settings.py` (`ADMIN_EMAIL: str = ''`)
- Modify: `src/dojoflow/services/security.py` (`generate_password`)
- Create: `src/dojoflow/services/admin.py` (`AdminService`)
- Create: `src/dojoflow/schemas/admin_api.py`
- Create: `src/dojoflow/api/dependencies/admin.py`
- Create: `src/dojoflow/api/routes/admin.py`; registrar em `main.py`
- Modify: `src/dojoflow/repositories/academy.py` (`list_with_master`)
- Create: `src/dojoflow/commands/create_academy.py`
- Modify: `deploy/env.prod.example` (`ADMIN_EMAIL=thiagotancredii@gmail.com`)
- Test: `tests/api/test_admin_api.py`, `tests/services/test_security_password.py`

**Interfaces:**
- Produces: `def is_admin(context: MasterContextRead) -> bool` em
  `api/dependencies/admin.py` (falso se `ADMIN_EMAIL` vazio ou se
  `context.support_mode` — este campo nasce na Tarefa 4; até lá, só e-mail).
- Produces: `CurrentAdminDep` (= `CurrentMasterDep` + `is_admin`, senão
  `ForbiddenError(code='ADMIN_ONLY')`).
- Produces: `def generate_password() -> str` — 12 caracteres de
  `abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789`, via `secrets`.
- Produces (schemas): `AdminMasterRead{id: UUID, name, email, phone}`,
  `AdminAcademyRead{id: UUID, name, status: AcademyStatus, created_at:
  datetime, master: AdminMasterRead | None, is_own: bool}`,
  `AdminAcademyCreate{academy_name: str(2–120), master_name: str(2–120),
  email: str(3–255, normalizado), phone: str | None (≤20)}`,
  `AdminCredentialsRead{academy: AdminAcademyRead, password: str}`.
- Produces (service): `AdminService.list_academies(search: str | None) ->
  list[AdminAcademyRead]` (busca em nome da academia **ou** do mestre,
  `ILIKE`, ordem por `created_at DESC`); `AdminService.create_academy(data:
  AdminAcademyCreate) -> AdminCredentialsRead` (reusa
  `OnboardingService.register_web` com a senha gerada).
- Produces (rotas): `GET /api/v1/admin/me -> MasterContextApiRead`,
  `GET /api/v1/admin/academies?search= -> list[AdminAcademyRead]`,
  `POST /api/v1/admin/academies -> 201 AdminCredentialsRead`.
- Produces (comando): `poetry run python -m dojoflow.commands.create_academy
  --academy-name … --master-name … --email … [--phone …]` → imprime e-mail e
  senha gerada.

- [ ] **Step 1: Write the failing tests** (`settings.ADMIN_EMAIL = SEED.email`
  via `monkeypatch` numa fixture `admin_headers`)

```python
@pytest.mark.parametrize('method,url', [
    ('GET', '/api/v1/admin/me'), ('GET', '/api/v1/admin/academies'),
    ('POST', '/api/v1/admin/academies'),
])
async def test_non_admin_gets_403(client, db_session, method, url):
    # other_academy_headers (não é ADMIN_EMAIL)
    assert response.status_code == 403
    assert response.json()['code'] == 'ADMIN_ONLY'

async def test_no_admin_when_admin_email_empty(client):  # ADMIN_EMAIL=''
    assert (await client.get('/api/v1/admin/me', headers=seed)).status_code == 403

async def test_create_academy_returns_password_and_master_can_log_in(client, admin_headers):
    # POST {academy_name:'Dojo Novo', master_name:'Mestre Novo',
    #       email:'  Novo@Dojo.TEST ', phone:'62988887777'}
    assert response.status_code == 201
    body = response.json()
    assert len(body['password']) == 12
    assert body['academy']['master']['email'] == 'novo@dojo.test'
    # POST /auth/login com novo@dojo.test + body['password'] → 200

async def test_create_academy_duplicate_email_conflict(client, admin_headers):
    # email = SEED.email
    assert response.status_code == 409
    assert response.json()['code'] == 'EMAIL_ALREADY_REGISTERED'

async def test_list_academies_search_and_is_own(client, admin_headers, db_session):
    # cria 'Dojo Tigre' (mestre 'Carlos') e outra; ?search=carl → só a Tigre
    # lista sem busca: a do SEED vem com is_own=True, as outras False

def test_generate_password_shape():
    pw = generate_password()
    assert len(pw) == 12 and not set(pw) & set('0O1lI')
```

- [ ] **Step 2:** `poetry run pytest tests/api/test_admin_api.py
  tests/services/test_security_password.py -q` → FAIL.
- [ ] **Step 3:** Implementar settings, `generate_password`, schemas,
  `list_with_master` (join academy → primeiro mestre por `master.id`),
  `AdminService`, dependência e rotas; `is_own` = academia do administrador.
- [ ] **Step 4:** Implementar `commands/create_academy.py` (argparse, no
  estilo de `seed_demo.py`; chama `AdminService.create_academy`; imprime
  "Academia criada. E-mail: … Senha: …"). Conferir à mão no banco local.
- [ ] **Step 5:** Rodar os testes → PASS.
- [ ] **Step 6: Commit** `feat: admin API to list and create academies`

---

### Task 3: API do painel — editar, trocar senha, ativar/desativar

**Files:**
- Modify: `src/dojoflow/services/admin.py`, `src/dojoflow/schemas/admin_api.py`,
  `src/dojoflow/api/routes/admin.py`
- Test: `tests/api/test_admin_api.py` (mesmo arquivo)

**Interfaces:**
- Consumes: `AdminService`, `CurrentAdminDep`, `generate_password`
  (Tarefa 2); `AuthService.revoke_all_sessions` (existente).
- Produces: `AdminAcademyUpdate{academy_name?, master_name?, email?, phone?}`
  (campos omitidos não mudam; `phone: null` apaga), `AdminStatusUpdate{status:
  AcademyStatus}`, `AdminPasswordRead{password: str}`.
- Produces (rotas, `{academy_id}` = `public_id` UUID da academia; 404
  `ACADEMY_NOT_FOUND`):
  `PATCH /api/v1/admin/academies/{academy_id} -> AdminAcademyRead`,
  `POST /api/v1/admin/academies/{academy_id}/reset-password ->
  AdminPasswordRead`,
  `POST /api/v1/admin/academies/{academy_id}/status -> AdminAcademyRead`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_update_academy_and_master(client, admin_headers, db_session):
    # PATCH outra academia {academy_name:'Novo Nome', email:' X@Y.TEST '}
    assert body['name'] == 'Novo Nome'
    assert body['master']['email'] == 'x@y.test'

async def test_update_email_conflict(client, admin_headers, db_session):
    assert response.json()['code'] == 'EMAIL_ALREADY_REGISTERED'  # 409

async def test_admin_cannot_change_own_email(client, admin_headers):
    # PATCH academia do SEED {email:'outro@x.test'}
    assert response.status_code == 409
    assert response.json()['code'] == 'ADMIN_EMAIL_LOCKED'

async def test_reset_password_revokes_sessions(client, admin_headers, db_session):
    # mestre da outra academia loga (cookie A) → reset → refresh com A → 401
    # login com a senha nova → 200; senha antiga → 401

async def test_block_logs_out_and_unblock_restores(client, admin_headers, db_session):
    # mestre loga → status blocked → refresh 401 ACADEMY_BLOCKED
    # → status active → login 200

async def test_cannot_block_own_academy(client, admin_headers):
    assert response.status_code == 409
    assert response.json()['code'] == 'CANNOT_BLOCK_OWN_ACADEMY'

async def test_unknown_academy_404(client, admin_headers):
    assert response.json()['code'] == 'ACADEMY_NOT_FOUND'
```

- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar no `AdminService`: `update_academy`,
  `reset_password` (hash novo + revogar sessões de todos os mestres da
  academia), `set_status` (ao bloquear, revogar sessões). Tudo
  `@transactional`.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5: Commit** `feat: admin API to edit academies, reset passwords and block`

---

### Task 4: Modo suporte (backend)

**Files:**
- Create: `migrations/versions/<rev>_support_mode.py` (`refresh_session.
  acting_academy_id` e `one_time_token.academy_id`, ambos `int FK academy`
  nullable) — `poetry run alembic revision --autogenerate -m "support mode"`
- Modify: `src/dojoflow/models/refresh_session.py`,
  `src/dojoflow/models/one_time_token.py`
- Modify: `src/dojoflow/services/security.py` (`create_access_token`)
- Modify: `src/dojoflow/services/auth.py` (`_create_session`,
  `_rotate_session`, `_issue_one_time_token`, novos métodos)
- Modify: `src/dojoflow/schemas/master_context.py` (`support_mode`)
- Modify: `src/dojoflow/api/dependencies/auth.py` (`resolve_master_context`)
- Modify: `src/dojoflow/api/routes/auth.py` (rota de troca; bloqueio das
  rotas de conta), `src/dojoflow/api/routes/admin.py` (rota de entrada)
- Modify: `src/dojoflow/shared/enums.py` (`AuditAction.SUPPORT_ENTRY =
  'support_entry'`; coluna é texto, sem migração de tipo)
- Test: `tests/api/test_support_mode.py`

**Interfaces:**
- Consumes: `is_admin`, `CurrentAdminDep` (Tarefa 2); `resolve_master_context`
  (Tarefa 1).
- Produces: `create_access_token(master_id: int, acting_academy_id: int |
  None = None) -> str` (claim `acting_academy_id` só quando presente).
- Produces: `MasterContextRead.support_mode: bool = False` e
  `MasterContextApiRead.support_mode: bool`.
- Produces: `AuthService.create_support_entry(admin_master_id: int,
  academy_id: int) -> SupportEntryRead{code: str, expires_at: datetime}`
  (one_time_token `purpose='support_entry'`, 60 s; grava `audit_log`
  `action=SUPPORT_ENTRY, entity_name='academy', entity_id=academy_id,
  master_id=admin`).
- Produces: `AuthService.exchange_support_code(code: str) -> AuthResult`
  (sessão com `acting_academy_id` e `expires_at = agora + 8 h`; código
  inválido → `UnauthorizedError(code='SUPPORT_CODE_INVALID')`).
- Produces (rotas): `POST /api/v1/admin/academies/{academy_id}/support-entry
  -> SupportEntryRead`; `POST /api/v1/auth/support/exchange {code} ->
  AuthTokenResponse` + cookie de refresh.
- Regra em `resolve_master_context`: token com `acting_academy_id` → exige
  `is_admin` pelo e-mail atual do dono do token (senão 401
  `SUPPORT_SESSION_INVALID`), carrega a academia vista e devolve o contexto com
  `academy_*` dela e `support_mode=True`; **não** aplica `ACADEMY_BLOCKED`.
- Rotas de conta recusam suporte com `ForbiddenError(code='SUPPORT_MODE')`:
  `POST /auth/set-credentials`, `/auth/telegram/link-token`,
  `/auth/telegram/setup-token`, e todo `/admin/*` (`is_admin` falso em suporte).

- [ ] **Step 1: Write the failing tests**

```python
async def test_support_flow_sees_target_academy(client, admin_headers, db_session):
    # outra academia com 1 aluno → POST support-entry → exchange(code)
    # GET /auth/me com o token: academy.name == 'Outra Academia', support_mode True
    # GET /api/v1/students → só o aluno da outra academia

async def test_support_code_single_use_and_expiry(client, admin_headers, db_session):
    # 2º exchange com o mesmo código → 401 SUPPORT_CODE_INVALID
    # código com expires_at no passado → 401 SUPPORT_CODE_INVALID

async def test_setup_token_is_not_a_support_code(client, db_session):
    # one_time_token purpose='telegram_setup' → exchange → SUPPORT_CODE_INVALID

async def test_support_refresh_keeps_academy_and_deadline(client, admin_headers, db_session):
    # exchange → refresh → /auth/me ainda na outra academia
    # refresh_session nova tem acting_academy_id igual e expires_at == original

async def test_support_session_ends_after_8_hours(client, admin_headers, db_session):
    # forçar expires_at = agora - 1 s na sessão → refresh 401

async def test_support_refused_when_admin_email_changes(client, admin_headers, db_session, monkeypatch):
    # exchange → monkeypatch ADMIN_EMAIL='outro@x' → /auth/me 401 SUPPORT_SESSION_INVALID

async def test_support_works_on_blocked_academy(client, admin_headers, db_session):
    # outra academia blocked → entry + exchange → /auth/me 200

@pytest.mark.parametrize('url', ['/api/v1/auth/set-credentials',
    '/api/v1/auth/telegram/link-token', '/api/v1/auth/telegram/setup-token',
    '/api/v1/admin/academies'])
async def test_account_and_admin_routes_refused_in_support(client, url, ...):
    assert response.status_code == 403  # SUPPORT_MODE (admin: ADMIN_ONLY)

async def test_support_entry_writes_audit_log(client, admin_headers, db_session):
    # 1 linha audit_log action='support_entry', entity_id=id da academia
```

- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Migração (conferir o arquivo gerado; `alembic upgrade head`
  e `alembic check` limpos no banco local).
- [ ] **Step 4:** Implementar token, sessão (rotação copia
  `acting_academy_id` e mantém `expires_at` quando ele existe), entrada, troca
  e a regra em `resolve_master_context`.
- [ ] **Step 5:** Rodar → PASS; `poetry run pytest tests/api/test_auth*.py
  tests/api/test_set_credentials.py tests/api/test_academy_blocked.py -q` →
  PASS.
- [ ] **Step 6: Commit** `feat: support mode sessions scoped to one academy`

---

### Task 5: Site — painel em `admin.*`

**Files:**
- Create: `frontend/src/lib/host.ts` (`export const isAdminHost =
  window.location.hostname.startsWith('admin.')`)
- Modify: `frontend/src/main.tsx` (escolhe `adminRouter` ou `router`)
- Modify: `frontend/vite.config.ts` (`allowedHosts` + `'admin.localhost'`)
- Modify: `frontend/src/features/auth/pages/LoginPage.tsx` (prop
  `redirectTo = '/app'`)
- Create: `frontend/src/features/admin/api.ts`, `router.tsx`,
  `AdminLayout.tsx`, `RequireAdmin.tsx`,
  `pages/AdminAcademiesPage.tsx`, `components/AcademyFormDialog.tsx`,
  `components/CredentialsDialog.tsx`
- Modify: `frontend/src/lib/api/schema.d.ts` (`npm run gen:api` com a API
  local rodando), `frontend/src/lib/api/errors.ts`

**Interfaces:**
- Consumes: rotas das Tarefas 2–4 via tipos gerados (`Schemas['AdminAcademyRead']`
  etc.); `useAuth`, `LoginPage`, componentes de `@/components/ui`.
- Produces: `adminRouter` com `/login` (LoginPage `redirectTo="/"`) e `/`
  (`RequireAdmin` → `AdminLayout` → `AdminAcademiesPage`); `RequireAdmin`
  chama `GET /admin/me`: 403 → tela "Sem acesso" com botão Sair.
- Produces: `buildWhatsAppAccessMessage(email: string, password: string):
  string` em `features/admin/api.ts` →
  `"Seu acesso ao Katsuflow:\nhttps://katsuflow.com.br\nE-mail: ${email}\nSenha: ${password}"`.
- Mensagens novas em `ERROR_MESSAGES`: `ACADEMY_BLOCKED`: "Academia
  desativada. Fale com o suporte."; `ADMIN_ONLY`: "Sem acesso.";
  `ADMIN_EMAIL_LOCKED`: "Você não pode trocar o seu próprio e-mail por aqui.";
  `CANNOT_BLOCK_OWN_ACADEMY`: "Você não pode desativar a sua própria
  academia."; `ACADEMY_NOT_FOUND`: "Academia não encontrada.";
  `SUPPORT_CODE_INVALID`: "Link de suporte inválido ou expirado. Clique em
  Entrar de novo no painel."; `SUPPORT_MODE`: "Indisponível no modo suporte.";
  `SUPPORT_SESSION_INVALID`: "Sessão de suporte encerrada.".

- [ ] **Step 1:** Página da lista: busca (debounce, `useDebouncedValue`),
  tabela no computador / cartões no celular com academia, mestre, e-mail,
  telefone, situação (chip), criada em; ações por linha: Editar, Trocar senha
  (confirmação), Ativar/Desativar (confirmação; desabilitado se `is_own`),
  Entrar (Tarefa 6 liga).
- [ ] **Step 2:** `AcademyFormDialog` (criar/editar; e-mail com erro no campo
  para `EMAIL_ALREADY_REGISTERED`/`ADMIN_EMAIL_LOCKED`) e `CredentialsDialog`
  (mensagem pronta + botão Copiar, depois de criar e de trocar senha).
- [ ] **Step 3:** `npx tsc -b` e `npm run lint` limpos.
- [ ] **Step 4:** Conferir no navegador em `http://admin.localhost:5173`
  (com `ADMIN_EMAIL` no `.env` local): login, criar, copiar mensagem, editar,
  trocar senha, desativar/ativar; login de não-admin → "Sem acesso";
  `http://localhost:5173` continua o site normal.
- [ ] **Step 5: Commit** `feat: admin panel on the admin subdomain`

---

### Task 6: Site — modo suporte e mensagem de bloqueio

**Files:**
- Create: `frontend/src/features/auth/pages/SupportEntryPage.tsx` (rota
  `/suporte` no `router` principal, fora do `RequireAuth`)
- Create: `frontend/src/app/components/SupportBanner.tsx`; usar em
  `AppLayout.tsx` acima do conteúdo
- Modify: `frontend/src/features/auth/api.ts` (`exchangeSupportCode(code:
  string): Promise<AuthTokens>`), `frontend/src/features/admin/api.ts`
  (`createSupportEntry(academyId: string): Promise<{code: string}>`)
- Modify: `frontend/src/features/settings/pages/SettingsPage.tsx` (esconde a
  seção "Conta" quando `master.support_mode`)
- Modify: `frontend/src/features/admin/pages/AdminAcademiesPage.tsx` (botão
  Entrar)

**Interfaces:**
- Consumes: `POST /admin/academies/{id}/support-entry`,
  `POST /auth/support/exchange`, `master.support_mode` (Tarefa 4);
  `startSession`, `signOut` (`useAuth`).
- Entrar: `const w = window.open('', '_blank')` **antes** do `await` (para não
  ser barrado como pop-up), depois
  `w.location = \`${location.protocol}//${mainHost}/suporte#${code}\``
  onde `mainHost` = `location.host` sem o prefixo `admin.` (dev:
  `admin.localhost:5173` → `localhost:5173`; produção →
  `katsuflow.com.br`). Se o `await` falhar, fechar a aba vazia (`w.close()`)
  e mostrar o erro.
- `SupportEntryPage`: lê o código de `location.hash`, apaga o hash da URL
  (`history.replaceState`), troca, `startSession`, `navigate('/app')`; erro →
  mensagem de `SUPPORT_CODE_INVALID`.
- Faixa: "Modo suporte: {master.academy.name} · Sair"; Sair →
  `signOut()` e `window.close()` (se o navegador não fechar, vai para
  `/login`).

- [ ] **Step 1:** Implementar API, página, faixa, esconder "Conta", botão
  Entrar.
- [ ] **Step 2:** `npx tsc -b` e `npm run lint` limpos.
- [ ] **Step 3:** Conferir no navegador: Entrar abre aba nova em
  `localhost:5173/app` com a faixa e os dados da outra academia; recarregar
  (F5) mantém o suporte; Configurações sem "Conta"; Sair fecha; reabrir o
  mesmo link → erro de link inválido; mestre de academia desativada no login →
  "Academia desativada. Fale com o suporte.".
- [ ] **Step 4: Commit** `feat: support mode banner and entry page`

---

### Task 7: Deploy e fechamento

**Files:**
- Modify: `deploy/Caddyfile`
- Modify: `docs/superpowers/specs/2026-10-21-admin-panel-design.md`
  (seção "Status da implementação")
- Obsidian: `2 · Especificações/Painel do dono (ideia).md`, `DojoFlow.md`

**Interfaces:**
- Caddy: em **ambos** os endereços, `respond /api/v1/auth/register 404`; no
  principal também `respond /api/v1/admin/* 404`; novo bloco
  `admin.{$DOMAIN}` igual ao principal (mesmo `/srv`, `try_files`, cabeçalhos,
  `reverse_proxy api:8000`), sem o bloqueio de `/api/v1/admin/*`.

- [ ] **Step 1:** Editar o Caddyfile (bloquear dentro do `handle /api/*`,
  antes do `reverse_proxy`).
- [ ] **Step 2:** Teste local com o compose de produção (como no teste da
  `feat/deploy`: `DOMAIN=localhost`, portas 8080/8443) e `curl -k`:
  `https://localhost:8443/api/v1/admin/me` → 404;
  `--resolve admin.localhost:8443:127.0.0.1 https://admin.localhost:8443/api/v1/admin/me`
  → 401 (sem token); `POST …/api/v1/auth/register` → 404 nos dois;
  `https://admin.localhost:8443/` → 200 HTML. Derrubar com `down -v`.
- [ ] **Step 3:** Suíte inteira: `poetry run task test`, `poetry run ruff
  check .`, `poetry run ruff format --check .`, `poetry run typos .`,
  `cd frontend && npm run build && npm run lint` → tudo limpo.
- [ ] **Step 4:** Status no spec e no Obsidian (o que foi feito, comandos de
  produção: `ADMIN_EMAIL` no `.env` do servidor, `create_academy` para a
  academia do Thiago).
- [ ] **Step 5: Commit** `chore: admin subdomain in Caddy, register closed`
