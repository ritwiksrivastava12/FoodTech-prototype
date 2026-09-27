"""Recommendation engine: hard safety filters → deterministic scoring → explained results.

Designed so a future ML model can replace `score_meal` without changing the API contract.
"""
from __future__ import annotations

from datetime import datetime

from app.services import food_math as fm
from app.services.nlp import parse_intent


def meal_to_dict(m) -> dict:
    return {
        "id": m.id, "name": m.name, "category": m.category, "cuisine": m.cuisine,
        "diet": m.diet, "description": m.description or "",
        "image_emoji": m.image_emoji or "🍛", "image_url": m.image_url or "",
        "time_min": m.time_min, "difficulty": m.difficulty,
        "servings_default": m.servings_default or 2,
        "calories": m.calories, "protein_g": m.protein_g, "carbs_g": m.carbs_g,
        "fat_g": m.fat_g, "fiber_g": m.fiber_g,
        "cost_cook": m.cost_cook, "cost_order_low": m.cost_order_low,
        "cost_order_high": m.cost_order_high,
        "ingredients": m.ingredients or [], "steps": m.steps or [],
        "mood_tags": m.mood_tags or [], "tags": m.tags or [],
        "rating": m.rating or 4.0,
    }


def current_meal_type(hour: int | None = None) -> str:
    h = datetime.now().hour if hour is None else hour
    if 5 <= h < 11:
        return "breakfast"
    if 11 <= h < 16:
        return "lunch"
    if 16 <= h < 19:
        return "snacks"
    return "dinner"


def score_meal(md: dict, ctx: dict) -> tuple[float, list[str]]:
    """Returns (score, reasons). Higher is better."""
    score, reasons = 50.0, []
    intent = ctx.get("intent", {})
    moods: list[str] = intent.get("moods", []) or ([ctx.get("mood")] if ctx.get("mood") else [])
    # mood match (important but not sole factor)
    mt = [x.lower() for x in (md.get("mood_tags") or [])]
    hits = [m for m in moods if m.lower() in mt]
    if hits:
        score += 14 + 3 * len(hits)
        reasons.append(f"Matches your mood ({', '.join(hits)})")
    # category
    want_cat = intent.get("meal_type") or ctx.get("meal_type")
    if want_cat and md.get("category") == want_cat:
        score += 6
        reasons.append(f"Great for {want_cat}")
    # budget
    budget = intent.get("budget") if intent.get("budget") is not None else ctx.get("budget")
    if budget:
        if md["cost_cook"] <= budget:
            score += 10
            reasons.append(f"Fits your ₹{budget} budget (cook ~₹{int(md['cost_cook'])})")
        else:
            score -= 18
    # time
    mt_max = intent.get("max_time") or ctx.get("max_time")
    if mt_max and md["time_min"] <= mt_max:
        score += 9
        reasons.append(f"Ready in {md['time_min']} min (you have {mt_max})")
    elif mt_max and md["time_min"] > mt_max:
        score -= 14
    # availability
    avail = ctx.get("availability", {}).get(md["id"])
    if avail:
        if avail["overall"] == "all":
            score += 12
            reasons.append("You have all the ingredients")
        elif avail["overall"] == "partial":
            score += 4
            reasons.append(f"You have {avail['available_count']}/{avail['total_count']} ingredients")
        else:
            score -= 6
    # have-ingredients bonus
    have = [h.lower().rstrip("s") if h.lower() not in ("rice",) else h.lower() for h in (intent.get("have") or [])]
    if have:
        names = " ".join(i.get("name", "").lower().rstrip("s") if not i.get("name", "").lower().endswith("rice") else i.get("name", "").lower() for i in md.get("ingredients", []))
        overlap = sum(1 for h in have if h and (h in names or h.rstrip("s") in names))
        if overlap:
            score += min(12, 5 * overlap)
            reasons.append(f"Uses what you have ({overlap} match{'es' if overlap>1 else ''})")
    # expiry priority
    exp_bonus = ctx.get("expiry_bonus", {}).get(md["id"], 0)
    if exp_bonus:
        score += exp_bonus
        reasons.append("Uses ingredients expiring soon — less waste")
    # nutrition goals
    if ctx.get("high_protein") or intent.get("high_protein"):
        p = md.get("protein_g", 0)
        if p >= 18:
            score += 10
            reasons.append(f"High protein ({p:.0f}g)")
        elif p >= 12:
            score += 5
    if ctx.get("nutrition_goal") in ("weight-loss", "low-carb", "balanced") and md.get("calories", 0) <= 450:
        score += 3
    # favorites
    if md["id"] in ctx.get("favorite_ids", set()):
        score += 6
        reasons.append("One of your go-to meals")
    # rating
    score += (md.get("rating", 4.0) - 4.0) * 4
    # quick & easy
    if ctx.get("quick_only") and md["time_min"] > 20:
        score -= 20
    return round(score, 1), reasons[:4]


