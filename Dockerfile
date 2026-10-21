# Imagens de produção. Dois alvos:
#   api — FastAPI (uvicorn)
#   web — Caddy servindo o site já compilado e repassando /api para a api

# --- Site (React + Vite) ---
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Dependências Python (só as de produção) ---
FROM python:3.13-slim AS deps
ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
RUN pip install --no-cache-dir poetry==2.1.4
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

# --- API ---
FROM python:3.13-slim AS api
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY --from=deps /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "dojoflow.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]

# --- Web (Caddy + site) ---
FROM caddy:2.10-alpine AS web
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /frontend/dist /srv
