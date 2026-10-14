# Site V1 — Plano B: Frontend (roteiro de estudo)

- **Data:** 2026-10-14
- **Spec:** `docs/superpowers/specs/2026-10-13-web-frontend-v1-design.md` (seções 3, 5, 6, 7.2)
- **Backend:** pronto na `main` (Plano A, PR #1)
- **Execução:** Thiago escreve todo o código; Claude é o professor. Cada fase é dividida em pílulas — um conceito e um trecho por vez, com explicação e comparação com Python. Claude não edita arquivos em `frontend/`; revisa o que Thiago escreveu quando pedido.

## Regras da execução

- Uma pílula = um conceito + um bloco de código explicado parte por parte. Depois, parar e esperar.
- Toda ideia nova de React/TypeScript vem comparada com o equivalente em Python (ou "não existe equivalente").
- Antes de qualquer comando de instalação, conferir a versão atual na documentação oficial.
- Cada fase termina com algo rodando no navegador e um commit do Thiago.
- Fatias verticais: cada tela fecha ponta a ponta (dados + visual) antes da próxima.

## Pré-requisitos (uma vez)

- `.env` do backend com `DATABASE_URL` na porta **5434**; `docker compose up -d postgres`; `poetry run alembic upgrade head`; `poetry run task run` (API em `localhost:8000`).

## Fases

| Fase | Entrega | Conceitos novos |
|---|---|---|
| 0 · Projeto | `frontend/` criado com Vite 8 + React + TS, rodando em `localhost:5173`; proxy `/api` → `localhost:8000` | npm/package.json vs Poetry/pyproject; dev server; JSX; componente = função |
| 1 · Visual base | Tailwind v4 + shadcn/ui + Lucide; tema lavanda/índigo, fonte Outfit, bordas grandes | Utility classes; CSS variables como tokens; alias `@/` |
| 2 · Esqueleto | React Router: `/login`, `/app` com layout (sidebar no desktop, barra inferior no celular), páginas vazias | Rotas aninhadas, `<Outlet>`, props, `children` |
| 3 · Contrato da API | `npm run gen:api` gera `src/api/schema.d.ts` do `/openapi.json`; cliente `openapi-fetch` | Tipos TS vs Pydantic; tipos gerados |
| 4 · Sessão | Tela de login (React Hook Form + Zod); `AuthContext` com access token em memória; refresh ao abrir o site; 401 → um único refresh; guarda de rota; logout | `useState`, `useEffect`, Context, Promise compartilhada |
| 5 · Conta | `/cadastro` e `/definir-acesso?token=` | `useSearchParams`, `useNavigate` |
| 6 · Modalidades | `/app/modalidades`: catálogo com ativar/desativar | Primeiro hook de dados (`useModalities`) com `useEffect` + `AbortController`; `refetch` |
| 7 · Lista de alunos | `/app/alunos`: busca com espera de 300 ms, filtros e página na URL, paginação, mestre-detalhe | Hook `useStudents`; debounce; estado na URL |
| 8 · Ficha | `/app/alunos/:id`: abas Matrículas, Dados, Endereço, Responsáveis, com edição | `useParams`; mutações (`mutate`, `isPending`); erros 422 nos campos |
| 9 · Novo aluno | `/app/alunos/novo`: 4 etapas, CEP automático | Formulário em etapas; estado entre etapas |
| 10 · Dashboard | `/app`: cards, alunos por modalidade, recentes, pendências | Composição de componentes; estados vazios |
| 11 · Configurações | Trocar senha (senha atual), conectar Telegram | Revisão de tudo |
| 12 · CI | Job de frontend: `tsc --noEmit`, ESLint, tipos do OpenAPI sincronizados | — |

## Contrato do backend usado pelo frontend (referência)

- Login/cadastro/refresh/definir acesso respondem `{access_token, token_type, master}`; o refresh vai no cookie `dojoflow_refresh` (`Path=/api/v1/auth`).
- `master` = `{id, name, email, telegram_linked, academy: {id, name, status}}` (ids são UUID).
- Erros: `{detail, code}`; 422 no formato padrão do FastAPI.
- 401 em rotas de `/auth/*` não dispara refresh (é falha de login/token de setup).
- Senha atual errada ao trocar senha → 403 `CURRENT_PASSWORD_INVALID`.
