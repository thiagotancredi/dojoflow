# Baixa automática pela InfinitePay — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O mestre liga a InfinitePay (tag + chave de API); o link `/pagar` leva ao checkout dela com o total vencido; o aviso de pagamento (ou a volta do aluno) é conferido no `payment_check` e vira baixa automática.

**Architecture:** Cliente HTTP isolado em `integrations/infinitepay/` (padrão do CEP). Regras num serviço novo `services/infinitepay.py` (`InfinitePayService`), que reaproveita `BillingService` para calcular o total vencido e para lançar a baixa (`create_payment`). Uma tabela nova guarda cada link de checkout; a baixa ganha a coluna `source`. Frontend: convite + janela de 3 etapas em Cobrança, botão "Pagar mensalidade" na página pública, selo/recibo/aviso "a conferir" na ficha.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic, httpx, `cryptography` (Fernet — dependência nova), pytest; React + TypeScript + openapi-fetch.

**Spec:** `docs/superpowers/specs/2026-10-24-infinitepay-auto-settlement-design.md`

## Global Constraints

- InfinitePay: criar link `POST https://api.checkout.infinitepay.io/links` com header `X-Api-Key`; conferir `POST https://api.checkout.infinitepay.io/payment_check` com `handle`, `order_nsu`, `transaction_nsu`, `slug`. Preço em **centavos**.
- Erros conhecidos da InfinitePay: HTTP 403 `{"message":"Forbidden"}` = chave recusada; HTTP 404 `{"error":"external_checkout_not_enabled",...}` = checkout não liberado (também para tag inexistente).
- **Nada de baixa sem `paid: true` do `payment_check`.** `transaction_nsu` único (uma baixa por pagamento).
- A baixa só entra se o valor do link == total vencido atual do aluno; senão o link vira **"a conferir"** (nada é lançado, nem como adiantamento).
- Baixa manual continua igual e, ao ser lançada, cancela (do lado do Katsuflow) os links abertos do aluno.
- Chave de API: guardada criptografada (Fernet, segredo em `INFINITEPAY_SECRET_KEY`); nunca devolvida pela API nem logada; a tela mostra no máximo os 4 últimos caracteres.
- Endereço do aviso: `{WEB_APP_URL}{API_V1_PREFIX}/public/webhooks/infinitepay` (em produção a API fica no mesmo domínio do site).
- Textos fixados pelo spec (usar como estão):
  - convite: "Receba com baixa automática" + selo "GRÁTIS" + "O aluno paga pela InfinitePay e a mensalidade fica paga sozinha, na hora. Pix sem taxa."
  - chave recusada: "A chave de API não foi aceita. Crie uma chave nova no app da InfinitePay (Checkout → Configurações → API Keys) e cole aqui."
  - checkout não liberado: "A InfinitePay ainda não liberou o checkout para essa tag. Confira se a tag está certa e, no app da InfinitePay, desligue e ligue de novo 'Habilitar Checkout Integrado'."
  - rede: "Não foi possível falar com a InfinitePay agora. Tente de novo."
  - página do aluno: botão "Pagar mensalidade" / "Pagar mensalidades"; texto "Você vai para a página segura da InfinitePay. Lá você escolhe Pix ou cartão e confirma com um código que chega no seu WhatsApp."; volta: "Confirmando seu pagamento…"
  - a conferir: "Pagamento de R$ X recebido pela InfinitePay em DD/MM, mas o valor em aberto mudou. Confira e, se for o caso, lance à mão ou devolva."
- Fora desta versão: validade curta (`valid_until`), trava de taxa, e-mail, exames de graduação.
- Testes nunca chamam a InfinitePay real (cliente simulado com `httpx.MockTransport` ou `monkeypatch`).
- Cada tarefa roda os próprios testes; a suíte completa só na Tarefa 10.

## Review Focus

