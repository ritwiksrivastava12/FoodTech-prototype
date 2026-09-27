# FoodMate — Stop wondering what to eat.

FoodMate is an intelligent personal food decision platform built as a functional prototype.
Core loop: **DECIDE → CHECK → COMPARE → COOK/BUY/ORDER → TRACK**

## Quick start (demo, no external keys required)

### Backend (Python + FastAPI)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend health: http://localhost:8000/api/health
API docs: http://localhost:8000/docs

Default demo user (seeded):
- email: `demo@foodmate.app`
- password: `demo1234`

### Frontend (React + Vite)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend: http://localhost:5173 (proxies `/api` → `http://localhost:8000`)

## Demo journey (end-to-end USP)

1. Login as demo user (tired, spicy/comfort mood).
2. Home greets you, shows meal context (dinner), mood chips, AI input.
3. Type: *"tired, spicy, high protein, under ₹100, 20 min, I have rice eggs onions, no paneer today"*
4. FoodMate recommends **Egg Fried Rice** — 15 min, ~₹65 cook cost vs ₹149–189 order, all ingredients available, no paneer repetition, fits budget.
5. Open meal → **Kitchen Check** (quantities compared) → **Cook vs Order** → **Cook Mode** (step-by-step, servings scalable 2→5) → **Complete & Track** (history + inventory deducted + nutrition logged).
6. Planner / Kitchen / Shop / Nutrition all update consistently.

## Architecture

```
frontend/ (React, presentation only)
  src/pages, components, services, store
backend/ (FastAPI, all business logic)
  app/core (config, security, database)
  app/models (SQLAlchemy)
  app/schemas (Pydantic)
  app/services (recommendation, inventory, nutrition, cost, shopping, ai_orchestrator, nlp, vision_mock)
  app/api (routes)
  app/data (seed_data)
  app/integrations (grocery/delivery/llm/speech/vision adapters — demo providers swappable)
```

- Frontend never touches DB or secrets. All LLM keys stay in backend env.
- `AI_PROVIDER` env: `rule` (default, deterministic, no key), `openai`, `anthropic`, `gemini`, `local`. Rule mode already gives full NL understanding; setting a key upgrades reasoning without changing the API contract.
- DB: SQLite by default (`foodmate.db`), `DATABASE_URL` supports PostgreSQL/MySQL. Mongo adapter interface documented for conversation docs (SQLite used in prototype for portability).
- Grocery/delivery integrations are **adapter interfaces** with transparent `demo` providers. UI always labels demo data as "Demo prices".

## Security

- PBKDF2 password hashing, JWT (HS256, 7-day expiry), per-user data scoping on every route.
- Pydantic validation everywhere, allergy/diet hard filters (never recommend violations).
- No secrets in frontend. CORS configurable.

## Testing business logic

```bash
cd backend
pytest -q
```

Covers: serving scaling, inventory check, shopping-list generation, repetition detection, cost calc, nutrition aggregation, dietary filtering, recommendation filtering.

## Docs

- `docs/API.md` — endpoint reference
- `docs/ARCHITECTURE.md` — data model, AI orchestration, adapters
- `docs/DEMO_SCRIPT.md` — investor/mentor walkthrough
