# DojoFlow

Gerenciador de mensalidades para academias de artes marciais. O mestre usa o
site (canal principal) e o bot do Telegram (atalho para cadastros).

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL (`src/dojoflow`)
- **Frontend:** React + Vite + TypeScript + Tailwind/shadcn (`frontend/`)

## Rodando localmente

Em desenvolvimento são três processos:

```
navegador → Vite :5173 ──/api──→ FastAPI :8000 ──→ Postgres :5434 (Docker)
```

### Primeira vez

```bash
cp .env.example .env            # DATABASE_URL já aponta para a porta 5434
poetry install                  # dependências do backend (Python 3.13)
cd frontend && npm install      # dependências do frontend
```

### Dia a dia (dois terminais, na raiz do projeto)

```bash
# Terminal 1: banco + API
docker compose up -d postgres      # liga o Postgres em segundo plano
poetry run alembic upgrade head    # aplica migrações pendentes (rode após cada git pull)
poetry run task run                # API em http://localhost:8000 (recarrega ao salvar)

# Terminal 2: frontend
cd frontend
npm run dev                        # site em http://localhost:5173
```

- Os dados do banco ficam no volume `dojoflow_postgres_data`; parar o container
  não apaga nada.
- O Vite repassa toda chamada `/api/...` para a API (ver `frontend/vite.config.ts`),
  então o navegador fala só com a porta 5173.

### Conferir

- http://localhost:8000/docs: Swagger da API
- http://localhost:5173: o site

### Desligar

`Ctrl+C` nos dois terminais e, para parar o banco, `docker compose stop`.

### Só quando algo mudar

- `poetry.lock` mudou → `poetry install`
- `frontend/package-lock.json` mudou → `npm install` (dentro de `frontend/`)
- Schema da API mudou → `npm run gen:api` (dentro de `frontend/`, com a API rodando)

## Qualidade

```bash
poetry run task lint && poetry run task typos && poetry run task test
cd frontend && npx tsc -b && npm run lint
```