1. **Aviso e volta do aluno ao mesmo tempo** (webhook + `/confirm` concorrentes) → uma baixa só. Teste na Tarefa 5 (`test_settle_twice_same_transaction_creates_one_payment`) + `SELECT … FOR UPDATE` no link.
2. **`order_nsu` de outra academia/aluno no `/confirm`** → o token do aluno precisa ser dono do link; senão ignora. Teste na Tarefa 5 (`test_confirm_with_other_students_order_is_ignored`).
3. **Chave vazando** em GET de configurações, em resposta de erro ou em log → nunca. Teste na Tarefa 3 (`test_settings_never_return_api_key`).
4. **Aluno sem telefone/e-mail** (ou menor sem responsável) → link criado mesmo assim, `customer` só com o que existir. Teste na Tarefa 4 (`test_checkout_without_phone_sends_name_only`).
5. **Tag digitada com `$`, espaços ou maiúsculas** → normalizada (`katsuflow`). Teste na Tarefa 3 (`test_connect_normalizes_handle`).

---

### Task 1: Dados, migração e criptografia da chave

**Files:**
- Create: `src/dojoflow/core/crypto.py`, `src/dojoflow/models/infinitepay_checkout.py`, `migrations/versions/<rev>_infinitepay.py`, `tests/services/test_crypto.py`
- Modify: `src/dojoflow/core/settings.py`, `src/dojoflow/models/academy_billing_settings.py`, `src/dojoflow/models/payment_transaction.py`, `src/dojoflow/models/__init__.py` (registrar o modelo, se for o padrão), `src/dojoflow/shared/enums.py`, `pyproject.toml`/`poetry.lock` (`poetry add cryptography`), `.env.example` (se existir)

**Interfaces:**
- Produces:
  - `settings.INFINITEPAY_SECRET_KEY: str` (padrão de dev fixo; mesmo validador do JWT: fora de `dev`, recusar o padrão)
  - `encrypt_secret(plain: str) -> str`, `decrypt_secret(token: str) -> str` em `core/crypto.py`
  - enum `PaymentSource(str, Enum)`: `MANUAL='manual'`, `INFINITEPAY='infinitepay'`
  - enum `CheckoutStatus(str, Enum)`: `OPEN='open'`, `PAID='paid'`, `CANCELED='canceled'`, `REVIEW='review'`, `RESOLVED='resolved'`
  - `AcademyBillingSettings`: `infinitepay_handle: str|None (60)`, `infinitepay_api_key: str|None (500, cifrada)`, `infinitepay_enabled: bool = False`, `infinitepay_tested_at: datetime|None`
  - `PaymentTransaction.source: PaymentSource` (default `MANUAL`, não nulo)
  - modelo `InfinitePayCheckout` (tabela `infinitepay_checkout`): `academy_id`, `student_id`, `handle (60)`, `order_nsu (64, único)`, `amount (money)`, `url (1000)`, `status (CheckoutStatus, default OPEN)`, `transaction_nsu (64, único, nulo)`, `invoice_slug (64, nulo)`, `receipt_url (500, nulo)`, `capture_method (20, nulo)`, `paid_amount (money, nulo)`, `installments (int, nulo)`, `paid_at (datetime, nulo)`, `payment_transaction_id (fk, nulo)`

- [ ] **Step 1:** Teste `test_encrypt_roundtrip` (`decrypt_secret(encrypt_secret('inchk_abc')) == 'inchk_abc'` e o cifrado não contém `'inchk_abc'`) e `test_settings_refuse_default_infinitepay_secret_outside_dev` (como o teste do JWT).
- [ ] **Step 2:** `poetry run pytest tests/services/test_crypto.py -v` → FAIL (módulo não existe).
- [ ] **Step 3:** `poetry add cryptography`; criar `core/crypto.py` com Fernet; enums; colunas; modelo; migração (`alembic revision --autogenerate -m infinitepay`, revisar à mão: `source` com `server_default='manual'`).
- [ ] **Step 4:** `poetry run pytest tests/services/test_crypto.py -v` → PASS; `poetry run alembic upgrade head` no banco local → OK; `poetry run alembic downgrade -1 && poetry run alembic upgrade head` → OK.
- [ ] **Step 5:** Commit `feat: InfinitePay data model and API key encryption`.

