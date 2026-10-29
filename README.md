# Lumen

Multi-tenant project management for **organizations → projects → work items**, with JWT auth and role-based access control.

## Stack

| Layer | Tech |
| --- | --- |
| Web | React 19, Vite, JavaScript, Tailwind CSS v4, shadcn-style UI |
| API | FastAPI, SQLAlchemy, Alembic, JWT |
| Data | PostgreSQL |
| Run | Docker Compose (Postgres + optional full stack) |

## Domain model

- **Organization** — tenant workspace members belong to  
- **Project** — scoped board inside an organization (key prefixes work item numbers)  
- **Work item** — tracked work with status, priority, description, comments  
- **Status** — workflow steps (backlog / started / done categories)  
- **Roles** — org and project RBAC (`org_owner`, `org_admin`, `project_admin`, …)

## Secrets

Do **not** commit real env files. Copy examples and set your own values:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Required for Compose / API:

- `POSTGRES_PASSWORD`
- `JWT_SECRET`

`deploy/` is local-only (gitignored) and not part of the published repo.

## Quick start

### 1. Postgres

```bash
cp .env.example .env   # set POSTGRES_PASSWORD and JWT_SECRET
docker compose up -d postgres
```

Postgres is exposed on **localhost:5433**.

### 2. API

```bash
cd backend
cp .env.example .env   # DATABASE_URL should use the same password as Compose
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8100
```

- API: http://127.0.0.1:8100  
- OpenAPI: http://127.0.0.1:8100/docs  

### 3. Web

```bash
cd frontend
cp .env.example .env   # VITE_API_URL=http://127.0.0.1:8100
npm install
npm run dev
```

- App: http://localhost:5173  

### 4. Demo data (optional)

```bash
cd backend
source .venv/bin/activate
python -m scripts.seed_demo
```

Optional: `SEED_PASSWORD=...` sets the shared password for all seeded users.  
Seeded emails include `owner@example.com` and `admin@example.com`.

## Full stack with Compose

With a root `.env` filled in:

```bash
docker compose up --build
```

- Web: http://localhost:5173  
- API: http://localhost:8100  

## Features

- Register / login (JWT)
- Organizations and membership
- Projects with default statuses and labels
- Work items, comments, activity
- Org dashboard and admin analytics
- Work-item list with detail pane (status, priority, description, comments)

## Project layout

```
backend/          FastAPI app, Alembic migrations, seed script
frontend/         Vite React app
docker-compose.yml
.env.example      Compose / shared env template
```

## License

Private unless you add a license file.
