# Página de pagamento Pix — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A cobrança do WhatsApp passa a levar um link `/pagar/<código>` para uma página pública com o que está vencido e o botão "Copiar código Pix" (copia e cola com valor).

**Architecture:** Backend gera o BR Code (Pix estático) num módulo puro `services/pix.py`; cada aluno tem um `pay_token` aleatório; um endpoint público sem login (`GET /api/v1/public/pay/{token}`) devolve só o necessário para a página. O frontend ganha a rota pública `/pagar/:token` (fora do `RequireAuth`), campos novos em Configurações → Cobrança e o link de pagamento na ficha do aluno.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + pytest (backend); React 19 + Vite + Tailwind + openapi-fetch + react-hook-form (frontend, sem testes automatizados: valida com `npm run build`, `npm run lint` e navegador).

**Spec:** `docs/superpowers/specs/2026-10-22-pix-payment-page-design.md`

## Global Constraints

- Branch: `feat/pix-payment-page` a partir da `main`.
- Rodar só os testes da própria tarefa durante o trabalho; suíte completa (`poetry run task test`), `task lint` e `npm run build && npm run lint` só na última tarefa.
- Python: aspas simples, linha até 79 colunas (ruff). Textos de tela em português.
- Nunca usar `cat >` em arquivos do frontend com o Vite rodando (usar Edit/Write).
- Tema da página pública: **grafite claro** sempre (gradiente da faixa `#2a2d33` → `#155e75`, tokens de `frontend/src/styles/theme.css`).
- Na página pública existe **um único** botão de copiar: "Copiar código Pix". A chave Pix **não** aparece.
- Tipo da chave é **obrigatório** para salvar uma chave; o site **nunca adivinha** o tipo; a migração **não** preenche tipo das chaves existentes.
- Sem chave, sem tipo ou sem cidade → sem código; página mostra "Fale com a academia para pagar".
- Academia bloqueada (`AcademyStatus.BLOCKED`) ou token inexistente → a mesma resposta 404 `PAY_LINK_INVALID`.
- "Em aberto" na página = cobranças com status `overdue`, valor `open_amount` (igual à mensagem).
- O endpoint público nunca devolve telefone, e-mail, CPF, chave Pix crua nem dados de outros alunos.

## Review Focus

1. Chave CPF/telefone digitada com pontuação ("529.982.247-25", "(11) 91234-5678") → salva normalizada; o código sai com `52998224725` / `+5511912345678` (Task 1 e Task 2).
2. Nome de recebedor com acento e pontuação ou com mais de 25 letras ("Associação Desportiva São João Batista") → código com `ASSOCIACAO DESPORTIVA SAO` (25 caracteres), sem acentos, CRC válido (Task 1).
3. Aluno menor: mensagem vai para o responsável → a página cumprimenta o responsável e as linhas dizem "Mensalidade de Ana · janeiro" (Task 4).
4. Aluno que pagou tudo depois de receber a mensagem abre o link → "Tudo em dia", sem código (Task 4).
5. Mestre gera link novo → o link antigo passa a dar 404 na hora (Task 5).

---

### Task 1: Gerador do código Pix e normalização da chave

**Files:**
- Create: `src/dojoflow/services/pix.py`
- Modify: `src/dojoflow/shared/enums.py` (enum novo)
- Test: `tests/services/test_pix.py`

**Interfaces:**
- Produces:
  - `class PixKeyType(str, enum.Enum)`: `CPF='cpf'`, `CNPJ='cnpj'`, `PHONE='phone'`, `EMAIL='email'`, `RANDOM='random'` (em `shared/enums.py`).
  - `normalize_pix_key(key: str, key_type: PixKeyType) -> str` — devolve a chave no formato do BR Code; `ValueError` com mensagem em português se não combinar com o tipo.
  - `pix_copy_paste(key: str, recipient_name: str, city: str, amount: Decimal) -> str` — `key` já normalizada.
  - `crc16(payload: str) -> str` — CRC16/CCITT-FALSE (poly `0x1021`, init `0xFFFF`), 4 hex maiúsculos.