### Task 2: Cliente HTTP da InfinitePay

**Files:**
- Create: `src/dojoflow/integrations/infinitepay/__init__.py`, `client.py`, `schemas.py`; `tests/services/test_infinitepay_client.py`

**Interfaces:**
- Produces (em `integrations/infinitepay/client.py`):
  - `class InfinitePayClient(transport: httpx.AsyncBaseTransport | None = None)` — timeout de 5 s
  - `async create_link(api_key: str, *, order_nsu: str, items: list[CheckoutItem], customer: CheckoutCustomer | None, redirect_url: str | None, webhook_url: str | None) -> str` (devolve `url`)
  - `async payment_check(*, handle: str, order_nsu: str, transaction_nsu: str, slug: str) -> PaymentCheck`
  - schemas: `CheckoutItem(description: str, quantity: int, price: int)` (centavos), `CheckoutCustomer(name: str, phone_number: str|None, email: str|None)`, `PaymentCheck(success: bool, paid: bool, amount: int|None, paid_amount: int|None, capture_method: str|None, installments: int|None)`
  - exceções: `InfinitePayKeyRejected`, `InfinitePayCheckoutDisabled`, `InfinitePayUnavailable` (rede, timeout, 5xx, resposta inesperada)

- [ ] **Step 1:** Testes com `httpx.MockTransport`:
  - `test_create_link_sends_key_and_cents` — request tem header `X-Api-Key: k`, JSON com `order_nsu`, `items[0].price == 15000`, `webhook_url`, `redirect_url`; `customer` omitido quando `None`; resposta `{"url": "https://checkout.infinitepay.io/x"}` → devolve a URL.
  - `test_create_link_forbidden_raises_key_rejected` (403) · `test_create_link_not_enabled_raises_checkout_disabled` (404 com `error: external_checkout_not_enabled`) · `test_create_link_timeout_raises_unavailable`.
  - `test_payment_check_paid` (`{"success":true,"paid":true,"amount":200,"paid_amount":200,"installments":1,"capture_method":"pix"}`) · `test_payment_check_unknown_returns_not_paid` (`{"success":false}` → `paid=False`).
- [ ] **Step 2:** `poetry run pytest tests/services/test_infinitepay_client.py -v` → FAIL.
- [ ] **Step 3:** Implementar o cliente (httpx.AsyncClient por chamada, como o CEP). Nunca incluir a chave em mensagens de exceção.
- [ ] **Step 4:** Mesmos testes → PASS.
- [ ] **Step 5:** Commit `feat: InfinitePay HTTP client`.

### Task 3: Ligar, ver e desligar (Configurações)

**Files:**
- Create: `src/dojoflow/services/infinitepay.py`, `src/dojoflow/schemas/infinitepay_api.py`, `src/dojoflow/api/dependencies/infinitepay.py`, `src/dojoflow/api/routes/infinitepay.py`, `tests/api/test_infinitepay_settings.py`
- Modify: `src/dojoflow/main.py` (registrar o router)

