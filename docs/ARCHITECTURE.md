# FoodMate architecture

## Product loop

`DECIDE → CHECK → COMPARE → COOK/BUY/ORDER → TRACK` — every screen maps to one stage,
and state (inventory, history, goals) flows forward through the loop.

## Stack boundaries

- **Frontend** (`frontend/src`): React + Vite. Presentation, client state, Web Speech API
  (voice), image picker, API calls only. No DB access, no secrets, no business rules.
- **Backend** (`backend/app`): FastAPI. All business logic, validation, auth, AI orchestration.
- **Data**: SQLite file by default (`foodmate.db`); `DATABASE_URL` switches to
  PostgreSQL/MySQL without code changes (SQLAlchemy). Conversations/moods are clean
  tables today; the schema is shaped so they can move to MongoDB documents later
  without changing the API contract.

## Backend layout

```
app/core        config (env), security (PBKDF2+JWT), database (engine/session)
app/models      SQLAlchemy entities (users, profiles, meals, favorites, inventory,
                plans, history, shopping, moods, conversations, nutrition)
app/schemas     Pydantic request validation
app/services
  nlp.py            deterministic NL intent parsing (moods, negatives, have-foods,
                    budget, time, servings, meal-type, cook/order signals)
  food_math.py      units (g/kg/ml/L/tsp/tbsp/cup/pcs + pcs↔g produce estimates),
                    serving scaling, availability, shopping deltas, diet/allergy/
                    dislike filters, repetition, nutrition aggregation, expiry
  recommender.py    hard safety filters → scoring → diversification → explanations.
                    `score_meal` is the seam a future ML model replaces.
  ai_orchestrator.py retrieve context → deterministic math → candidates → LLM
                    (optional) → explainable reply. `llm_complete` supports
                    openai/anthropic/gemini via env, `rule` fallback by default.
app/integrations/adapters.py  GroceryAdapter / DeliveryAdapter / LLMAdapter —
                    demo providers today, real partners later. UI always labels demo.
app/api           auth, meals, ai, kitchen_planner, shop_nutrition
app/data          seed_data.py (18 meals, demo kitchen, grocery/restaurant demos)
```

## AI orchestration (not “LLM does everything”)

1. Parse intent deterministically (`nlp`).
2. Load structured context: profile, inventory map, history, favorites.
3. Compute availability + expiry bonuses deterministically.
4. Score candidates (`recommender`) with hard diet/allergy/repetition filters.
5. Optionally call an LLM for phrasing/reasoning only (`AI_PROVIDER` env).
   Nutrition numbers and prices always come from structured data, never the LLM.
6. Respond with picks + reasons + next actions.

## Key decisions

- **Passwords**: PBKDF2-HMAC-SHA256 (stdlib, no native deps), JWT HS256, per-user scoping on every query.
- **Units**: base-unit math (g/ml/pcs) with produce pcs↔g estimates (onion ≈100g…); pantry micro-spices tolerated, never silently ignored.
- **Repetition**: configurable (`allow | no-same-day | avoid-2/3-days`), matches exact dish or main ingredient.
- **Inventory integrity**: cooking deducts only on explicit completion with `deduct_inventory` flag; grocery sync only moves checked items; both reported back to the user.
- **Honesty**: grocery/delivery/vision responses carry `demo` flags and disclaimers; buttons explain pending integrations instead of faking orders.