- [ ] **Step 1: Write the failing tests**

```python
def test_crc16_matches_central_bank_example():
    payload = (
        '00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-'
        '4266554400005204000053039865802BR5913Fulano de Tal6008BRASILIA'
        '62070503***6304'
    )
    assert crc16(payload) == '1D3D'

def test_pix_copy_paste_with_amount():
    code = pix_copy_paste(
        '+5511912345678', 'Thiago T. Trajano', 'São Paulo', Decimal('300')
    )
    assert code == (
        '00020126360014br.gov.bcb.pix0114+5511912345678520400005303986'
        '5406300.005802BR5916THIAGO T TRAJANO6009SAO PAULO62070503***'
        '63047BFD'
    )

def test_pix_copy_paste_truncates_name_and_city():
    code = pix_copy_paste(
        'dojo@exemplo.com', 'Associação Desportiva São João Batista',
        'São José dos Campos', Decimal('150.5'),
    )
    assert '5925ASSOCIACAO DESPORTIVA SAO' in code
    assert '6015SAO JOSE DOS CA' in code
    assert '5406150.50' in code
    assert code[-4:] == crc16(code[:-4])

@pytest.mark.parametrize(('raw', 'key_type', 'expected'), [
    ('529.982.247-25', PixKeyType.CPF, '52998224725'),
    ('11.222.333/0001-81', PixKeyType.CNPJ, '11222333000181'),
    ('(11) 91234-5678', PixKeyType.PHONE, '+5511912345678'),
    ('+55 11 91234-5678', PixKeyType.PHONE, '+5511912345678'),
    ('5511912345678', PixKeyType.PHONE, '+5511912345678'),
    (' Dojo@Exemplo.COM ', PixKeyType.EMAIL, 'dojo@exemplo.com'),
    ('123E4567-E12B-12D1-A456-426655440000', PixKeyType.RANDOM,
     '123e4567-e12b-12d1-a456-426655440000'),
])
def test_normalize_pix_key(raw, key_type, expected):
    assert normalize_pix_key(raw, key_type) == expected

@pytest.mark.parametrize(('raw', 'key_type'), [
    ('52998224726', PixKeyType.CPF),          # dígito errado
    ('11111111111', PixKeyType.CPF),          # todos iguais
    ('11222333000180', PixKeyType.CNPJ),
    ('1234', PixKeyType.PHONE),
    ('dojo.exemplo.com', PixKeyType.EMAIL),
    ('nao-e-uuid', PixKeyType.RANDOM),
    ('dojo@exemplo.com', PixKeyType.CPF),     # tipo trocado
])
def test_normalize_pix_key_rejects(raw, key_type):
    with pytest.raises(ValueError):
        normalize_pix_key(raw, key_type)
```

- [ ] **Step 2: Run to verify they fail**

Run: `poetry run pytest tests/services/test_pix.py -v`
Expected: FAIL (`ModuleNotFoundError: dojoflow.services.pix`)

- [ ] **Step 3: Implement `services/pix.py` and `PixKeyType`**

Campos EMV (`ID + tamanho com 2 dígitos + valor`), nesta ordem: `00`=`01`; `26`= (`00`=`br.gov.bcb.pix`, `01`=chave); `52`=`0000`; `53`=`986`; `54`=valor com 2 casas e ponto; `58`=`BR`; `59`=nome; `60`=cidade; `62`=(`05`=`***`); `63`=CRC calculado sobre tudo antes, incluindo o próprio `6304`. Nome e cidade: tirar acentos (`unicodedata.normalize('NFKD')` + descartar combinantes), manter só `A-Z 0-9` e espaço, maiúsculas, espaços repetidos viram um, cortar em 25 (nome) e 15 (cidade) e tirar espaço do fim. CPF/CNPJ: só dígitos, 11/14, dígitos verificadores pelo módulo 11, rejeitar todos iguais. Telefone: só dígitos; 10–11 dígitos → prefixar `55`; 12–13 dígitos começando com `55` → aceitar; senão erro; resultado `+` + dígitos. E-mail: `strip().lower()`, exatamente um `@` com texto dos dois lados e um `.` depois do `@`, até 77 caracteres. Aleatória: UUID (`uuid.UUID(value)`), devolver em minúsculas com hífens.