def recommend(meals: list, ctx: dict, limit: int = 8) -> list[dict]:
    """Apply hard filters, score, sort, diversify mains. Returns enriched meal dicts."""
    profile = ctx.get("profile", {})
    intent = ctx.get("intent", {})
    diet = profile.get("diet", "")
    allergies = profile.get("allergies", [])
    disliked = list(profile.get("disliked", []) or []) + [n.lower() for n in (intent.get("negatives", []) or [])]
    history = ctx.get("history", [])
    rule = profile.get("repetition_rule", "no-same-day")

    ranked = []
    for m in meals:
        md = meal_to_dict(m)
        if fm.violates_diet(md["diet"], diet):
            continue
        bad = fm.violates_allergy(md["ingredients"], allergies)
        if bad:
            continue
        if fm.violates_disliked(md["name"], md["ingredients"], disliked):
            continue
        blocked = fm.repetition_blocked(md["name"], md["ingredients"], history, rule)
        if blocked and not ctx.get("allow_repeat"):
            continue
        s, reasons = score_meal(md, ctx)
        avail = ctx.get("availability", {}).get(md["id"])
        md["score"] = s
        md["reasons"] = reasons or ["Balanced pick for you"]
        md["availability"] = avail or {"overall": "unknown", "available_count": 0, "total_count": len(md["ingredients"])}
        md["repeat_note"] = blocked
        ranked.append(md)
    ranked.sort(key=lambda x: -x["score"])
    # diversify: avoid same leading main back-to-back, but never bury a much better pick.
    out, remaining = [], ranked[:]
    while remaining and len(out) >= 0 and len(out) < limit:
        pick = remaining[0]
        key = pick["name"].split()[0].lower()
        last_keys = [x["name"].split()[0].lower() for x in out[-2:]]
        if key not in last_keys:
            out.append(pick)
            remaining.pop(0)
            continue
        # conflict: look for a non-conflicting alternative within 15 pts
        alt_idx = next((i for i, r in enumerate(remaining[1:], 1)
                        if r["name"].split()[0].lower() not in last_keys
                        and (pick["score"] - r["score"]) <= 15), None)
        if alt_idx is not None:
            out.append(remaining.pop(alt_idx))
        else:
            out.append(pick)
            remaining.pop(0)
    return out


def build_context(profile: dict, inventory_map: dict, history: list, intent_text: str = "",
                  mood: str = "", meal_type: str = "", budget=None, max_time=None,
                  availability: dict | None = None, expiry_bonus: dict | None = None,
                  favorite_ids: set | None = None, **kw) -> dict:
    intent = parse_intent(intent_text or "")
    if mood and mood not in intent["moods"]:
        intent["moods"] = [mood] + intent["moods"]
    return {
        "profile": profile, "intent": intent, "mood": mood,
        "meal_type": intent.get("meal_type") or meal_type or current_meal_type(),
        "budget": intent.get("budget") if intent.get("budget") is not None else budget,
        "max_time": intent.get("max_time") or max_time,
        "availability": availability or {}, "expiry_bonus": expiry_bonus or {},
        "favorite_ids": favorite_ids or set(), "history": history,
        "high_protein": intent.get("high_protein") or profile.get("nutrition_goal") in ("high-protein", "muscle-gain"),
        "nutrition_goal": profile.get("nutrition_goal"),
        "quick_only": kw.get("quick_only", False),
        "allow_repeat": kw.get("allow_repeat", False),
    }
