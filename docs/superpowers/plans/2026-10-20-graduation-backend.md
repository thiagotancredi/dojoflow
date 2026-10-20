# Faixas e listas de graduação — Plano: Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** API para a academia cadastrar faixas por modalidade, registrar o histórico de faixas de cada matrícula e montar listas de graduação com aviso de apto na data do exame.

**Architecture:** Mesmo desenho do resto do backend: models + migration Alembic, repositórios `BaseRepository[Model]`, services com IDs inteiros e `@transactional`, rotas que convertem `public_id` (UUID) ↔ `id` via dependencies. As regras de tempo (soma de meses pelo calendário, apto/não apto) ficam num módulo puro, testado sem banco. A lista guarda um retrato (faixa + data) por item, então não muda quando o aluno gradua depois.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 async + psycopg 3, Alembic, Pydantic v2, pytest + pytest-asyncio + httpx, PostgreSQL 17.

**Spec:** `docs/superpowers/specs/2026-10-20-graduation-lists-design.md` (seções Domínio, Telas 1–3 com 2a e 2b → contratos que o front vai consumir). Protótipo do fluxo: `docs/superpowers/specs/2026-10-20-graduation-flow-prototype.html`. O frontend (desenho da faixa, tela de Faixas, Graduações, ficha do aluno) é um **plano separado**, escrito depois deste.

## Global Constraints

- ruff (`line-length = 79`, `quote-style = 'single'`, regras `I F E W PL PT`), `ruff format --check`, `typos` e `alembic check` passam ao fim de cada task (o CI roda os quatro).
- Código em inglês; `detail` dos erros em inglês; o front traduz pelo `code`.
- Toda rota do site recebe e devolve só `public_id` (UUID), nunca `id` inteiro.
- Toda tabela nova tem `academy_id`, e toda consulta filtra pela academia do mestre logado.
- Erros de domínio: `{"detail": str, "code": str}` (404 `NotFoundError`, 409 `ConflictError`); validação de payload = 422 padrão do FastAPI.
- Cores: hex `#rrggbb`, guardadas em minúsculas. Cor padrão das marcas: `#d4a017`.
- Marcas (graus/dan): inteiro **0–10**, padrão 0.
- Tempo mínimo: número **> 0** + unidade `days` | `months` | `years`, os dois juntos ou nenhum.
- Meses e anos somam pelo calendário (15/01 + 1 mês = 15/02); dia inexistente cai no último dia do mês (31/01 + 1 mês = 28/02 ou 29/02).
- "Hoje" = data em `America/Sao_Paulo`.
- Nada muda no bot do Telegram.
- Testes: `docker compose up -d postgres` antes; banco de teste na porta 5434 (`tests/conftest.py`).
- Commits pequenos, `tipo: descrição` em inglês, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **Fim de mês:** faixa em 31/01 com tempo de 1 mês. Esperado: apto a partir de 28/02 (29/02 em ano bissexto), sem erro e sem pular para março. → teste na Task 1.
- **Duas graduações na mesma data:** o mestre lança "Branca" e "Amarela" em 10/03. Esperado: a faixa atual é a lançada por último. → teste na Task 4.
- **Aluno gradua depois de entrar na lista:** esperado que o item da lista continue mostrando a faixa e a data do retrato. → teste na Task 6.
- **Faixa de outra modalidade (ou de outra academia)** no histórico ou como faixa pretendida. Esperado: 409 `BELT_MODALITY_MISMATCH` (ou 404 `BELT_NOT_FOUND` se for de outra academia), nunca gravar. → testes nas Tasks 4 e 6.
- **Remover a modalidade da academia e adicionar de novo:** esperado que as faixas continuem lá. → teste na Task 3.
- **Cadastro de aluno com faixa inválida** (de outra modalidade): esperado que **nada** seja gravado (nem aluno, nem matrícula), não um aluno criado sem faixa. → teste na Task 7.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `src/dojoflow/shared/enums.py` (modificar) | `DurationUnit`, `Eligibility` |
| `src/dojoflow/services/belt_rules.py` (criar) | Regras puras: `add_duration`, `eligible_on`, `evaluate_eligibility`, `local_today` |
| `src/dojoflow/models/belt.py` (criar) | `Belt` |
| `src/dojoflow/models/enrollment_belt.py` (criar) | `EnrollmentBelt` (histórico) |
| `src/dojoflow/models/graduation_list.py` (criar) | `GraduationList`, `GraduationListEntry` |
| `src/dojoflow/models/__init__.py` (modificar) | Exporta os models novos |
| `migrations/versions/<rev>_create_belts_and_graduation_lists.py` (criar) | Tabelas + Musculação e Crossfit no catálogo |
| `src/dojoflow/repositories/{belt,enrollment_belt,graduation_list,graduation_list_entry}.py` (criar) | Repositórios vazios (`pass`) |
| `src/dojoflow/schemas/belt.py` / `belt_api.py` (criar) | Payload, leitura interna e de API das faixas |
| `src/dojoflow/services/belt_presets.py` (criar) | `TAEKWONDO_PRESET` (19 faixas) |
| `src/dojoflow/services/belt.py` (criar) | `BeltService` |
| `src/dojoflow/schemas/enrollment_belt.py` / `enrollment_belt_api.py` (criar) | Histórico |
| `src/dojoflow/services/enrollment_belt.py` (criar) | `EnrollmentBeltService` |
| `src/dojoflow/schemas/graduation_list.py` / `graduation_list_api.py` (criar) | Listas, itens, candidatos |
| `src/dojoflow/services/graduation_list.py` (criar) | `GraduationListService` |
| `src/dojoflow/api/dependencies/{belt,enrollment_belt,graduation_list}.py` (criar) | `*ServiceDep` |
| `src/dojoflow/api/dependencies/public_ids.py` (modificar) | Resolvers novos; `EnrollmentIdDep` sai de `routes/students.py` para cá |
| `src/dojoflow/api/routes/{belts,enrollment_belts,graduation_lists}.py` (criar) | Rotas |
| `src/dojoflow/main.py` (modificar) | Registra os routers |
| `src/dojoflow/schemas/modality.py`, `modality_api.py`, `services/modality.py` (modificar) | `has_belts` nas opções de modalidade |
| `tests/helpers/graduation.py` (criar) | Helpers de teste (modalidade ativa, aluno, faixas) |
| `src/dojoflow/schemas/student_api.py`, `src/dojoflow/api/routes/students.py` (modificar) | Faixa atual opcional no cadastro e na nova matrícula (Task 7) |
| `tests/services/test_belt_rules.py`, `tests/api/test_{belts,enrollment_belts,graduation_lists}_api.py`, `tests/api/test_students_belt.py` (criar) | Testes |