- [ ] **Step 4: Run to verify they pass**

Run: `poetry run pytest tests/services/test_pix.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow/services/pix.py src/dojoflow/shared/enums.py tests/services/test_pix.py
git commit -m "feat: Pix copy-and-paste code and key normalization"
```

---

### Task 2: Migração + Configurações de cobrança com tipo da chave e cidade

**Files:**
- Create: `migrations/versions/<rev>_pix_payment_page.py` (down_revision `f72609848a9f`)
- Modify: `src/dojoflow/models/academy_billing_settings.py`, `src/dojoflow/models/student.py`, `src/dojoflow/schemas/billing_settings_api.py`, `src/dojoflow/services/billing.py` (`get_settings`, `save_settings`)
- Test: `tests/api/test_billing_settings_api.py`

**Interfaces:**
- Consumes: `PixKeyType`, `normalize_pix_key` (Task 1).
- Produces:
  - `AcademyBillingSettings.pix_key_type: Mapped[PixKeyType | None]` (`enum_column(PixKeyType, nullable=True)`), `AcademyBillingSettings.pix_city: Mapped[str | None]` (`str_column(60, nullable=True)`).
  - `Student.pay_token: Mapped[str]` — `String(32)`, `unique=True`, `index=True`, `nullable=False`, `default=new_pay_token`.
  - `new_pay_token() -> str` em `src/dojoflow/models/student.py` (`secrets.token_urlsafe(16)`).
  - `BillingSettingsApi` ganha `pix_key_type: PixKeyType | None = None` e `pix_city: str | None = Field(default=None, max_length=60)`.

- [ ] **Step 1: Write the failing tests** (em `test_billing_settings_api.py`; atualizar `SETTINGS` para incluir `'pix_key_type': 'email'` e `'pix_city': 'Goiânia'`, e o `test_settings_default_template` para os campos novos `None`)

