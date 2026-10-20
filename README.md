# DojoFlow

Gerenciador de mensalidades para academias de artes marciais. O mestre usa o
site (canal principal) e o bot do Telegram (atalho para cadastros).

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL (`src/dojoflow`)
- **Frontend:** React + Vite + TypeScript + Tailwind/shadcn (`frontend/`)

## Rodando localmente

Backend (Python 3.13 + Poetry):

```bash
cp .env.example .env
docker compose up -d postgres   # Postgres na porta 5434
poetry install
poetry run alembic upgrade head
poetry run task run             # API em http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173 (repassa /api para a API)
```

## Qualidade

```bash
poetry run task lint && poetry run task typos && poetry run task test
cd frontend && npx tsc -b && npm run lint
```

Depois de mudar um schema da API, regere os tipos do frontend com
`npm run gen:api` (com a API rodando).