---

### Task 1: Regras de tempo e aptidão (módulo puro)

**Files:**
- Modify: `src/dojoflow/shared/enums.py`
- Create: `src/dojoflow/services/belt_rules.py`
- Test: `tests/services/test_belt_rules.py`

**Interfaces:**
- Produces:
  - `class DurationUnit(str, enum.Enum)`: `DAYS = 'days'`, `MONTHS = 'months'`, `YEARS = 'years'`
  - `class Eligibility(str, enum.Enum)`: `ELIGIBLE = 'eligible'`, `NOT_YET = 'not_yet'`, `NO_BELT = 'no_belt'`, `NO_REQUIREMENT = 'no_requirement'`
  - `add_duration(start: date, amount: int, unit: DurationUnit) -> date`
  - `eligible_on(graduated_on: date, amount: int | None, unit: DurationUnit | None) -> date | None` (None quando a faixa não tem tempo mínimo)
  - `evaluate_eligibility(graduated_on: date | None, amount: int | None, unit: DurationUnit | None, reference: date) -> Eligibility`
  - `local_today() -> date` (data em `ZoneInfo('America/Sao_Paulo')`)

- [ ] **Step 1: Escrever os testes**

```python
from datetime import date

import pytest

from dojoflow.services.belt_rules import (
    add_duration, eligible_on, evaluate_eligibility,
)
from dojoflow.shared.enums import DurationUnit as U, Eligibility as E


@pytest.mark.parametrize(('start', 'amount', 'unit', 'expected'), [
    (date(2026, 1, 15), 1, U.MONTHS, date(2026, 2, 15)),
    (date(2026, 1, 31), 1, U.MONTHS, date(2026, 2, 28)),
    (date(2028, 1, 31), 1, U.MONTHS, date(2028, 2, 29)),
    (date(2026, 11, 30), 3, U.MONTHS, date(2027, 2, 28)),
    (date(2024, 2, 29), 1, U.YEARS, date(2025, 2, 28)),
    (date(2026, 1, 1), 90, U.DAYS, date(2026, 4, 1)),
])
def test_add_duration_uses_calendar(start, amount, unit, expected): ...
    # assert add_duration(start, amount, unit) == expected

def test_eligible_exactly_on_exam_day():
    # evaluate_eligibility(date(2026, 8, 1), 3, U.MONTHS, date(2026, 11, 1)) == E.ELIGIBLE
    # ... reference=date(2026, 10, 31) == E.NOT_YET

def test_eligibility_is_measured_on_exam_date():
    # exemplo da spec: 2 meses hoje (20/10), precisa de 3, exame em 20/11
    # evaluate_eligibility(date(2026, 8, 20), 3, U.MONTHS, date(2026, 11, 20)) == E.ELIGIBLE

def test_no_belt_and_no_requirement():
    # evaluate_eligibility(None, 3, U.MONTHS, date(2026, 1, 1)) == E.NO_BELT
    # evaluate_eligibility(date(2020, 1, 1), None, None, date(2026, 1, 1)) == E.NO_REQUIREMENT

def test_eligible_on():
    # eligible_on(date(2026, 8, 1), 3, U.MONTHS) == date(2026, 11, 1)
    # eligible_on(date(2026, 8, 1), None, None) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/services/test_belt_rules.py -v`
Expected: FAIL (`ModuleNotFoundError: dojoflow.services.belt_rules`)

- [ ] **Step 3: Implementar os enums e `belt_rules.py`**

Sem dependência nova (nada de `dateutil`). Meses: some ao índice `ano*12 + (mês-1)`, volte com `divmod` e limite o dia com `calendar.monthrange`. Anos = 12 meses. Dias = `timedelta`. `ELIGIBLE` quando `eligible_on(...) <= reference`.

- [ ] **Step 4: Rodar e ver passar**