**Interfaces:**
- Consumes: Task 1 (colunas, crypto), Task 2 (`InfinitePayClient`, exceções).
- Produces:
  - `InfinitePayService(db_session, client: InfinitePayClient)`; dependência `InfinitePayServiceDep` (cliente injetável para testes via `app.dependency_overrides` ou monkeypatch de `InfinitePayClient`)
  - `async status(academy_id) -> InfinitePayStatusApi` com `enabled: bool`, `handle: str|None`, `tested_at: datetime|None`, `key_last4: str|None`
  - `async connect(academy_id, handle: str, api_key: str) -> InfinitePayStatusApi` — normaliza a tag (tira `$` e espaços, minúsculas), cria link de teste (`order_nsu='kftest-'+uuid`, item "Teste de conexão Katsuflow", 100 centavos, sem webhook) e, se der certo, salva tag + chave cifrada + `enabled=True` + `tested_at=now`
  - `async disconnect(academy_id) -> InfinitePayStatusApi` — `enabled=False` (mantém tag/chave para religar)
  - Rotas (mestre logado): `GET /academy/infinitepay` → status; `PUT /academy/infinitepay` body `{handle, api_key}` → status; `DELETE /academy/infinitepay` → status
  - Erros da API (`ConflictError`/código): `INFINITEPAY_KEY_REJECTED`, `INFINITEPAY_CHECKOUT_DISABLED`, `INFINITEPAY_UNAVAILABLE` com os textos das Global Constraints

- [ ] **Step 1:** Testes:
  - `test_connect_success_enables` (status `enabled`, `handle == 'katsuflow'`, `key_last4` == 4 últimos, `tested_at` preenchido; o cliente falso recebeu a chave)
  - `test_connect_normalizes_handle` (`' $KatsuFlow '` → `katsuflow`)
  - `test_connect_key_rejected_does_not_enable` · `test_connect_checkout_disabled_message` · `test_connect_unavailable_message` (código + texto exato; continua `enabled=False`)
  - `test_settings_never_return_api_key` (GET/PUT não têm a chave inteira em nenhum campo; a coluna no banco ≠ chave em texto)
  - `test_disconnect_keeps_handle` · `test_infinitepay_settings_isolated_by_academy` (outra academia vê `enabled=False`)
- [ ] **Step 2:** `poetry run pytest tests/api/test_infinitepay_settings.py -v` → FAIL.
- [ ] **Step 3:** Implementar serviço, schemas, dependência, rotas.
- [ ] **Step 4:** Mesmos testes → PASS.
- [ ] **Step 5:** Commit `feat: connect InfinitePay in billing settings`.

### Task 4: Página pública cria o link de checkout

**Files:**
- Modify: `src/dojoflow/services/billing.py` (`public_payment`), `src/dojoflow/schemas/public_pay.py`, `src/dojoflow/api/routes/public_pay.py`, `src/dojoflow/services/infinitepay.py`
- Test: `tests/api/test_infinitepay_checkout.py`; ajustar `tests/api/test_public_pay.py` (conjunto de campos)

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `PublicPaymentRead.checkout_enabled: bool` (quando `True`, `pix_code` vem `None`)
  - `BillingService.overdue_for_student(academy_id, student_id, today) -> list[ChargeRead]` (extrair de `public_payment` a lista vencida ordenada que ela já monta; `public_payment` passa a usá-la)
  - `InfinitePayService.checkout_for_token(token: str, today: date | None = None) -> str` (URL) — erros: token inválido/academia bloqueada → `NotFoundError(code='PAY_LINK_INVALID')`; nada vencido → `ConflictError(code='NOTHING_TO_PAY')`; integração desligada → `ConflictError(code='INFINITEPAY_DISABLED')`; falha da InfinitePay → `INFINITEPAY_UNAVAILABLE`
  - Reaproveita link `OPEN` do mesmo aluno com o mesmo `amount` criado há menos de **24 h**; senão cria: `order_nsu = secrets.token_urlsafe(24)`, itens = rótulos/valores da página pública, `customer` = destinatário de `choose_recipient` (nome; telefone `+55…`; e-mail se houver), `redirect_url = {WEB_APP_URL}/pagar/{token}`, `webhook_url` = Global Constraints
  - Rota `POST /public/pay/{token}/checkout` → `{ "url": str }` (com `public_pay_limiter`)

