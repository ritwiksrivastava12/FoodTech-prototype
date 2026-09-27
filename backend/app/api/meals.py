from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import inventory_map, lookup_inv, profile_dict
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.entities import Favorite, Meal, MealHistory
from app.schemas.schemas import RecommendIn
from app.services import food_math as fm
from app.services.nlp import parse_intent
from app.services.recommender import build_context, current_meal_type, meal_to_dict, recommend

router = APIRouter(prefix="/api", tags=["meals"])


def enrich(md: dict, servings: int, inv) -> dict:
    req = fm.scale_ingredients(md["ingredients"], md["servings_default"], servings)
    check = fm.check_availability(req, inv)
    nut = fm.scale_nutrition(md, md["servings_default"], servings)
    cook = fm.scale_cost(md["cost_cook"], md["servings_default"], servings)
    return {**md, "servings": servings, "scaled_ingredients": req,
            "availability": check, "nutrition_scaled": nut, "cost_cook_scaled": cook,
            "missing": fm.missing_to_shopping(check)}


@router.get("/meals")
def list_meals(category: str = "", q: str = "", uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    query = db.query(Meal)
    if category:
        query = query.filter(Meal.category == category)
    meals = query.order_by(Meal.rating.desc()).all()
    inv, _ = inventory_map(db, uid)
    inv_lookup = {}
    for k, v in inv.items():
        inv_lookup[k] = v
    # wrap lookup with singular handling
    from app.api.deps import lookup_inv as li
    full = dict(inv)
    out = []
    for m in meals:
        md = meal_to_dict(m)
        if q and q.lower() not in (md["name"] + " " + " ".join(md["tags"]) + " " + md["cuisine"]).lower():
            continue
        # build availability with alias-tolerant map
        req = md["ingredients"]
        # temporarily expand inv with singular/plural keys
        check = fm.check_availability(req, _alias_map(full))
        out.append({**md, "availability": {"overall": check["overall"],
                                           "available_count": check["available_count"],
                                           "total_count": check["total_count"]}})
    return out


def _alias_map(inv: dict) -> dict:
    m = dict(inv)
    for k, v in list(inv.items()):
        if k.endswith("s"):
            m.setdefault(k[:-1], v)
        else:
            m.setdefault(k + "s", v)
    return m


@router.get("/meals/search")
def search_meals(q: str = Query("", min_length=1), uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Natural-language aware search: handles 'high protein under ₹150', 'I have rice eggs', 'without paneer', '15 min'."""
    intent = parse_intent(q)
    meals = db.query(Meal).all()
    prof = profile_dict(db, uid)
    inv, _ = inventory_map(db, uid)
    inv = _alias_map(inv)
    history = [{"meal_name": h.meal_name} for h in
               db.query(MealHistory).filter(MealHistory.user_id == uid).order_by(MealHistory.id.desc()).limit(8).all()]
    fav_ids = {f.meal_id for f in db.query(Favorite).filter(Favorite.user_id == uid).all() if f.meal_id}
    ctx = build_context(prof, inv, history, intent_text=q, budget=intent.get("budget"),
                        availability={m.id: fm.check_availability(m.ingredients or [], inv) for m in meals},
                        favorite_ids=fav_ids, allow_repeat=True)
    # hard diet/allergy filter + negatives
    results = recommend(meals, ctx, limit=12)
    # extra text relevance: if query names a dish/ingredient, boost
    ql = q.lower()
    for r in results:
        if any(w in (r["name"] + " " + " ".join(r["tags"])).lower() for w in ql.split() if len(w) > 3):
            r["score"] += 2
    results.sort(key=lambda x: -x["score"])
    return {"intent": intent, "results": results}


@router.get("/meals/{meal_id}")
def meal_detail(meal_id: int, servings: int = 2, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    m = db.query(Meal).filter(Meal.id == meal_id).first()
    if not m:
        raise HTTPException(404, "Meal not found")
    md = meal_to_dict(m)
    inv, _ = inventory_map(db, uid)
    return enrich(md, servings, _alias_map(inv))


@router.post("/meals")
def create_meal(body: dict, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "Meal name is required")
    m = Meal(name=name, category=body.get("category", "dinner"), cuisine=body.get("cuisine", "home"),
             diet=body.get("diet", "veg"), description=body.get("description", ""),
             image_emoji=body.get("image_emoji", "🍽️"), time_min=int(body.get("time_min", 20)),
             servings_default=int(body.get("servings", 2)),
             calories=float(body.get("calories", 0)), protein_g=float(body.get("protein_g", 0)),
             carbs_g=float(body.get("carbs_g", 0)), fat_g=float(body.get("fat_g", 0)),
             fiber_g=float(body.get("fiber_g", 0)), cost_cook=float(body.get("cost_cook", 80)),
             cost_order_low=float(body.get("cost_order_low", 129)),
             cost_order_high=float(body.get("cost_order_high", 179)),
             ingredients=body.get("ingredients", []), steps=body.get("steps", []),
             mood_tags=body.get("mood_tags", []), tags=body.get("tags", []), rating=4.0)
    db.add(m)
    db.commit()
    db.refresh(m)
    return meal_to_dict(m)


@router.post("/recommendations")
def recommendations(body: RecommendIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    meals = db.query(Meal).all()
    prof = profile_dict(db, uid)
    inv, items = inventory_map(db, uid)
    inv = _alias_map(inv)
    hist_rows = db.query(MealHistory).filter(MealHistory.user_id == uid).order_by(MealHistory.id.desc()).limit(12).all()
    history = [{"meal_name": h.meal_name} for h in hist_rows]
    fav_ids = {f.meal_id for f in db.query(Favorite).filter(Favorite.user_id == uid).all() if f.meal_id}
    # expiry bonus: meals using items expiring <=3 days get +6
    from datetime import date
    soon = set()
    for it in items:
        if it.expiry and (it.expiry - date.today()).days <= 3 and float(it.qty or 0) > 0:
            soon.add((it.name or "").lower())
    expiry_bonus = {}
    for m in meals:
        names = " ".join(i.get("name", "").lower() for i in (m.ingredients or []))
        if any(s in names for s in soon):
            expiry_bonus[m.id] = 6
    ctx = build_context(prof, inv, history, intent_text=body.intent_text, mood=body.mood,
                        meal_type=body.meal_type or current_meal_type(),
                        budget=body.budget if body.budget is not None else prof.get("budget_per_meal"),
                        max_time=body.max_time,
                        availability={m.id: fm.check_availability(m.ingredients or [], inv) for m in meals},
                        expiry_bonus=expiry_bonus, favorite_ids=fav_ids,
                        quick_only=body.quick_only, allow_repeat=body.allow_repeat)
    recs = recommend(meals, ctx, limit=body.limit)
    for r in recs:
        nut = fm.scale_nutrition(r, r["servings_default"], body.servings or 2)
        r["nutrition_scaled"] = nut
        r["cost_cook_scaled"] = fm.scale_cost(r["cost_cook"], r["servings_default"], body.servings or 2)
        r["servings"] = body.servings or 2
        r["missing"] = fm.missing_to_shopping(r["availability"]) if isinstance(r.get("availability"), dict) and "items" in r["availability"] else []
    return {"meal_type": ctx["meal_type"], "intent": ctx["intent"], "results": recs,
            "sections": build_sections(recs)}


def build_sections(recs: list[dict]) -> list[dict]:
    def pick(fn, title, subtitle):
        items = [r for r in recs if fn(r)][:6]
        return {"title": title, "subtitle": subtitle, "ids": [r["id"] for r in items]} if items else None
    secs = [
        pick(lambda r: True, "Recommended for you", "Based on mood, kitchen, budget & history"),
        pick(lambda r: r["availability"].get("overall") == "all", "Ready to cook now", "You have everything"),
        pick(lambda r: r["time_min"] <= 15, "Under 15 minutes", "When time is short"),
        pick(lambda r: r.get("cost_cook_scaled", r["cost_cook"]) <= 100, "Under ₹100", "Budget friendly"),
        pick(lambda r: r["protein_g"] >= 18, "High protein", "For gym & muscle goals"),
    ]
    return [s for s in secs if s]