Run: `poetry run pytest tests/services/test_belt_rules.py -v` → PASS. Depois `poetry run ruff check . && poetry run ruff format --check .`.

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow/shared/enums.py src/dojoflow/services/belt_rules.py tests/services/test_belt_rules.py
git commit -m "feat: add belt duration and eligibility rules"
```

---

### Task 2: Tabelas, migration e catálogo (Musculação, Crossfit)

**Files:**
- Create: `src/dojoflow/models/belt.py`, `src/dojoflow/models/enrollment_belt.py`, `src/dojoflow/models/graduation_list.py`
- Modify: `src/dojoflow/models/__init__.py`
- Create: `migrations/versions/<rev>_create_belts_and_graduation_lists.py` (down_revision `a7b8c9d0e1f2`)
- Create: `src/dojoflow/repositories/belt.py`, `enrollment_belt.py`, `graduation_list.py`, `graduation_list_entry.py`

**Interfaces:**
- Consumes: `DurationUnit` (Task 1); helpers de `database/helper_mapped_columns.py`.
- Produces (todas herdam `BaseModel`, ou seja, `id`, `public_id`, `created_at`, `updated_at`):
  - `Belt` / tabela `belt`: `academy_id` fk, `modality_id` fk, `name` str(80), `primary_color` str(7), `stripe_color` str(7) nullable, `marks` int default 0, `marks_color` str(7) default `'#d4a017'`, `tip_color` str(7) nullable, `min_time_amount` int nullable, `min_time_unit` `enum_column(DurationUnit, nullable=True)`, `position` int. `UniqueConstraint('academy_id', 'modality_id', 'name', name='uq_belt_academy_modality_name')`. **Sem** unique em `position` (o reordenamento troca posições em sequência).
  - `EnrollmentBelt` / `enrollment_belt`: `academy_id`, `enrollment_id`, `belt_id` (fks), `graduated_on` date.
  - `GraduationList` / `graduation_list`: `academy_id`, `modality_id` (fks), `name` str(120), `exam_date` date.
  - `GraduationListEntry` / `graduation_list_entry`: `academy_id`, `graduation_list_id`, `enrollment_id`, `target_belt_id` (fks), `snapshot_belt_id` fk nullable, `snapshot_graduated_on` date nullable. `UniqueConstraint('graduation_list_id', 'enrollment_id', name='uq_graduation_list_entry_list_enrollment')`.
  - `BeltRepository`, `EnrollmentBeltRepository`, `GraduationListRepository`, `GraduationListEntryRepository` (só `pass`, como `ModalityRepository`).

- [ ] **Step 1: Criar os models, exportar em `models/__init__.py` e criar os repositórios**

- [ ] **Step 2: Gerar a migration**

Run: `docker compose up -d postgres && poetry run alembic upgrade head && poetry run alembic revision --autogenerate -m "create belts and graduation lists"`
Expected: arquivo novo com `create_table` das 4 tabelas.

- [ ] **Step 3: Completar a migration à mão**

No `upgrade()`, depois das tabelas: `op.execute("INSERT INTO modality (name, emoji, is_active) VALUES ('Musculação', '🏋️', true), ('Crossfit', '💪', true) ON CONFLICT (name) DO NOTHING")`. No `downgrade()`, só derrubar as tabelas, com um comentário dizendo que as duas modalidades ficam no catálogo, porque podem já ter matrículas. Formatar no estilo das migrations existentes.

- [ ] **Step 4: Validar a migration**

Run: `poetry run alembic upgrade head && poetry run alembic check && poetry run alembic downgrade -1 && poetry run alembic upgrade head`
Expected: `No new upgrade operations detected.` e nenhum erro na ida e volta.

Run: `docker exec dojoflow_postgres psql -U postgres -d dojoflow -c "select name, emoji from modality where name in ('Musculação','Crossfit')"`
Expected: 2 linhas.

- [ ] **Step 5: Suíte completa**

Run: `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos .` → tudo verde (os testes criam o schema por `create_all`, então os models novos entram aqui).

- [ ] **Step 6: Commit**

```bash
git add src/dojoflow/models src/dojoflow/repositories migrations/versions
git commit -m "feat: add belt, enrollment belt and graduation list tables"
```

---

### Task 3: Faixas da academia (CRUD, ordem, sequência padrão do Taekwondo)

**Files:**
- Create: `src/dojoflow/schemas/belt.py`, `src/dojoflow/schemas/belt_api.py`, `src/dojoflow/services/belt_presets.py`, `src/dojoflow/services/belt.py`, `src/dojoflow/api/dependencies/belt.py`, `src/dojoflow/api/routes/belts.py`
- Modify: `src/dojoflow/api/dependencies/public_ids.py`, `src/dojoflow/main.py`, `src/dojoflow/schemas/modality.py`, `src/dojoflow/schemas/modality_api.py`, `src/dojoflow/services/modality.py`, `tests/api/test_modalities_api.py`
- Create: `tests/helpers/graduation.py`
- Test: `tests/api/test_belts_api.py`

**Interfaces:**
- Consumes: `Belt`, `BeltRepository`, `EnrollmentBelt`, `GraduationListEntry` (Task 2); `DurationUnit` (Task 1).
- Produces:
  - `schemas/belt.py`:
    - `HexColor = Annotated[str, StringConstraints(pattern=r'^#[0-9a-fA-F]{6}$', to_lower=True)]`
    - `BeltPayload(BaseModel)`: `name: str` (strip, 1–80), `primary_color: HexColor`, `stripe_color: HexColor | None = None`, `marks: int = Field(0, ge=0, le=10)`, `marks_color: HexColor = '#d4a017'`, `tip_color: HexColor | None = None`, `min_time_amount: int | None = Field(None, gt=0)`, `min_time_unit: DurationUnit | None = None`; `model_validator`: amount e unit juntos ou nenhum. É também o corpo do POST/PUT na API (não tem ids).
    - `BeltRead(BeltPayload)`: `id: int`, `public_id: UUID`, `modality_id: int`, `position: int`.
  - `schemas/belt_api.py`: `BeltApiRead` (`id: UUID` + todos os campos de `BeltPayload` + `position`), com `from_internal(belt: BeltRead)`; `BeltOrderRequest(belt_ids: list[UUID])`.
  - `TAEKWONDO_PRESET: tuple[BeltPayload, ...]` (tabela abaixo).
  - `BeltService(belt_repository, db_session)`:
    - `list_by_modality(academy_id: int, modality_id: int) -> list[BeltRead]` (por `position`)
    - `get(academy_id: int, belt_id: int) -> BeltRead` (404 `BELT_NOT_FOUND`)
    - `next_belt(academy_id: int, modality_id: int, current_belt_id: int | None) -> BeltRead | None` (None atual → a primeira; última → None)
    - `create(academy_id, modality_id, data: BeltPayload) -> BeltRead` (entra no fim: `position = max + 1`)
    - `update(academy_id, belt_id, data: BeltPayload) -> BeltRead` (troca tudo, `null` limpa)
    - `delete(academy_id, belt_id) -> None` (renumera as restantes 1..n)
    - `reorder(academy_id, modality_id, belt_ids: list[int]) -> None` (`position = índice + 1`)
    - `apply_taekwondo_preset(academy_id, modality_id) -> list[BeltRead]`
  - Erros: nome repetido na mesma (academia, modalidade), comparando sem maiúsculas e espaços nas pontas → 409 `BELT_NAME_TAKEN`; faixa usada em `enrollment_belt.belt_id`, `graduation_list_entry.target_belt_id` ou `.snapshot_belt_id` → 409 `BELT_IN_USE` (mensagem: `This belt is used in a student's history or in a graduation list.`); `belt_ids` diferente do conjunto atual (falta, sobra ou repete) → 409 `BELT_ORDER_MISMATCH`; preset com faixas já cadastradas → 409 `BELTS_ALREADY_EXIST`; preset em modalidade cujo nome não é `Taekwondo` → 409 `PRESET_NOT_AVAILABLE`.
  - `public_ids.py`: `EnabledModalityIdDep` (path `modality_id: UUID` → `int`; 404 `MODALITY_NOT_FOUND` se não existe, 404 `MODALITY_NOT_ENABLED` se a academia não oferece); `BeltIdDep` (path `belt_id: UUID`, filtro `Belt.academy_id`, 404 `BELT_NOT_FOUND`); `resolve_belt_id(db_session, public_id, academy_id) -> int` (para UUIDs no corpo).
  - Rotas (tag `Belts`):
    - `GET /academy/modalities/{modality_id}/belts` → `list[BeltApiRead]`
    - `POST /academy/modalities/{modality_id}/belts` (corpo `BeltPayload`) → 201 `BeltApiRead`
    - `POST /academy/modalities/{modality_id}/belts/taekwondo-preset` → 201 `list[BeltApiRead]`
    - `PUT /academy/modalities/{modality_id}/belts/order` (corpo `BeltOrderRequest`) → 204
    - `PUT /academy/belts/{belt_id}` (corpo `BeltPayload`) → 200 `BeltApiRead`
    - `DELETE /academy/belts/{belt_id}` → 204
  - `ModalityOptionRead.has_belts: bool = False` e `ModalityOptionApiRead.has_belts: bool` (true se a academia tem ≥ 1 faixa na modalidade; uma consulta só em `list_academy_options`). É o que a tela "Nova lista" usa para filtrar.
  - `tests/helpers/graduation.py`:
    - `enable_modality(client, db_session, headers, name: str) -> str` (cria no catálogo, liga na academia, devolve o UUID)
    - `create_belt(client, headers, modality_id: str, name: str, **fields) -> dict` (POST; padrão `primary_color='#f8fafc'`)
    - `create_student(client, headers, modality_id: str, name: str = 'Ana Lima', status: str = 'active') -> tuple[str, str]` (POST `/students`, devolve `(student_id, enrollment_id)` lendo a ficha)