```python
async def test_settings_requires_key_type(client):
    headers = await auth_headers(client)
    response = await client.put(URL, headers=headers, json={**SETTINGS, 'pix_key_type': None})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

async def test_settings_rejects_key_not_matching_type(client):
    headers = await auth_headers(client)
    response = await client.put(URL, headers=headers, json={**SETTINGS, 'pix_key_type': 'cpf'})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

async def test_settings_normalizes_key(client):
    headers = await auth_headers(client)
    saved = await client.put(URL, headers=headers, json={
        **SETTINGS, 'pix_key': '(11) 91234-5678', 'pix_key_type': 'phone'})
    assert saved.json()['pix_key'] == '+5511912345678'
    assert saved.json()['pix_key_type'] == 'phone'

async def test_settings_type_without_key_is_dropped(client):
    headers = await auth_headers(client)
    saved = await client.put(URL, headers=headers, json={
        **SETTINGS, 'pix_key': '', 'pix_key_type': 'cpf'})
    assert saved.json()['pix_key'] is None
    assert saved.json()['pix_key_type'] is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `poetry run pytest tests/api/test_billing_settings_api.py -v`
Expected: FAIL (campos novos ausentes / 200 em vez de 422)

- [ ] **Step 3: Model + schema + service**

Validação no `BillingSettingsApi` com `model_validator(mode='after')`: chave preenchida sem tipo → erro "Escolha o tipo da chave Pix."; chave preenchida → `normalize_pix_key` (o `ValueError` vira 422); chave vazia → tipo `None`. `get_settings`/`save_settings` passam os dois campos novos.

- [ ] **Step 4: Migração**

Uma migração só: `academy_billing_settings.pix_key_type` (`String(6)`, nullable) e `pix_city` (`String(60)`, nullable); `student.pay_token` criado nullable, preenchido com `secrets.token_urlsafe(16)` para cada aluno existente (loop em Python sobre `SELECT id FROM student`), depois `NOT NULL` + índice único `ix_student_pay_token`. **Não** preencher `pix_key_type`. `downgrade` remove os três.

Run: `poetry run alembic upgrade head && poetry run alembic downgrade -1 && poetry run alembic upgrade head`
Expected: sem erro (banco local `dojoflow_postgres` ligado).

- [ ] **Step 5: Run to verify they pass**

Run: `poetry run pytest tests/api/test_billing_settings_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add migrations/versions src/dojoflow/models src/dojoflow/schemas/billing_settings_api.py src/dojoflow/services/billing.py tests/api/test_billing_settings_api.py
git commit -m "feat: Pix key type, city and student pay token"
```

---

### Task 3: Link de pagamento na mensagem do WhatsApp

**Files:**
- Modify: `src/dojoflow/services/billing.py` (`DEFAULT_MESSAGE_TEMPLATE`, `StudentContact`, `_contacts`, `whatsapp_url`, `student_billing`), `src/dojoflow/schemas/billing.py` (`StudentBillingRead`), `src/dojoflow/schemas/billing_api.py` (`StudentBillingApiRead`)
- Test: `tests/api/test_billing_api.py`, `tests/api/test_billing_settings_api.py` (texto padrão)

**Interfaces:**
- Consumes: `Student.pay_token` (Task 2).
- Produces:
  - `pay_url(token: str) -> str` em `services/billing.py` → `f'{settings.WEB_APP_URL}/pagar/{token}'` (importar o settings do core como `app_settings` para não colidir com o parâmetro `settings`).
  - `StudentContact.pay_token: str`.
  - Marcador `{link}` em `whatsapp_url`.
  - `StudentBillingRead.pay_url: str` e `StudentBillingApiRead.pay_url: str`.

- [ ] **Step 1: Write the failing tests**

```python
# test_billing_settings_api.py — trocar a asserção do texto padrão por:
assert DEFAULT_MESSAGE_TEMPLATE == (
    'Olá, {nome}! Tudo bem? 🥋\n\n'
    'Passando para lembrar que a mensalidade da {academia} está em '
    'aberto: {valor} ({meses}).\n\n'
    'Para pagar pelo Pix, é só tocar aqui:\n{link}\n\n'
    'Se já pagou, desconsidere. Obrigado!'
)

# test_billing_api.py
async def test_whatsapp_message_has_pay_link(client, db_session, monkeypatch):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    body = await _read(client, ctx['student_id'], ctx['headers'])
    _, text = _message(body['whatsapp_url'])
    token = await _pay_token(db_session, ctx['student_id'])
    assert f'http://localhost:5173/pagar/{token}' in text
    assert body['pay_url'] == f'http://localhost:5173/pagar/{token}'

async def test_custom_template_without_link_gets_it_appended(client, db_session, monkeypatch):
    ctx = await _overdue_student(client, db_session, monkeypatch)
    await client.put('/api/v1/academy/billing-settings', headers=ctx['headers'],
                     json={'message_template': 'Oi, {nome}!'})
    body = await _read(client, ctx['student_id'], ctx['headers'])
    _, text = _message(body['whatsapp_url'])
    token = await _pay_token(db_session, ctx['student_id'])
    assert text == f'Oi, Ana!\n\nPara pagar pelo Pix, toque aqui: http://localhost:5173/pagar/{token}'
```

`_pay_token(db_session, student_public_id) -> str`: helper local do arquivo de teste (`select(Student.pay_token).where(Student.public_id == UUID(...))`). Em `test_whatsapp_message_uses_template`, acrescentar `|{link}` ao template e ao texto esperado. Se `WEB_APP_URL` dos testes não for `http://localhost:5173`, montar o esperado com `settings.WEB_APP_URL`.

