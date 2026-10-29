# KubeFlow PMS

Multi-tenant project management system with org/project RBAC.

- **Frontend:** React + Vite + JavaScript + Tailwind + shadcn/ui
- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL
- **Deploy:** Docker Compose + Kubernetes manifests

## Secrets

Copy examples — never commit real `.env` or `secrets.yaml` files:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit JWT_SECRET / POSTGRES_PASSWORD to strong values
```

## Quick start (local)

```bash
# Postgres
docker compose up -d postgres

# API
cd backend
cp .env.example .env   # if needed
source .venv/bin/activate   # or: uv venv && uv pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8100

# Web
cd frontend
cp .env.example .env   # if needed
npm install
npm run dev
```

- Web: http://localhost:5173  
- API: http://127.0.0.1:8100/docs  
- Seed fake data: `cd backend && source .venv/bin/activate && python -m scripts.seed_demo`  
  Optional: `SEED_PASSWORD=...` to set the shared password for seeded demo users.

## Features

- Auth (register/login JWT)
- Organizations, invites
- Projects with default workflow statuses & labels
- Work items, comments, activity log
- Org/project RBAC (`org_owner`, `org_admin`, `project_admin`, …)
- Org dashboard (progress + my open tasks)
- Issue stream UI with detail pane

## Kubernetes

```bash
kubectl apply -f deploy/k8s/namespace.yaml
cp deploy/k8s/secrets.example.yaml deploy/k8s/secrets.yaml
# edit secrets.yaml with real passwords / JWT_SECRET
kubectl apply -f deploy/k8s/secrets.yaml
kubectl apply -f deploy/k8s/
# Build/load images pms-api:latest and pms-web:latest into your cluster first
```