**Sequência padrão do Taekwondo** (marcas sempre douradas `#d4a017`, sem ponta; cores da paleta do protótipo aprovado):

| # | name | primary | stripe | marks | tempo |
|---|---|---|---|---|---|
| 1 | Branca | `#f8fafc` | — | 0 | 3 months |
| 2 | Cinza | `#9ca3af` | — | 0 | 3 months |
| 3 | Amarela | `#facc15` | — | 0 | 3 months |
| 4 | Laranja | `#f97316` | — | 0 | 3 months |
| 5 | Verde | `#16a34a` | — | 0 | 3 months |
| 6 | Verde e azul | `#16a34a` | `#1d4ed8` | 0 | 3 months |
| 7 | Azul | `#1d4ed8` | — | 0 | 3 months |
| 8 | Azul e vermelha | `#1d4ed8` | `#dc2626` | 0 | 3 months |
| 9 | Vermelha | `#dc2626` | — | 0 | 3 months |
| 10 | Vermelha e preta | `#dc2626` | `#111827` | 0 | 6 months |
| 11–19 | Preta 1º Dan … Preta 9º Dan | `#111827` | — | 1…9 | 1, 2, 3, 4, 5, 6, 8, 9 years; 9º Dan sem tempo |

- [ ] **Step 1: Escrever os helpers e os testes** (`tests/api/test_belts_api.py`)

```python
async def test_create_and_list_belts_in_order(client, db_session):
    # Branca (primary '#F8FAFC', 3 months) e Amarela; GET devolve as duas
    # com position 1 e 2, primary_color '#f8fafc', marks 0, marks_color '#d4a017',
    # stripe_color None, min_time_amount 3, min_time_unit 'months'

async def test_belt_name_unique_within_modality(client, db_session):
    # 'Branca' e depois ' branca ' na mesma modalidade -> 409 BELT_NAME_TAKEN
    # 'Branca' em outra modalidade -> 201

@pytest.mark.parametrize('bad', [
    {'min_time_amount': 3},                              # sem unidade
    {'min_time_unit': 'months'},                         # sem número
    {'min_time_amount': 0, 'min_time_unit': 'months'},
    {'marks': 11},
    {'primary_color': 'red'},
])
async def test_invalid_belt_payload_is_422(client, db_session, bad): ...

async def test_update_belt_replaces_fields(client, db_session):
    # cria com stripe '#1d4ed8'; PUT com name 'Verde' e stripe_color None
    # -> 200, stripe_color None, position igual

async def test_reorder_belts(client, db_session):
    # 3 faixas; PUT order invertido -> 204, GET na nova ordem
    # PUT com só 2 ids -> 409 BELT_ORDER_MISMATCH

async def test_delete_unused_belt_renumbers(client, db_session):
    # A, B, C; DELETE B -> 204; GET: A pos 1, C pos 2

async def test_taekwondo_preset(client, db_session):
    # POST preset -> 201, 19 faixas; [0].name 'Branca';
    # [5] == 'Verde e azul' com stripe '#1d4ed8'; [9] 6 months;
    # [10] 'Preta 1º Dan', marks 1, 1 years; [16] 'Preta 7º Dan', 8 years;
    # [18] 'Preta 9º Dan', marks 9, min_time_amount None
    # segunda chamada -> 409 BELTS_ALREADY_EXIST
    # em 'Judô' -> 409 PRESET_NOT_AVAILABLE

async def test_belts_require_enabled_modality(client, db_session):
    # modalidade no catálogo mas não ligada -> GET 404 MODALITY_NOT_ENABLED

async def test_belts_survive_modality_toggle(client, db_session):
    # cria faixa, toggle (desliga), toggle (liga) -> GET ainda tem a faixa

async def test_other_academy_cannot_touch_belt(client, db_session):
    # segunda academia (auth_headers com email/phone diferentes):
    # PUT e DELETE na faixa da primeira -> 404 BELT_NOT_FOUND

async def test_modality_options_report_has_belts(client, db_session):
    # duas modalidades ligadas, uma com faixa -> has_belts True / False
```

Atualizar `tests/api/test_modalities_api.py`: o dicionário esperado em `/academy/modalities` ganha `'has_belts': False`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_belts_api.py tests/api/test_modalities_api.py -v`
Expected: FAIL (404 nas rotas novas / `has_belts` ausente)

- [ ] **Step 3: Implementar schemas, preset, `BeltService`, dependencies, resolvers, rotas e `has_belts`; registrar `belts_router` em `main.py` com `settings.API_V1_PREFIX`**

O preset reaproveita `create` em sequência dentro do mesmo `@transactional`. A troca de posições no `reorder` é um `update_by_id` por faixa.

- [ ] **Step 4: Rodar e ver passar**

Run: `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos .` → verde (inclui `test_openapi_contract`).

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests
git commit -m "feat: belts per academy modality with taekwondo preset"
```

---

### Task 4: Histórico de faixas da matrícula