- [ ] **Step 1:** Testes (usar o cenário `_overdue_student` de `test_public_pay.py`, extraído para `tests/helpers/` se precisar):
  - `test_public_pay_checkout_enabled_hides_pix_code` (`checkout_enabled is True`, `pix_code is None`) e, desligado, `checkout_enabled is False` com o código de sempre
  - `test_checkout_creates_link_with_overdue_total` (cliente falso recebe 2 itens de 10000 centavos; resposta tem a URL; linha `OPEN`, `amount == 200`, `handle` da academia)
  - `test_checkout_reuses_open_link_same_amount` (segunda chamada não chama o cliente de novo)
  - `test_checkout_new_link_when_amount_changed`
  - `test_checkout_minor_uses_responsible_as_customer` · `test_checkout_without_phone_sends_name_only`
  - `test_checkout_disabled_409` · `test_checkout_nothing_overdue_409` · `test_checkout_unknown_token_404`
- [ ] **Step 2:** `poetry run pytest tests/api/test_infinitepay_checkout.py tests/api/test_public_pay.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Mesmos testes → PASS.
- [ ] **Step 5:** Commit `feat: create InfinitePay checkout from public pay page`.

### Task 5: Aviso, volta do aluno e baixa automática

**Files:**
- Modify: `src/dojoflow/services/infinitepay.py`, `src/dojoflow/services/billing.py` (`create_payment`), `src/dojoflow/api/routes/public_pay.py`, `src/dojoflow/schemas/infinitepay_api.py`
- Test: `tests/api/test_infinitepay_settlement.py`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  - `BillingService.create_payment(..., source: PaymentSource = PaymentSource.MANUAL)`; quando `MANUAL`, marca `CANCELED` os checkouts `OPEN` do aluno
  - `InfinitePayService.settle(order_nsu: str, transaction_nsu: str, slug: str, *, receipt_url: str | None = None, student_id: int | None = None) -> CheckoutStatus | None` — passos 1–5 do spec, seção 3:
    1. busca o checkout por `order_nsu` com `with_for_update()`; não achou (ou `student_id` dado e diferente) → `None`
    2. já `PAID`/`REVIEW`/`RESOLVED` com o mesmo `transaction_nsu` → devolve o status sem fazer nada
    3. `payment_check(handle=checkout.handle, …)`; `paid` falso → `None`; `InfinitePayUnavailable` sobe
    4. `paid_amount*100 >= amount*100` e `amount == soma do vencido atual` → `create_payment(amount, hoje, método, notes='InfinitePay', source=INFINITEPAY)`, status `PAID`, guarda `transaction_nsu`, `invoice_slug`, `receipt_url`, `capture_method`, `paid_amount`, `installments`, `paid_at`, `payment_transaction_id`
    5. senão → status `REVIEW` (mesmos dados guardados, sem baixa)
    - método: `capture_method == 'pix'` → `PaymentMethod.PIX`; `'credit_card'` → `CREDIT_CARD`; outro → `OTHER`
  - Rota `POST /public/webhooks/infinitepay` — body com `order_nsu`, `transaction_nsu`, `invoice_slug`, `receipt_url` (demais campos ignorados) → 200 sempre que processado/ignorado; `InfinitePayUnavailable` → 400 (a InfinitePay reenvia)
  - Rota `POST /public/pay/{token}/confirm` — body `{order_nsu, transaction_nsu, slug, receipt_url?}` (o que a InfinitePay põe no endereço de volta) → chama `settle(..., student_id=dono do token)` → `{ "status": "paid" | "review" | "pending" }` (`pending` quando `None`); com `public_pay_limiter`

- [ ] **Step 1:** Testes (cliente falso para `payment_check`):
  - `test_webhook_paid_creates_automatic_payment` (cobranças jan+fev quitadas; transação `source == 'infinitepay'`, `method == 'pix'`; checkout `PAID` com `receipt_url`)
  - `test_webhook_card_payment_method_credit_card`
  - `test_settle_twice_same_transaction_creates_one_payment` (webhook e confirm seguidos → 1 transação)
  - `test_webhook_not_paid_does_nothing` · `test_webhook_unknown_order_ignored_200`
  - `test_webhook_unavailable_returns_400`
  - `test_manual_payment_cancels_open_checkout`
  - `test_paid_after_manual_payment_goes_to_review` (link de 200; mestre lança 100 à mão; aviso chega → `REVIEW`, nenhuma transação nova, nenhum adiantamento)
  - `test_paid_after_disconnect_still_settles` (checkout guarda a tag; integração desligada → ainda `PAID`)
  - `test_confirm_with_other_students_order_is_ignored` → `pending`, nada lançado
  - `test_confirm_returns_paid`
- [ ] **Step 2:** `poetry run pytest tests/api/test_infinitepay_settlement.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Mesmos testes + `tests/api/test_billing_api.py tests/api/test_bulk_payments.py` → PASS.
- [ ] **Step 5:** Commit `feat: settle InfinitePay payments automatically`.

