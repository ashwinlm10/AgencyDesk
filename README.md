# AgencyDesk

Multi-tenant client & project management platform for agency-client work.
Stack: **React (Vite) + FastAPI (Python) + PostgreSQL**.

See `DESIGN.md` for schema/access-control write-up.

## Prerequisites

- Python 3.11+
- Node 18+
- PostgreSQL running locally (or any reachable instance)

## 1. Database

```bash
createdb agencydesk
```

## 2. Backend

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/agencydesk"   # adjust to your setup
export JWT_SECRET="something-random"

alembic upgrade head      # applies migrations
python seed.py             # seeds 2 agencies, staff, a client, mixed-visibility tasks

uvicorn app.main:app --reload --port 8000
```

API is now at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Running tests (proves tenant isolation & the 5 edge cases)

```bash
createdb agencydesk_test
cd backend
pytest tests/ -v
```

All 13 tests should pass — they cover cross-tenant access blocking, internal
content never reaching clients (list view, single-item lookup, and comments),
clients being blocked from mutating tasks, invite-resend not duplicating,
double-accepting an invite being idempotent, mid-task member removal
unassigning tasks, and the same email holding different roles across two
agencies.

## 3. Frontend

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

Open `http://localhost:5173`.

## Seeded accounts (password for all: `password123`)

| Email | Agency | Role |
|---|---|---|
| admin@pixelpine.com | Pixel & Pine | agency_admin |
| member@pixelpine.com | Pixel & Pine | agency_member |
| admin@mapledigital.com | Maple Digital | agency_admin |
| shared@client.com | **both** agencies | client_user in each, different client company per agency — demonstrates the "one person, two agencies" identity model. Log in once, then pick which agency to enter. |

## Project layout

```
backend/
  app/
    models.py       # schema — see composite FKs for tenant isolation
    deps.py          # AuthContext + role guards, used by every route
    routers/         # one file per resource
  alembic/versions/  # migrations
  tests/             # isolation + edge-case proof suite
  seed.py
frontend/
  src/pages/         # Login, Projects, ProjectBoard, TaskDetail
  src/context/        # auth/session state
DESIGN.md
```
**Demo video:** https://drive.google.com/file/d/1IU6_Eb-1-D4-zqB93zYlw3n7983NClS4/view?usp=sharing

Multi-tenant client & project management platform for agency-client work.
Stack: **React (Vite) + FastAPI (Python) + PostgreSQL**.
...