**Files:**
- Create: `src/dojoflow/schemas/enrollment_belt.py`, `src/dojoflow/schemas/enrollment_belt_api.py`, `src/dojoflow/services/enrollment_belt.py`, `src/dojoflow/api/dependencies/enrollment_belt.py`, `src/dojoflow/api/routes/enrollment_belts.py`
- Modify: `src/dojoflow/api/dependencies/public_ids.py`, `src/dojoflow/api/routes/students.py` (passa a importar `EnrollmentIdDep` de `public_ids`), `src/dojoflow/main.py`
- Test: `tests/api/test_enrollment_belts_api.py`

**Interfaces:**
- Consumes: `BeltService.get`, `BeltRead`, `BeltApiRead` (Task 3); `evaluate_eligibility`, `eligible_on`, `local_today` (Task 1); `EnrollmentBelt`, `EnrollmentBeltRepository` (Task 2).
- Produces:
  - `schemas/enrollment_belt.py`:
    - `EnrollmentBeltPayload(belt_id: int, graduated_on: date)`
    - `BeltRecord(id: int, public_id: UUID, enrollment_id: int, graduated_on: date, belt: BeltRead)`
  - `EnrollmentBeltService(enrollment_belt_repository, belt_service, db_session)`:
    - `list_history(academy_id, enrollment_id) -> list[BeltRecord]` (mais recente primeiro: `graduated_on desc, id desc`)
    - `current_belts(academy_id, enrollment_ids: list[int]) -> dict[int, BeltRecord]` (uma consulta com `DISTINCT ON (enrollment_id)` na mesma ordem; matrícula sem registro fica fora do dict)
    - `add(academy_id, enrollment_id, data: EnrollmentBeltPayload) -> None`
    - `update(academy_id, enrollment_id, record_id, data: EnrollmentBeltPayload) -> None`
    - `delete(academy_id, enrollment_id, record_id) -> None`
    - Faixa de outra modalidade que a da matrícula → 409 `BELT_MODALITY_MISMATCH`.
  - `schemas/enrollment_belt_api.py`:
    - `EnrollmentBeltApiPayload(belt_id: UUID, graduated_on: date)` (os dois obrigatórios)
    - `BeltRecordApiRead(id: UUID, graduated_on: date, belt: BeltApiRead)`
    - `EnrollmentBeltsApiRead(current: BeltRecordApiRead | None, eligibility: Eligibility, eligible_on: date | None, history: list[BeltRecordApiRead])`. `eligibility` é calculada com `local_today()`; `eligible_on` = data em que fica apto (None sem faixa ou sem tempo mínimo).
  - `public_ids.py`: `EnrollmentIdDep` (movido de `routes/students.py`, mesmo comportamento: filtro `Enrollment.student_id`, 404 `ENROLLMENT_NOT_FOUND`); `BeltRecordIdDep` (path `record_id: UUID`, filtro `EnrollmentBelt.enrollment_id`, 404 `BELT_RECORD_NOT_FOUND`).
  - Rotas (prefixo `/students`, tag `Belts`):
    - `GET /students/{student_id}/enrollments/{enrollment_id}/belts` → `EnrollmentBeltsApiRead`
    - `POST …/belts` (corpo `EnrollmentBeltApiPayload`) → 204
    - `PUT …/belts/{record_id}` (corpo `EnrollmentBeltApiPayload`) → 204
    - `DELETE …/belts/{record_id}` → 204
    - O `belt_id` do corpo passa por `resolve_belt_id` (outra academia → 404 `BELT_NOT_FOUND`).

- [ ] **Step 1: Escrever os testes**

```python
async def test_register_graduations_and_read_history(client, db_session):
    # Taekwondo com Branca e Amarela (3 months); aluno ativo
    # POST Branca 2020-01-10, POST Amarela 2020-04-10 -> 204, 204
    # GET -> current.belt.name 'Amarela', current.graduated_on '2020-04-10',
    # eligibility 'eligible', eligible_on '2020-07-10',
    # history na ordem [Amarela, Branca]

async def test_same_date_uses_last_created(client, db_session):
    # POST Branca 2020-03-10, depois Amarela 2020-03-10 -> current 'Amarela'

async def test_no_belt_registered(client, db_session):
    # GET sem registros -> current None, eligibility 'no_belt',
    # eligible_on None, history []

async def test_belt_without_min_time(client, db_session):
    # faixa sem tempo mínimo -> eligibility 'no_requirement', eligible_on None

async def test_belt_from_other_modality_rejected(client, db_session):
    # faixa de Jiu-jitsu numa matrícula de Taekwondo -> 409 BELT_MODALITY_MISMATCH

async def test_belt_from_other_academy_not_found(client, db_session):
    # belt_id de outra academia -> 404 BELT_NOT_FOUND

async def test_graduated_on_is_required(client, db_session):
    # POST só com belt_id -> 422

async def test_edit_and_delete_record(client, db_session):
    # PUT troca faixa e data -> GET reflete; DELETE -> history []
    # DELETE de novo -> 404 BELT_RECORD_NOT_FOUND

async def test_belt_in_history_cannot_be_deleted(client, db_session):
    # DELETE /academy/belts/{id} da faixa registrada -> 409 BELT_IN_USE
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_enrollment_belts_api.py -v` → FAIL (404 nas rotas).

- [ ] **Step 3: Implementar schemas, service, dependency, resolvers e rotas; mover `EnrollmentIdDep`; registrar o router em `main.py`**

- [ ] **Step 4: Rodar e ver passar**

