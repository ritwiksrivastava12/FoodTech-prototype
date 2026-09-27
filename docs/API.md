# FoodMate API reference

Base URL (dev): `http://localhost:8000`. Interactive docs: `/docs`.
Auth: `Authorization: Bearer <jwt>` for all `/api/*` except register/login/health.

## Auth & profile

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | `{name, email, password, phone?}` | Seeds kitchen inventory |
| POST | `/api/auth/login` | `{email, password}` | Returns `{token, user}` |
| GET | `/api/auth/me` | — | User + profile |
| GET/PUT | `/api/profile` | profile fields | diet, allergies, disliked, cuisines, ability, equipment, budgets, goals, repetition_rule |

## Decide

| Method | Path | Notes |
|---|---|---|
| POST | `/api/recommendations` | `{mood, intent_text, meal_type?, budget?, max_time?, servings?, quick_only?, allow_repeat?, limit?}` → scored meals with `reasons`, `availability`, `nutrition_scaled`, `cost_cook_scaled`, `missing`, `sections` |
| GET | `/api/meals/search?q=` | NL-aware search; returns `{intent, results}` |
| GET | `/api/meals?category=` | Discovery listing with availability summary |
| GET | `/api/meals/{id}?servings=` | Full detail, scaled |
| POST | `/api/meals` | Create meal (structured fields) |
| GET/POST/DELETE | `/api/favorites…` | Go-To meals; custom meals via `{name, …}` without `meal_id` |
| GET/POST | `/api/moods` | Mood taxonomy + entries |

## AI

| Method | Path | Notes |
|---|---|---|
| POST | `/api/ai/chat` | `{message, mood?, servings?}` → `{reply, intent, recommendations, actions}` |
| POST | `/api/ai/vision` | `{labels[], description?}` → detected w/ confidence + `needs_confirmation`, advice, recommendations. Demo detector; swap `VISION_PROVIDER` later |
| GET | `/api/ai/history` | Last 30 conversation turns |

## Check / kitchen

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/kitchen` | List / add-update `{name, qty, unit, expiry_days?}` |
| PUT/DELETE | `/api/kitchen/{id}` | Edit / remove |
| POST | `/api/kitchen/check` | `{meal_id, servings}` → quantity-aware `{check, missing}` |

## Plan & track

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/planner` | `{date, meal_type, meal_id?, custom_name?, locked?}`; locked plans reject edits (409) |
| POST | `/api/planner/unlock/{id}` | Unlock |
| DELETE | `/api/planner/{id}` | Remove |
| GET | `/api/history` | Meal history |
| POST | `/api/history/complete` | `{meal_id, meal_type, servings, mode, date?, deduct_inventory?}` → tracks history + nutrition, optionally deducts inventory |

## Compare / cook / shop

| Method | Path | Notes |
|---|---|---|
| GET | `/api/compare/cook-vs-order/{meal_id}?servings=` | Cook cost/time/pros vs demo order range/options + savings verdict |
| GET | `/api/cook/{meal_id}?servings=` | Scaled ingredients, nutrition, cost, timed steps |
| GET | `/api/shopping` | Lists + items + totals |
| POST | `/api/shopping/generate` | `{meal_ids?, servings?, name?}` — only missing/insufficient added |
| PUT | `/api/shopping/item/{id}` | `{checked}` |
| POST | `/api/shopping/sync/{list_id}` | Checked items → kitchen (simulates grocery sync incl. qty) |
| GET | `/api/grocery/compare?q=` | `{demo:true, results[]}` — brand, pack, price, platform, delivery |
| GET | `/api/delivery/compare?dish=` | `{demo:true, results[]}` — restaurant, rating, price breakdown, total, ETA |

## Nutrition

| Method | Path | Notes |
|---|---|---|
| GET/PUT | `/api/nutrition/goals` | calorie/protein targets, nutrition & fitness goals |
| GET | `/api/nutrition/daily?day=` | consumed vs goals + logged meals + non-medical disclaimer |

## Config

`GET /api/config` — active LLM provider + feature flags. `GET /api/health` — service status.