- [ ] **Step 2: Run to verify they fail**

Run: `poetry run pytest tests/api/test_billing_api.py -k "whatsapp or pay_link or template" tests/api/test_billing_settings_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

`_contacts` passa a selecionar `Student.pay_token`. Em `whatsapp_url`: `'{link}': pay_url(student.pay_token)`; se o texto (antes da troca) não tem `{link}`, acrescentar `'\n\nPara pagar pelo Pix, toque aqui: {link}'` antes de trocar. `student_billing` preenche `pay_url` (buscar o token do aluno). Atualizar o `from_internal`.

- [ ] **Step 4: Run to verify they pass** (mesmo comando) — Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests/api
git commit -m "feat: WhatsApp billing message carries the payment page link"
```

---

### Task 4: Endpoint público da página de pagamento

**Files:**
- Create: `src/dojoflow/api/routes/public_pay.py`, `src/dojoflow/schemas/public_pay.py`, `src/dojoflow/api/dependencies/rate_limit.py`
- Modify: `src/dojoflow/services/billing.py` (método novo), `src/dojoflow/main.py` (registrar rota)
- Test: `tests/api/test_public_pay.py`

**Interfaces:**
- Consumes: `pix_copy_paste` (Task 1), `Student.pay_token`, `pix_key_type`, `pix_city` (Task 2), `choose_recipient`, `month_name`, `local_today`.
- Produces:
  - `GET /api/v1/public/pay/{token}` (sem autenticação) → `PublicPaymentRead`; token inexistente ou academia bloqueada → `NotFoundError('Payment link not found.', code='PAY_LINK_INVALID')`.
  - Schemas: `PublicPaymentItemRead(label: str, amount: Decimal)`; `PublicPaymentRead(academy_name: str, master_name: str, greeting_name: str, status: Literal['open', 'clear'], items: list[PublicPaymentItemRead], total: Decimal, recipient_name: str, pix_code: str | None)`.
  - `BillingService.public_payment(token: str, today: date | None = None) -> PublicPaymentRead | None`.
  - `RateLimiter(limit: int, window_seconds: int)` com `async __call__(request: Request) -> None` (levanta `HTTPException(429)`) e `reset() -> None`; instância `public_pay_limiter = RateLimiter(30, 60)` usada como dependência da rota.

- [ ] **Step 1: Write the failing tests** (usar `_overdue_student`-like setup: jan e fev/2027 de R$ 100, hoje 20/02/2027; fixture autouse que chama `public_pay_limiter.reset()`)

```python
async def test_public_pay_open(client, db_session, monkeypatch):
    # settings: pix_key 'dojo@exemplo.com', tipo 'email', recebedor 'Mestre Web', cidade 'Goiânia'
    body = (await client.get(f'/api/v1/public/pay/{token}')).json()
    assert body['academy_name'] == 'Academia Web Teste'
    assert body['master_name'] == SEED.master_name
    assert body['greeting_name'] == 'Ana'
    assert body['status'] == 'open'
    assert body['items'] == [
        {'label': 'Mensalidade · janeiro', 'amount': '100.00'},
        {'label': 'Mensalidade · fevereiro', 'amount': '100.00'},
    ]
    assert body['total'] == '200.00'
    assert body['recipient_name'] == 'Mestre Web'
    assert body['pix_code'].startswith('000201')
    assert '5406200.00' in body['pix_code']
    assert '6007GOIANIA' in body['pix_code']
    assert set(body) == {'academy_name', 'master_name', 'greeting_name', 'status',
                         'items', 'total', 'recipient_name', 'pix_code'}

async def test_public_pay_minor_greets_responsible(...):
    # aluna Ana nascida em 2015 + responsável Maria Lima com telefone
    assert body['greeting_name'] == 'Maria'
    assert body['items'][0]['label'] == 'Mensalidade de Ana · janeiro'

async def test_public_pay_clear_after_paying(...):
    # paga R$ 200 → status 'clear', items [], total '0.00', pix_code None

async def test_public_pay_without_pix_settings_has_no_code(...):
    # sem configurações → status 'open', pix_code None, recipient_name = nome da academia

async def test_public_pay_unknown_token_404(client):
    response = await client.get('/api/v1/public/pay/nao-existe')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'PAY_LINK_INVALID'

async def test_public_pay_blocked_academy_404(...):
    # Academy.status = BLOCKED → 404 PAY_LINK_INVALID

async def test_public_pay_rate_limited(client):
    for _ in range(30):
        await client.get('/api/v1/public/pay/x')
    assert (await client.get('/api/v1/public/pay/x')).status_code == HTTPStatus.TOO_MANY_REQUESTS
```