Run: `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos .` → verde (os testes de alunos continuam passando com o `EnrollmentIdDep` movido).

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests
git commit -m "feat: enrollment belt history with eligibility"
```

---

### Task 5: Listas de graduação (criar, listar, detalhe com candidatos, editar, excluir)

**Files:**
- Create: `src/dojoflow/schemas/graduation_list.py`, `src/dojoflow/schemas/graduation_list_api.py`, `src/dojoflow/services/graduation_list.py`, `src/dojoflow/api/dependencies/graduation_list.py`, `src/dojoflow/api/routes/graduation_lists.py`
- Modify: `src/dojoflow/api/dependencies/public_ids.py`, `src/dojoflow/main.py`
- Test: `tests/api/test_graduation_lists_api.py`

**Interfaces:**
- Consumes: `BeltService.list_by_modality`, `BeltService.next_belt` (Task 3); `EnrollmentBeltService.current_belts`, `BeltRecord` (Task 4); `evaluate_eligibility` (Task 1); `GraduationList*` models e repositórios (Task 2).
- Produces:
  - `schemas/graduation_list.py`:
    - `GraduationListCreate(name: str (strip, 1–120), modality_id: int, exam_date: date)`
    - `GraduationListUpdate(name: str | None = None, exam_date: date | None = None)` (null explícito → 422, como `EnrollmentApiUpdateRequest._reject_null`)
    - `GraduationListSummary(id, public_id, name, modality_id, modality_public_id: UUID, modality_name, modality_emoji, exam_date, created_at: datetime, entry_count: int)`
    - `GraduationCandidate(enrollment_id, enrollment_public_id: UUID, student_name, current: BeltRecord | None, eligibility: Eligibility, suggested_target: BeltRead | None)`
    - `GraduationEntry` (Task 6) e `GraduationListDetail(summary: GraduationListSummary, belts: list[BeltRead], entries: list[GraduationEntry], candidates: list[GraduationCandidate])`
  - `GraduationListService(graduation_list_repository, graduation_list_entry_repository, belt_service, enrollment_belt_service, academy_modality_repository, db_session)`:
    - `list_summaries(academy_id) -> list[GraduationListSummary]` (por `exam_date desc, id desc`)
    - `create(academy_id, data: GraduationListCreate) -> GraduationListSummary`: modalidade não oferecida → 404 `MODALITY_NOT_ENABLED`; sem faixas → 409 `MODALITY_HAS_NO_BELTS`
    - `get_detail(academy_id, list_id) -> GraduationListDetail`: candidatos = matrículas **ativas** da modalidade da lista que ainda não estão nela, por nome do aluno; `eligibility` medida na `exam_date` da lista; `suggested_target = next_belt(current)`
    - `update(academy_id, list_id, data: GraduationListUpdate) -> None`
    - `delete(academy_id, list_id) -> None` (apaga os itens e depois a lista, na mesma transação)
  - `schemas/graduation_list_api.py`:
    - `GraduationListApiCreate(name, modality_id: UUID, exam_date)`; `GraduationListApiUpdate` (mesmos campos de `GraduationListUpdate`)
    - `ModalityRefApiRead(id: UUID, name, emoji)`
    - `GraduationListSummaryApiRead(id: UUID, name, modality: ModalityRefApiRead, exam_date, created_at, entry_count)`
    - `GraduationCandidateApiRead(enrollment_id: UUID, student_name, current: BeltRecordApiRead | None, eligibility, suggested_target: BeltApiRead | None)`
    - `GraduationListDetailApiRead(summary: GraduationListSummaryApiRead, belts: list[BeltApiRead], entries: list[GraduationEntryApiRead], candidates: list[GraduationCandidateApiRead])`
  - `public_ids.py`: `GraduationListIdDep` (path `list_id: UUID`, filtro `GraduationList.academy_id`, 404 `GRADUATION_LIST_NOT_FOUND`).
  - Rotas (prefixo `/graduation-lists`, tag `Graduation lists`):
    - `GET ''` → `list[GraduationListSummaryApiRead]`
    - `POST ''` → 201 `GraduationListSummaryApiRead`
    - `GET '/{list_id}'` → `GraduationListDetailApiRead`
    - `PATCH '/{list_id}'` → 204
    - `DELETE '/{list_id}'` → 204

- [ ] **Step 1: Escrever os testes**

```python
async def test_create_and_list(client, db_session):
    # Taekwondo com faixas; POST {name 'Novembro/2026', modality_id, exam_date '2026-11-20'}
    # -> 201, modality.name 'Taekwondo', entry_count 0; GET '' -> 1 item

async def test_create_requires_belts_and_enabled_modality(client, db_session):
    # modalidade ligada sem faixas -> 409 MODALITY_HAS_NO_BELTS
    # modalidade não ligada -> 404 MODALITY_NOT_ENABLED

async def test_detail_lists_active_candidates_with_eligibility(client, db_session):
    # faixas Branca, Amarela (3 months); exame 2026-11-20
    # Ana: Branca em 2026-08-20 -> 'eligible', suggested_target 'Amarela'
    # Bruno: Branca em 2026-09-01 -> 'not_yet'
    # Caio: sem faixa -> 'no_belt', suggested_target 'Branca'
    # Duda: matrícula inativa -> não aparece
    # candidatos ordenados [Ana, Bruno, Caio]; entries []; belts com 2 itens

async def test_changing_exam_date_recalculates(client, db_session):
    # Bruno 'not_yet'; PATCH exam_date '2026-12-01' -> Bruno 'eligible'

async def test_patch_rejects_null(client, db_session):
    # PATCH {'name': None} -> 422

async def test_delete_list(client, db_session):
    # DELETE -> 204; GET detalhe -> 404 GRADUATION_LIST_NOT_FOUND

async def test_other_academy_cannot_see_list(client, db_session):
    # GET detalhe com outra academia -> 404 GRADUATION_LIST_NOT_FOUND
```

- [ ] **Step 2: Rodar e ver falhar** → `poetry run pytest tests/api/test_graduation_lists_api.py -v` (FAIL, 404).

- [ ] **Step 3: Implementar schemas, service, dependency, resolver e rotas; registrar o router**

Nesta task, `GraduationListDetail.entries` sai sempre `[]`; a Task 6 preenche. Defina `GraduationEntry` / `GraduationEntryApiRead` já com os campos da Task 6, para o contrato não mudar.

- [ ] **Step 4: Rodar e ver passar** → `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos .`

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests
git commit -m "feat: graduation lists with eligible candidates"
```

---

### Task 6: Itens da lista (adicionar, faixa pretendida, retrato, remover)

**Files:**
- Modify: `src/dojoflow/services/graduation_list.py`, `src/dojoflow/schemas/graduation_list.py`, `src/dojoflow/schemas/graduation_list_api.py`, `src/dojoflow/api/routes/graduation_lists.py`, `src/dojoflow/api/dependencies/public_ids.py`
- Test: `tests/api/test_graduation_lists_api.py` (mesmo arquivo)

