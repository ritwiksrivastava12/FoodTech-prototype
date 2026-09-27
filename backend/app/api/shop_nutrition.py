from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import inventory_map, profile_dict
from app.api.meals import _alias_map
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.integrations.adapters import delivery, grocery
from app.models.entities import InventoryItem, Meal, NutritionLog, ShoppingItem, ShoppingList
from app.schemas.schemas import ShoppingGenIn
from app.services import food_math as fm
from app.services.recommender import meal_to_dict

router = APIRouter(prefix="/api", tags=["shop-nutrition-cook"])


# ---------- Shopping ----------
@router.get("/shopping")
def lists(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    out = []
    for l in db.query(ShoppingList).filter(ShoppingList.user_id == uid).order_by(ShoppingList.id.desc()).all():
        items = db.query(ShoppingItem).filter(ShoppingItem.list_id == l.id).all()
        out.append({"id": l.id, "name": l.name, "status": l.status,
                    "items": [{"id": i.id, "name": i.name, "qty": i.qty, "unit": i.unit,
                               "est_price": i.est_price, "checked": i.checked, "reason": i.reason} for i in items],
                    "total_est": round(sum(i.est_price or 0 for i in items), 0)})
    return out


@router.post("/shopping/generate")
def generate(body: ShoppingGenIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    inv, _ = inventory_map(db, uid)
    inv = _alias_map(inv)
    agg: dict[str, dict] = {}
    if body.meal_ids:
        meals = db.query(Meal).filter(Meal.id.in_(body.meal_ids)).all()
    else:
        # from unlocked planner items without full coverage — use next 7 days
        from app.models.entities import MealPlan
        plans = db.query(MealPlan).filter(MealPlan.user_id == uid).all()
        meals = []
        for p in plans:
            if p.meal_id:
                m = db.query(Meal).filter(Meal.id == p.meal_id).first()
                if m:
                    meals.append(m)
    for m in meals:
        md = meal_to_dict(m)
        req = fm.scale_ingredients(md["ingredients"], md["servings_default"], body.servings)
        check = fm.check_availability(req, inv)
        for miss in fm.missing_to_shopping(check):
            k = miss["name"].lower()
            if k in agg:
                # sum in base units
                b1, k1 = fm.to_base(agg[k]["qty"], agg[k]["unit"])
                b2, _ = fm.to_base(miss["qty"], miss["unit"])
                q, u = fm.pretty_qty(b1 + b2, k1)
                agg[k].update(qty=q, unit=u)
            else:
                agg[k] = {**miss, "est_price": 0}
    # naive price estimates from grocery demo
    demo = {g["name"].lower(): g["price"] for g in grocery.compare("")}
    for k, v in agg.items():
        for dn, p in demo.items():
            if k in dn or dn.split()[0] in k:
                v["est_price"] = p
                break
        else:
            v["est_price"] = 30
    lst = ShoppingList(user_id=uid, name=body.name)
    db.add(lst)
    db.flush()
    for k, v in agg.items():
        db.add(ShoppingItem(list_id=lst.id, name=v["name"], qty=v["qty"], unit=v["unit"],
                            est_price=v["est_price"], reason=v.get("reason", "")))
    db.commit()
    return {"ok": True, "list_id": lst.id, "items_added": len(agg),
            "message": f"Added {len(agg)} missing item(s). Sufficient stock was skipped." if agg else "Nothing missing — your kitchen covers it."}


@router.put("/shopping/item/{item_id}")
def toggle_item(item_id: int, body: dict, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    it = db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
    if not it:
        raise HTTPException(404, "Not found")
    lst = db.query(ShoppingList).filter(ShoppingList.id == it.list_id, ShoppingList.user_id == uid).first()
    if not lst:
        raise HTTPException(403, "Not yours")
    if "checked" in body:
        it.checked = bool(body["checked"])
    db.commit()
    return {"ok": True}


@router.post("/shopping/sync/{list_id}")
def sync_to_kitchen(list_id: int, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Simulate grocery purchase → add checked items into inventory (future: real platform sync w/ qty+expiry)."""
    lst = db.query(ShoppingList).filter(ShoppingList.id == list_id, ShoppingList.user_id == uid).first()
    if not lst:
        raise HTTPException(404, "Not found")
    items = db.query(ShoppingItem).filter(ShoppingItem.list_id == list_id, ShoppingItem.checked == True).all()  # noqa: E712
    inv = {r.name: r for r in db.query(InventoryItem).filter(InventoryItem.user_id == uid).all()}
    for i in items:
        key = i.name.strip().lower()
        row = inv.get(key)
        if row:
            b1, k1 = fm.to_base(float(row.qty or 0), row.unit or "g")
            b2, k2 = fm.to_base(float(i.qty or 0), i.unit or "g")
            if k1 == k2:
                q, u = fm.pretty_qty(b1 + b2, k1)
                # keep row unit if convertible
                row.qty = round((b1 + b2) / (fm.to_base(1, row.unit)[0]), 2)
        else:
            db.add(InventoryItem(user_id=uid, name=key, display=i.name, qty=i.qty, unit=i.unit))
    lst.status = "purchased"
    db.commit()
    return {"ok": True, "synced": len(items)}


# ---------- Grocery + delivery compare (demo-labelled) ----------
@router.get("/grocery/compare")
def grocery_compare(q: str = "", uid: int = Depends(get_current_user_id)):
    return {"demo": True, "notice": "Demo prices — no live order. Connect a grocery partner to go live.",
            "results": grocery.compare(q)}


@router.get("/delivery/compare")
def delivery_compare(dish: str = "", uid: int = Depends(get_current_user_id)):
    return {"demo": True, "notice": "Demo estimates — no live order. Connect Swiggy/Zomato partner to go live.",
            "results": delivery.compare(dish)}


@router.get("/compare/cook-vs-order/{meal_id}")
def cook_vs_order(meal_id: int, servings: int = 2, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    m = db.query(Meal).filter(Meal.id == meal_id).first()
    if not m:
        raise HTTPException(404, "Meal not found")
    md = meal_to_dict(m)
    cook = fm.scale_cost(md["cost_cook"], md["servings_default"], servings)
    order_opts = delivery.compare(md["name"])
    return {"meal": md["name"], "servings": servings, "demo": True,
            "cook": {"cost": cook, "time_min": md["time_min"],
                     "pros": ["Cheaper", "You control nutrition & spice", "Uses your kitchen stock"],
                     "cons": ["Takes time & effort"]},
            "order": {"range": [md["cost_order_low"], md["cost_order_high"]],
                      "options": order_opts[:4],
                      "pros": ["Zero effort", "Fast when tired"],
                      "cons": ["Costs 2–3× more", "Less control on oil/nutrition"]},
            "savings": round(((md["cost_order_low"] + md["cost_order_high"]) / 2) - cook, 0),
            "verdict": f"Cooking saves ~₹{round(((md['cost_order_low']+md['cost_order_high'])/2)-cook,0)} vs ordering."}


# ---------- Cook mode ----------
@router.get("/cook/{meal_id}")
def cook_mode(meal_id: int, servings: int = 2, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    m = db.query(Meal).filter(Meal.id == meal_id).first()
    if not m:
        raise HTTPException(404, "Meal not found")
    md = meal_to_dict(m)
    ing = fm.scale_ingredients(md["ingredients"], md["servings_default"], servings)
    nut = fm.scale_nutrition(md, md["servings_default"], servings)
    steps = []
    for i, s in enumerate(md["steps"], 1):
        steps.append({"n": i, "of": len(md["steps"]), "title": s.get("title", f"Step {i}"),
                      "detail": s.get("detail", ""), "minutes": s.get("minutes", 2),
                      "timer_sec": s.get("timer_sec")})
    return {"meal": md["name"], "servings": servings, "ingredients": ing,
            "nutrition": nut, "cost": fm.scale_cost(md["cost_cook"], md["servings_default"], servings),
            "steps": steps}


# ---------- Nutrition ----------
@router.get("/nutrition/goals")
def get_goals(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = profile_dict(db, uid)
    return {"calorie_target": p.get("calorie_target", 2000), "protein_target": p.get("protein_target", 70),
            "nutrition_goal": p.get("nutrition_goal", "balanced"), "fitness_goal": p.get("fitness_goal", "stay-fit")}


@router.put("/nutrition/goals")
def put_goals(body: dict, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from app.models.entities import Profile
    p = db.query(Profile).filter(Profile.user_id == uid).first()
    for k in ("calorie_target", "protein_target", "nutrition_goal", "fitness_goal"):
        if k in body:
            setattr(p, k, body[k])
    db.commit()
    return {"ok": True}


@router.get("/nutrition/daily")
def daily(day: str = "", uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    d = date.today()
    if day:
        try:
            d = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            pass
    logs = db.query(NutritionLog).filter(NutritionLog.user_id == uid, NutritionLog.date == d).all()
    tot = fm.aggregate_nutrition([{"calories": l.calories, "protein_g": l.protein_g, "carbs_g": l.carbs_g,
                                   "fat_g": l.fat_g, "fiber_g": l.fiber_g} for l in logs])
    goals = {"calorie_target": 2000, "protein_target": 70}
    from app.models.entities import Profile
    p = db.query(Profile).filter(Profile.user_id == uid).first()
    if p:
        goals = {"calorie_target": p.calorie_target or 2000, "protein_target": p.protein_target or 70}
    return {"date": str(d), "consumed": tot, "goals": goals,
            "meals": [{"meal_type": l.meal_type, "meal_name": l.meal_name, "calories": l.calories, "protein_g": l.protein_g} for l in logs],
            "disclaimer": "General nutrition info, not medical advice."}


@router.get("/config")
def config():
    from app.integrations.adapters import LLMAdapter
    return {"llm": LLMAdapter.status(), "features": {"voice": True, "vision": "demo", "grocery": "demo", "delivery": "demo"}}