Os valores de dinheiro seguem o formato que o resto da API já devolve para `Decimal` (conferir em `test_billing_api.py` e ajustar as strings se for número).

- [ ] **Step 2: Run to verify they fail**

Run: `poetry run pytest tests/api/test_public_pay.py -v`
Expected: FAIL (404 da rota inexistente / import error)

- [ ] **Step 3: Implement**

`public_payment`: busca aluno por `pay_token` junto com `Academy` (status ativo); `ensure_monthly_charges(academy_id, today)`; `_charges(..., Enrollment.student_id == id)` filtrando `status == 'overdue'`, ordem por `reference_month` crescente. Rótulo: taxa → `'Taxa de matrícula'`; mensalidade → `'Mensalidade · ' + month_name(ref, today.year)`; se quem recebe é responsável, `'Mensalidade de <primeiro nome do aluno> · <mês>'` (e `'Taxa de matrícula de <primeiro nome>'`); se os itens têm mais de uma modalidade, acrescentar `' · <modalidade>'`. `greeting_name`: primeiro nome do contato de `choose_recipient`; sem contato, primeiro nome do aluno. `master_name`: `Master.name` do menor `Master.id` da academia. `recipient_name`: `recipient_name` ou nome da academia. `pix_code`: só com itens e com chave + tipo + cidade. Rota pública num `APIRouter(prefix='/public', tags=['Public'])` registrado em `main.py` com `API_V1_PREFIX`. `RateLimiter`: dicionário IP → `deque` de instantes (`time.monotonic()`), chave `request.client.host`.

- [ ] **Step 4: Run to verify they pass** — Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests/api/test_public_pay.py
git commit -m "feat: public payment page endpoint"
```

---

### Task 5: Gerar link novo

**Files:**
- Modify: `src/dojoflow/api/routes/billing.py`, `src/dojoflow/services/billing.py`, `src/dojoflow/schemas/billing_api.py`
- Test: `tests/api/test_public_pay.py`

**Interfaces:**
- Consumes: `new_pay_token` (Task 2), `pay_url` (Task 3).
- Produces: `POST /api/v1/students/{student_id}/billing/pay-link` → `PayLinkApiRead(pay_url: str)`; `BillingService.renew_pay_token(academy_id: int, student_id: int) -> str` (`@transactional`, devolve a URL nova).

- [ ] **Step 1: Write the failing tests**

```python
async def test_renew_pay_link_invalidates_old(client, db_session, monkeypatch):
    old = await _pay_token(db_session, student_id)
    response = await client.post(f'/api/v1/students/{student_id}/billing/pay-link', headers=headers)
    assert response.status_code == HTTPStatus.OK
    new_url = response.json()['pay_url']
    assert not new_url.endswith(old)
    assert (await client.get(f'/api/v1/public/pay/{old}')).status_code == HTTPStatus.NOT_FOUND
    assert (await client.get(f'/api/v1/public/pay/{new_url.rsplit("/", 1)[1]}')).status_code == HTTPStatus.OK

async def test_renew_pay_link_other_academy_404(client, db_session):
    # aluno da academia seed; headers de other_academy_headers → 404