### Task 6: O que o mestre vê (backend)

**Files:**
- Modify: `src/dojoflow/schemas/billing.py`, `src/dojoflow/schemas/billing_api.py`, `src/dojoflow/services/billing.py` (`_payments`, `student_billing`), `src/dojoflow/services/infinitepay.py`, `src/dojoflow/api/routes/billing.py`
- Test: `tests/api/test_infinitepay_reviews.py`

**Interfaces:**
- Consumes: Task 5.
- Produces:
  - `PaymentRead`/`PaymentApiRead`: `source: PaymentSource`, `receipt_url: str | None` (do checkout ligado à transação)
  - `StudentBillingRead`/`StudentBillingApiRead`: `reviews: list[CheckoutReviewApiRead]` com `id: UUID` (public_id do checkout), `amount: Decimal`, `paid_at: date`, `receipt_url: str | None` — só checkouts `REVIEW` do aluno
  - `InfinitePayService.resolve_review(academy_id, student_id, review_public_id) -> None` → `RESOLVED`
  - Rota `POST /students/{student_id}/billing/reviews/{review_id}/resolve` → 204

- [ ] **Step 1:** Testes: `test_student_billing_shows_automatic_source_and_receipt` · `test_student_billing_lists_reviews` · `test_resolve_review_hides_it` · `test_resolve_review_other_academy_404`.
- [ ] **Step 2:** `poetry run pytest tests/api/test_infinitepay_reviews.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Mesmos testes + `tests/api/test_openapi_contract.py` → PASS.
- [ ] **Step 5:** Commit `feat: show automatic payments and reviews to the master`.

### Task 7: Frontend — Configurações → Cobrança

**Files:**
- Create: `frontend/src/features/settings/components/InfinitePayInvite.tsx`, `InfinitePaySetupDialog.tsx`, `frontend/src/features/settings/infinitepay-api.ts`
- Modify: `frontend/src/features/settings/components/BillingSettingsSection.tsx` (convite no topo do cartão Cobrança), `frontend/src/lib/api/schema.d.ts` (`npm run gen:api` com a API local rodando)

**Interfaces:**
- Consumes: rotas da Task 3.
- Produces: `<InfinitePayInvite />` (desligado: convite + "Ligar"; ligado: "✓ Baixa automática ligada · $tag · testada em DD/MM/AAAA" + "Trocar chave" + "Desligar" com confirmação) e `<InfinitePaySetupDialog />` com 3 etapas (Conta → Checkout → Sua tag e sua chave), textos da seção 1 do spec (incluindo nomes em inglês do app e a pegadinha "ligar pelo app do celular"); "Testar e ligar" mostra o texto de erro que a API devolver.

- [ ] **Step 1:** `npm run gen:api` (API local de pé) → tipos novos em `schema.d.ts`.
- [ ] **Step 2:** Implementar os componentes usando `Dialog` de `components/ui/dialog.tsx` (mesmo padrão das janelas existentes, que viram gaveta no celular) e os tokens do tema; campo de chave `type="password"`, sem preencher de volta.
- [ ] **Step 3:** `cd frontend && npx tsc -b && npm run lint` → sem erros.
- [ ] **Step 4:** Passeio no navegador (Vite + API local, cliente da InfinitePay apontando para a API real é aceitável aqui só com a conta do Thiago, ou simulado): convite → 3 etapas → erro de chave errada → sucesso → estado ligado → desligar. Em 390 px e no computador.
- [ ] **Step 5:** Commit `feat: InfinitePay setup in billing settings`.

### Task 8: Frontend — página do aluno

**Files:**
- Modify: `frontend/src/features/pay/PayPage.tsx`, `frontend/src/features/pay/api.ts`

**Interfaces:**
- Consumes: Task 4 (`checkout_enabled`, `POST …/checkout`), Task 5 (`POST …/confirm`).
- Produces: com `checkout_enabled`, botão "Pagar mensalidade(s)" + texto do spec no lugar de `CopyPixCode`; tocar → `POST checkout` → `window.location.assign(url)`; ao voltar com `order_nsu`, `transaction_nsu`, `slug` (e `receipt_url`) na query → `POST confirm`, mostrar "Confirmando seu pagamento…", recarregar os dados a cada 2 s por até 20 s; `paid` → recarrega (estado "Tudo em dia"); ao fim do tempo, volta à tela normal. Limpar a query do endereço depois de confirmar.

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** `cd frontend && npx tsc -b && npm run lint` → sem erros.
- [ ] **Step 3:** Passeio: ligado × desligado; volta simulada abrindo `/pagar/<token>?order_nsu=…&transaction_nsu=…&slug=…` com o `payment_check` simulado.
- [ ] **Step 4:** Commit `feat: pay page sends students to InfinitePay checkout`.

### Task 9: Frontend — ficha do aluno

**Files:**
- Modify: `frontend/src/features/billing/components/StudentBillingTab.tsx`, `ChargeStatement.tsx`, `frontend/src/features/billing/api.ts` (ou onde ficam as chamadas da ficha)

**Interfaces:**
- Consumes: Task 6 (`source`, `receipt_url`, `reviews`, rota resolve).
- Produces: pagamento com `source === 'infinitepay'` mostra o selo "Automática · InfinitePay" e o link "Ver recibo" (nova aba) onde hoje aparece a data do pagamento; cada item de `reviews` vira um aviso no topo da aba Mensalidades com o texto do spec, "Ver recibo" e "Marcar como resolvido".

- [ ] **Step 1:** Implementar.
- [ ] **Step 2:** `cd frontend && npx tsc -b && npm run lint` → sem erros.
- [ ] **Step 3:** Passeio com dados criados pelos testes manuais da Task 8 (um pago, um "a conferir").
- [ ] **Step 4:** Commit `feat: show automatic payments and reviews in the student sheet`.

### Task 10: Fechamento

**Files:**
- Modify: `docs/superpowers/specs/2026-10-24-infinitepay-auto-settlement-design.md` (Status), nota do Obsidian "Integração InfinitePay (ideia)"

- [ ] **Step 1:** `poetry run pytest -q` → tudo passa; `poetry run ruff check . && poetry run ruff format --check .` → OK; `cd frontend && npx tsc -b && npm run lint` → OK.
- [ ] **Step 2:** Revisão independente da branch inteira (código + segurança da chave e das rotas públicas).
- [ ] **Step 3:** Atualizar o status no spec e no Obsidian (o que foi feito, `INFINITEPAY_SECRET_KEY` a configurar no `.env` do servidor, migração a rodar no deploy).
- [ ] **Step 4:** Commit `docs: InfinitePay auto-settlement status`. **Não** enviar ao GitHub nem publicar sem o "sim" do Thiago. Depois do deploy: pagamento real de R$ 2,00 com a conta do Thiago conferindo a baixa automática na ficha.
