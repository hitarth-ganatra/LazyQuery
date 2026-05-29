# LazyQuery

LazyQuery is an AI-powered full-stack platform for querying relational datasets in natural language and receiving tabular + visual analytics outputs.

## MVP Scope

- **Supported database**: PostgreSQL (public schema introspection)
- **NL-to-SQL complexity**: single-statement read-only analytics queries (`SELECT`, aggregations, joins, filters)
- **Chart outputs**: table, metric, bar, line, scatter (auto recommendation from result shape)
- **Auth**: no user auth in MVP (service-level access)
- **Deployment target**: Docker Compose (frontend + backend + PostgreSQL)

## Measurable Acceptance Criteria

1. Backend exposes `POST /api/query` and `GET /api/health`.
2. Natural-language prompt is transformed into SQL using Groq API when configured; deterministic fallback exists when unavailable.
3. SQL guardrails reject non-read-only statements and enforce pagination/limits.
4. Backend can introspect PostgreSQL public schema and execute read-only queries with timeout.
5. Response payload includes generated SQL, rows, columns, intent, warnings, and chart recommendation.
6. Frontend provides NL input, execution status, SQL preview, history, tabular results, and chart rendering.
7. Benchmark script reports SQL exact-match accuracy from fixture cases.

## Repository Structure

- `backend/` – FastAPI API, NL-to-SQL pipeline, SQL safety, analytics, tests
- `frontend/` – React + TypeScript query workspace
- `evaluation/` – benchmark fixture and scoring script
- `docker-compose.yml` – local orchestration for postgres/backend/frontend

## Environment Setup

### Backend

1. `cd /tmp/workspace/hitarth-ganatra/LazyQuery/backend`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and update values (`GROQ_API_KEY`, `DATABASE_URL`)
5. `uvicorn app.main:app --reload --port 8000`

### Frontend

1. `cd /tmp/workspace/hitarth-ganatra/LazyQuery/frontend`
2. `npm install`
3. `cp /tmp/workspace/hitarth-ganatra/LazyQuery/.env.example .env`
4. `npm run dev`

## Docker Run

From `/tmp/workspace/hitarth-ganatra/LazyQuery`:

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## API Contract

### `POST /api/query`

Request:

```json
{
  "prompt": "Show top 5 customers by revenue",
  "limit": 100,
  "offset": 0
}
```

Response includes:

- `intent`
- `sql`
- `columns`
- `rows`
- `row_count`
- `chart` (`chart_type`, `x_key`, `y_keys`, `title`)
- `warnings`

## Validation Commands

### Backend

```bash
cd /tmp/workspace/hitarth-ganatra/LazyQuery/backend
ruff check .
pytest
```

### Frontend

```bash
cd /tmp/workspace/hitarth-ganatra/LazyQuery/frontend
npm run lint
npm run build
```

### Benchmark

```bash
cd /tmp/workspace/hitarth-ganatra/LazyQuery
python evaluation/run_benchmark.py
```