```

- [ ] **Step 2: Run to verify they fail** — `poetry run pytest tests/api/test_public_pay.py -k renew -v` → FAIL
- [ ] **Step 3: Implement** — rota usa `StudentIdDep` + `CurrentMasterDep` como as outras de `/students/{student_id}/billing`.
- [ ] **Step 4: Run to verify they pass** — PASS
- [ ] **Step 5: Commit** — `git commit -m "feat: renew a student's payment link"`

---

### Task 6: Frontend — Configurações → Cobrança

**Files:**
- Modify: `frontend/src/lib/api/schema.d.ts` (gerado), `frontend/src/features/settings/components/BillingSettingsSection.tsx`, `frontend/src/features/billing/whatsapp.ts`

**Interfaces:**
- Consumes: campos `pix_key_type`, `pix_city` e o novo texto padrão (Tasks 2–3).
- Produces: `TemplateValues` ganha `link: string`.

- [ ] **Step 1: Regenerar tipos** — com a API rodando (`poetry run task run`): `cd frontend && npm run gen:api`. Expected: `schema.d.ts` com `pix_key_type`, `pix_city`, `pay_url`, `PublicPaymentRead`, `/api/v1/public/pay/{token}`.
- [ ] **Step 2: Formulário**
  - Bloco Pix: `<select>` (ou o Select do shadcn já usado no projeto) "Tipo da chave" com CPF, CNPJ, Celular, E-mail, Aleatória, ao lado da chave; campo "Cidade" (até 60, placeholder "cidade de quem recebe"). Descrição do bloco: "Usados para montar o código Pix que o aluno copia."
  - Validação no cliente: chave preenchida sem tipo → "Escolha o tipo da chave." (o 422 do backend continua sendo mostrado por `showApiError`).
  - Aviso (mesmo estilo `TriangleAlert`) quando há chave sem tipo ou sem cidade: "Sem tipo da chave e cidade, o aluno não consegue copiar o código Pix na página de pagamento."
  - `DEFAULT_MESSAGE_TEMPLATE` igual ao do backend (Task 3); marcador `{link}` ("link da página de pagamento") **antes** de `{pix}` na lista; prévia usa `link: 'katsuflow.com.br/pagar/…'` — usar `` `${window.location.origin}/pagar/exemplo` ``.
  - O aviso antigo "Sem chave Pix, a mensagem sai com o 'Pix:' vazio" continua só quando o texto usa `{pix}`.
- [ ] **Step 3: Verificar** — `cd frontend && npm run build && npm run lint` → sem erros; abrir Configurações no navegador (login em `1 · Fundamentos/05 · Ambiente local`), salvar uma chave celular com pontuação e ver ela voltar normalizada.
- [ ] **Step 4: Commit** — `git commit -m "feat: Pix key type and city in billing settings"`

---

### Task 7: Frontend — página pública `/pagar/:token`

**Files:**
- Create: `frontend/src/features/pay/PayPage.tsx`, `frontend/src/features/pay/api.ts`
- Modify: `frontend/src/app/router.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/public/pay/{token}` → `Schemas['PublicPaymentRead']` (Task 4).
- Produces: rota `{ path: '/pagar/:token', element: <PayPage /> }` no topo do router, fora de `/app` e do `RequireAuth`.

- [ ] **Step 1: Página** — layout B da spec (protótipo: Obsidian `Anexos/pagina-pagamento-pix.html`), largura máx. ~420px centralizada:
  1. Faixa com gradiente `#2a2d33` → `#155e75`, texto branco: nome da academia (negrito) e "Mestre <master_name>".
  2. Cartão branco sobreposto à faixa (margem negativa): "Olá, <greeting_name> · total em aberto", total grande (`formatMoney` de `@/lib/format`, se existir; senão o formatador já usado em `StudentBillingTab`), selo "N mensalidades" (`items.length`; "1 mensalidade").
  3. Cartão "O que está em aberto" com `items` (rótulo à esquerda, valor à direita).
  4. Cartão "Pagar para": `recipient_name` + "Recebe pelo Pix".
  5. Com `pix_code`: botão "Copiar código Pix" (`navigator.clipboard.writeText`; se falhar, mostrar o código num `<textarea readOnly>` selecionado para cópia manual). Depois de copiar: botão vira "Código copiado!" e aparece "Agora abra o app do seu banco → Pix → Pix copia e cola." Texto fixo abaixo: "Cole no app do seu banco, em 'Pix copia e cola'. O valor de R$ X já vai preenchido." Sem `pix_code` (e status `open`): "Fale com a academia para pagar."
  6. `status === 'clear'`: no lugar dos cartões 2–5, cartão "Tudo em dia! Nenhuma mensalidade pendente."
  7. Rodapé: "Cobrança enviada pelo" + símbolo do lutador (recorte via CSS de `@/assets/brand/logo-light.png`: contêiner `h-7 w-[30px] overflow-hidden`, imagem `h-7 max-w-none`) + "Katsu" em `#155e75` e "flow" em `#2a2d33`, negrito.
  8. 404 → "Link inválido ou expirado. Peça um novo link para a academia." 429/erro de rede → "Não foi possível carregar. Tente de novo." com botão.
  9. Força tema claro: no mount `applyMode('light')`, no unmount volta ao `currentMode()` salvo antes (funções de `@/app/theme`).