**Interfaces:**
- Consumes: tudo da Task 5; `resolve_belt_id` (Task 3); `EnrollmentBeltService.current_belts` (Task 4).
- Produces:
  - `GraduationEntry(id, public_id, enrollment_id, enrollment_public_id: UUID, student_name, snapshot_belt: BeltRead | None, snapshot_graduated_on: date | None, eligibility: Eligibility, target_belt: BeltRead)`. A `eligibility` vem do **retrato** (faixa + data guardadas) contra a `exam_date` atual da lista, usando o tempo mínimo atual da faixa do retrato.
  - `GraduationEntryApiRead(id: UUID, enrollment_id: UUID, student_name, snapshot_belt: BeltApiRead | None, snapshot_graduated_on, eligibility, target_belt: BeltApiRead)`
  - `GraduationListService`:
    - `add_entry(academy_id, list_id, enrollment_id: int, target_belt_id: int | None) -> None`: grava o retrato a partir de `current_belts`; `target_belt_id` None → `next_belt(current)`; sem próxima (aluno na última faixa) → 409 `TARGET_BELT_REQUIRED`; matrícula de outra modalidade ou inativa → 409 `ENROLLMENT_NOT_CANDIDATE`; já está na lista → 409 `ALREADY_IN_LIST`; faixa pretendida de outra modalidade → 409 `BELT_MODALITY_MISMATCH`. **Nunca** recusa aluno por não estar apto.
    - `update_entry(academy_id, list_id, entry_id, target_belt_id: int) -> None`
    - `remove_entry(academy_id, list_id, entry_id) -> None`
    - `get_detail` passa a preencher `entries` (por nome do aluno); `entry_count` em `list_summaries` conta os itens.
  - API: `GraduationEntryApiCreate(enrollment_id: UUID, target_belt_id: UUID | None = None)`, `GraduationEntryApiUpdate(target_belt_id: UUID)`.
  - `public_ids.py`: `GraduationEntryIdDep` (path `entry_id: UUID`, filtro `GraduationListEntry.graduation_list_id`, 404 `GRADUATION_ENTRY_NOT_FOUND`). O `enrollment_id` do corpo é resolvido com filtro `Enrollment.academy_id` (404 `ENROLLMENT_NOT_FOUND`).
  - Rotas:
    - `POST /graduation-lists/{list_id}/entries` → 204
    - `PATCH /graduation-lists/{list_id}/entries/{entry_id}` → 204
    - `DELETE /graduation-lists/{list_id}/entries/{entry_id}` → 204

- [ ] **Step 1: Escrever os testes**

```python
async def test_add_entry_defaults_to_next_belt(client, db_session):
    # Ana (Branca em 2026-08-20); POST entries {enrollment_id} -> 204
    # detalhe: entries[0].target_belt.name 'Amarela', snapshot_belt 'Branca',
    # snapshot_graduated_on '2026-08-20', eligibility 'eligible';
    # Ana sumiu de candidates; summary entry_count 1

async def test_add_entry_can_skip_belts(client, db_session):
    # target_belt_id = Laranja (pulando Amarela) -> target 'Laranja'

async def test_not_eligible_student_can_be_added(client, db_session):
    # Bruno 'not_yet' -> 204, entry eligibility 'not_yet'

async def test_entry_keeps_snapshot_after_new_graduation(client, db_session):
    # adiciona Ana; registra Amarela para Ana em 2026-10-25
    # detalhe: entry ainda mostra snapshot 'Branca' / '2026-08-20'

async def test_duplicate_entry_rejected(client, db_session):
    # segundo POST com a mesma matrícula -> 409 ALREADY_IN_LIST

async def test_non_candidate_enrollment_rejected(client, db_session):
    # matrícula de Jiu-jitsu numa lista de Taekwondo -> 409 ENROLLMENT_NOT_CANDIDATE
    # matrícula inativa de Taekwondo -> 409 ENROLLMENT_NOT_CANDIDATE

async def test_target_belt_from_other_modality_rejected(client, db_session):
    # target_belt_id de Jiu-jitsu -> 409 BELT_MODALITY_MISMATCH

async def test_last_belt_requires_explicit_target(client, db_session):
    # aluno na última faixa, sem target -> 409 TARGET_BELT_REQUIRED

async def test_update_and_remove_entry(client, db_session):
    # PATCH target -> reflete; DELETE -> 204, aluno volta a candidates
    # DELETE de novo -> 404 GRADUATION_ENTRY_NOT_FOUND

async def test_target_belt_in_list_cannot_be_deleted(client, db_session):
    # DELETE /academy/belts/{target} usado só na lista -> 409 BELT_IN_USE

async def test_delete_list_with_entries(client, db_session):
    # lista com 2 itens -> DELETE 204
```

- [ ] **Step 2: Rodar e ver falhar** → `poetry run pytest tests/api/test_graduation_lists_api.py -v`

- [ ] **Step 3: Implementar `add_entry`, `update_entry`, `remove_entry`, os itens no detalhe e `entry_count`; resolver e rotas**

- [ ] **Step 4: Rodar e ver passar** → `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos .`

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests
git commit -m "feat: graduation list entries with belt snapshot"
```

---

### Task 7: Faixa atual no cadastro do aluno e na nova matrícula (tela 2a)

**Files:**
- Modify: `src/dojoflow/schemas/student_api.py`, `src/dojoflow/api/routes/students.py`, `src/dojoflow/services/enrollment_belt.py`
- Test: `tests/api/test_students_belt.py`

**Interfaces:**
- Consumes: `EnrollmentBeltService`, `EnrollmentBeltPayload`, `EnrollmentBeltApiPayload` (Task 4); `resolve_belt_id` (Task 3); `unit_of_work` (`database/transaction.py`).
- Produces:
  - `EnrollmentApiPayload.current_belt: EnrollmentBeltApiPayload | None = None` (vale para `POST /students` e `POST /students/{id}/enrollments`). `_to_internal_enrollment` passa a excluir `current_belt` do `model_dump`, porque `StudentEnrollmentPayload` não muda: o bot não é afetado.
  - `EnrollmentBeltService.add_for_modality(academy_id: int, student_id: int, modality_id: int, data: EnrollmentBeltPayload) -> None` (acha a matrícula pelo par aluno × modalidade, que é único, e chama `add`).
  - Nas duas rotas, quando `current_belt` vem preenchido: resolver o `belt_id` **antes** de gravar e envolver "criar aluno/matrícula" + `add_for_modality` num `async with unit_of_work(db_session_dep):`. Qualquer erro desfaz tudo. Sem `current_belt`, nada muda.

- [ ] **Step 1: Escrever os testes**

```python
async def test_create_student_with_current_belt(client, db_session):
    # Taekwondo com Branca e Amarela; POST /students com
    # enrollment.current_belt = {belt_id: Amarela, graduated_on: '2025-03-01'} -> 201
    # GET .../enrollments/{eid}/belts -> current 'Amarela', '2025-03-01'

async def test_create_student_without_belt_still_works(client, db_session):
    # sem current_belt -> 201, history []

async def test_invalid_belt_creates_nothing(client, db_session):
    # current_belt de Jiu-jitsu numa matrícula de Taekwondo -> 409 BELT_MODALITY_MISMATCH
    # GET /students -> total 0

async def test_unknown_belt_is_404_and_creates_nothing(client, db_session):
    # belt_id = uuid4() -> 404 BELT_NOT_FOUND; GET /students -> total 0

async def test_new_enrollment_with_current_belt(client, db_session):
    # aluno de Jiu-jitsu; POST /students/{id}/enrollments (Taekwondo) com
    # current_belt Branca hoje -> 204; GET .../belts -> current 'Branca'
```

- [ ] **Step 2: Rodar e ver falhar** → `poetry run pytest tests/api/test_students_belt.py -v` (FAIL: campo ignorado, sem histórico)

- [ ] **Step 3: Implementar o campo, `add_for_modality` e a orquestração nas duas rotas**

- [ ] **Step 4: Rodar e ver passar** → `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos .` (os testes de alunos e do bot continuam verdes)

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests
git commit -m "feat: optional current belt when enrolling a student"
```

---

### Task 8: Lançar faixas dos alunos antigos em lote (tela 2b)

**Files:**
- Modify: `src/dojoflow/services/enrollment_belt.py`, `src/dojoflow/schemas/enrollment_belt.py`, `src/dojoflow/schemas/enrollment_belt_api.py`, `src/dojoflow/api/routes/belts.py`, `src/dojoflow/schemas/modality.py`, `src/dojoflow/schemas/modality_api.py`, `src/dojoflow/services/modality.py`
- Test: `tests/api/test_belts_bulk_api.py`

**Interfaces:**
- Consumes: `EnabledModalityIdDep`, `resolve_belt_id` (Task 3); `EnrollmentBeltService.add` (Task 4).
- Produces:
  - `PendingBeltEnrollment(enrollment_id: int, enrollment_public_id: UUID, student_public_id: UUID, student_name: str)`
  - `EnrollmentBeltService.list_pending(academy_id, modality_id) -> list[PendingBeltEnrollment]`: matrículas **ativas** da modalidade sem nenhum registro, por nome do aluno.
  - `EnrollmentBeltService.bulk_add(academy_id, modality_id, items: list[tuple[int, EnrollmentBeltPayload]]) -> int` (`@transactional`, tudo ou nada; devolve quantos gravou). Matrícula de outra modalidade → 409 `ENROLLMENT_MODALITY_MISMATCH`; faixa de outra modalidade → 409 `BELT_MODALITY_MISMATCH`; a mesma matrícula repetida no lote → 409 `DUPLICATE_ENROLLMENT_IN_BATCH`.
  - API: `PendingBeltEnrollmentApiRead(enrollment_id: UUID, student_id: UUID, student_name)`; `BulkBeltItemApi(enrollment_id: UUID, belt_id: UUID, graduated_on: date)`; `BulkBeltRequest(items: list[BulkBeltItemApi] = Field(min_length=1, max_length=200))`; `BulkBeltResultApiRead(saved: int)`.
  - Rotas (tag `Belts`):
    - `GET /academy/modalities/{modality_id}/belts/pending-enrollments` → `list[PendingBeltEnrollmentApiRead]`
    - `POST /academy/modalities/{modality_id}/belts/bulk` → 200 `BulkBeltResultApiRead`. Os UUIDs dos itens são resolvidos com filtro de academia: 404 `ENROLLMENT_NOT_FOUND` / `BELT_NOT_FOUND`.
  - `ModalityOptionRead.pending_belt_count: int = 0` e `ModalityOptionApiRead.pending_belt_count: int` (alimenta o aviso "N alunos sem faixa registrada"). Atualizar o dicionário esperado em `tests/api/test_modalities_api.py` com `'pending_belt_count': 0`.

- [ ] **Step 1: Escrever os testes**

```python
async def test_pending_lists_active_enrollments_without_belt(client, db_session):
    # Taekwondo: Ana (sem faixa), Bruno (com Branca), Duda (inativa, sem faixa)
    # GET pending-enrollments -> só Ana
    # GET /academy/modalities -> Taekwondo pending_belt_count 1

async def test_bulk_saves_all(client, db_session):
    # Ana e Caio sem faixa; POST bulk com os dois -> 200 {'saved': 2}
    # pending-enrollments -> []; GET .../belts da Ana -> current conforme enviado

async def test_bulk_is_all_or_nothing(client, db_session):
    # item 1 válido, item 2 com faixa de Jiu-jitsu -> 409 BELT_MODALITY_MISMATCH
    # pending-enrollments ainda tem os dois

async def test_bulk_rejects_enrollment_of_other_modality(client, db_session):
    # matrícula de Jiu-jitsu no lote de Taekwondo -> 409 ENROLLMENT_MODALITY_MISMATCH

async def test_bulk_rejects_duplicate_enrollment(client, db_session):
    # a mesma matrícula duas vezes -> 409 DUPLICATE_ENROLLMENT_IN_BATCH

async def test_bulk_empty_is_422(client, db_session):
    # items [] -> 422
```

- [ ] **Step 2: Rodar e ver falhar** → `poetry run pytest tests/api/test_belts_bulk_api.py tests/api/test_modalities_api.py -v`

- [ ] **Step 3: Implementar `list_pending`, `bulk_add`, schemas, rotas e `pending_belt_count`**

- [ ] **Step 4: Verificação completa**

Run: `poetry run pytest -q && poetry run ruff check . && poetry run ruff format --check . && poetry run typos . && poetry run alembic check`
Expected: tudo verde; `No new upgrade operations detected.`

Run: `poetry run task run` e abrir http://localhost:8000/docs → as tags `Belts` e `Graduation lists` aparecem com respostas tipadas.

- [ ] **Step 5: Commit**

```bash
git add src/dojoflow tests
git commit -m "feat: bulk belt registration for existing students"
```

- [ ] **Step 6: Atualizar o Obsidian**

Em `DojoFlow.md` (bloco "Próxima sessão") e na nota da spec: backend das faixas concluído; próximo passo é o plano do frontend (componente do desenho → tela de Faixas → Lançar faixas → Graduações → ficha e cadastro do aluno com as Fases 7–8).