- [ ] **Step 2: Verificar** — `npm run build && npm run lint`; abrir `http://localhost:5173/pagar/<token de um aluno com atraso>` (pegar token no banco: `docker exec dojoflow_postgres psql -U postgres -d dojoflow -c "select name, pay_token from student limit 5"`) no modo celular do DevTools (largura 375px): conferir os estados aberto, tudo em dia, link inválido e copiar.
- [ ] **Step 3: Commit** — `git commit -m "feat: public Pix payment page"`

---

### Task 8: Frontend — link de pagamento na ficha do aluno

**Files:**
- Modify: `frontend/src/features/billing/components/StudentBillingTab.tsx`, `frontend/src/features/billing/api.ts`, `frontend/src/features/billing/hooks.ts`

**Interfaces:**
- Consumes: `pay_url` em `StudentBillingApiRead` (Task 3), `POST /api/v1/students/{student_id}/billing/pay-link` (Task 5).
- Produces: hook `useRenewPayLink(studentId)` seguindo o padrão dos hooks de mutação existentes em `hooks.ts` (invalida a leitura da aba).

- [ ] **Step 1: UI** — na aba Mensalidades, perto do botão WhatsApp: linha "Link de pagamento" com botão "Copiar link" e botão discreto "Gerar link novo" que abre `ConfirmDialog` ("O link antigo para de funcionar. Quem já recebeu precisa receber o novo.") e, ao confirmar, chama o hook e mostra toast "Link novo gerado".
- [ ] **Step 2: Verificar** — `npm run build && npm run lint`; no navegador, gerar link novo e abrir o antigo (deve mostrar "Link inválido…").
- [ ] **Step 3: Commit** — `git commit -m "feat: copy and renew payment link on the student page"`

---

### Task 9: Fechamento

- [ ] **Step 1:** `poetry run task lint && poetry run task test` → tudo verde.
- [ ] **Step 2:** `cd frontend && npm run build && npm run lint` → sem erros.
- [ ] **Step 3:** Passeio no navegador: Configurações (tipo + cidade) → Mensalidades → WhatsApp (prévia com o link) → abrir o link no modo celular → copiar o código → colar num validador de BR Code ou no app do banco, sem confirmar o pagamento, e conferir nome, cidade e valor.
- [ ] **Step 4:** Atualizar o status da spec (repo e Obsidian `2 · Especificações/Página de pagamento Pix (design)`) e o índice `DojoFlow.md` ("Próxima sessão").
- [ ] **Step 5:** Commit final; PR só com o "sim" do Thiago.
