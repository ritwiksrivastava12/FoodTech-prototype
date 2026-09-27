from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import inventory_map
from app.api.meals import _alias_map
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.entities import (Favorite, InventoryItem, Meal, MealHistory, MealPlan,
                                  NutritionLog, ShoppingItem, ShoppingList)
from app.schemas.schemas import HistoryCompleteIn, KitchenCheckIn, KitchenItemIn, PlanIn, ShoppingGenIn
from app.services import food_math as fm
from app.services.recommender import meal_to_dict

router = APIRouter(prefix="/api", tags=["kitchen-planner"])


# ---------- Kitchen ----------
@router.get("/kitchen")
def get_kitchen(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from datetime import date as d
    items = db.query(InventoryItem).filter(InventoryItem.user_id == uid).all()
    out = []
    for it in items:
        _, kind = fm.to_base(1, it.unit or "g")
        status = "available" if float(it.qty or 0) > 0 else "out-of-stock"
        if status == "available":
            # low-stock heuristic: <=20% of a typical pack
            if (kind == "g" and fm.to_base(float(it.qty), it.unit)[0] < 200) or \
               (kind == "ml" and fm.to_base(float(it.qty), it.unit)[0] < 200) or \
               (kind == "pcs" and float(it.qty) <= 2):
                status = "low-stock"
        exp_in = (it.expiry - d.today()).days if it.expiry else None
        out.append({"id": it.id, "name": it.name, "display": it.display or it.name,
                    "qty": it.qty, "unit": it.unit, "status": status,
                    "expiry": str(it.expiry) if it.expiry else None,
                    "expiry_in_days": exp_in,
                    "expiring_soon": exp_in is not None and 0 <= exp_in <= 3})
    return sorted(out, key=lambda x: (x["status"] == "out-of-stock", x.get("expiring_soon") is not True, x["display"]))


@router.post("/kitchen")
def add_item(body: KitchenItemIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from datetime import timedelta
    key = body.name.strip().lower()
    if not key:
        raise HTTPException(400, "Name required")
    q = db.query(InventoryItem).filter(InventoryItem.user_id == uid, InventoryItem.name == key).first()
    exp = date.today() + timedelta(days=body.expiry_days) if body.expiry_days else None
    if q:
        q.qty = float(body.qty)
        q.unit = body.unit
        if exp:
            q.expiry = exp
        if body.name.strip():
            q.display = body.name.strip().title()
    else:
        q = InventoryItem(user_id=uid, name=key, display=body.name.strip().title(),
                          qty=body.qty, unit=body.unit, expiry=exp)
        db.add(q)
    db.commit()
    return {"ok": True}


@router.put("/kitchen/{item_id}")
def update_item(item_id: int, body: KitchenItemIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    it = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
    if not it:
        raise HTTPException(404, "Item not found")
    it.qty = body.qty
    it.unit = body.unit
    if body.name.strip():
        it.display = body.name.strip().title()
    db.commit()
    return {"ok": True}


@router.delete("/kitchen/{item_id}")
def delete_item(item_id: int, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    it = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
    if not it:
        raise HTTPException(404, "Item not found")
    db.delete(it)
    db.commit()
    return {"ok": True}


@router.post("/kitchen/check")
def kitchen_check(body: KitchenCheckIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    m = db.query(Meal).filter(Meal.id == body.meal_id).first()
    if not m:
        raise HTTPException(404, "Meal not found")
    md = meal_to_dict(m)
    inv, _ = inventory_map(db, uid)
    req = fm.scale_ingredients(md["ingredients"], md["servings_default"], body.servings)
    check = fm.check_availability(req, _alias_map(inv))
    return {"meal": md["name"], "servings": body.servings, "check": check,
            "missing": fm.missing_to_shopping(check)}


# ---------- Planner ----------
@router.get("/planner")
def get_planner(week: str = "", uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.query(MealPlan).filter(MealPlan.user_id == uid).order_by(MealPlan.date).all()
    if week:
        rows = [r for r in rows if str(r.date).startswith(week[:7])]
    out = []
    for r in rows:
        meal = db.query(Meal).filter(Meal.id == r.meal_id).first() if r.meal_id else None
        out.append({"id": r.id, "date": str(r.date), "meal_type": r.meal_type,
                    "meal_id": r.meal_id, "meal_name": meal.name if meal else r.custom_name,
                    "image_emoji": meal.image_emoji if meal else "🍽️",
                    "locked": r.locked, "source": r.source})
    return out


@router.post("/planner")
def upsert_plan(body: PlanIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        d = datetime.strptime(body.date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    if body.meal_type not in ("breakfast", "lunch", "snacks", "dinner"):
        raise HTTPException(400, "Invalid meal_type")
    ex = db.query(MealPlan).filter(MealPlan.user_id == uid, MealPlan.date == d,
                                   MealPlan.meal_type == body.meal_type).first()
    if ex and ex.locked and not body.locked:
        raise HTTPException(409, "Meal is locked. Unlock first to change it.")
    if ex:
        ex.meal_id = body.meal_id
        ex.custom_name = body.custom_name
        ex.locked = body.locked
    else:
        ex = MealPlan(user_id=uid, date=d, meal_type=body.meal_type, meal_id=body.meal_id,
                      custom_name=body.custom_name, locked=body.locked)
        db.add(ex)
    db.commit()
    return {"ok": True}


@router.post("/planner/unlock/{plan_id}")
def unlock(plan_id: int, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    r = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == uid).first()
    if not r:
        raise HTTPException(404, "Not found")
    r.locked = False
    db.commit()
    return {"ok": True}


@router.delete("/planner/{plan_id}")
def delete_plan(plan_id: int, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    r = db.query(MealPlan).filter(MealPlan.id == plan_id, MealPlan.user_id == uid).first()
    if not r:
        raise HTTPException(404, "Not found")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ---------- History + complete meal ----------
@router.get("/history")
def history(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.query(MealHistory).filter(MealHistory.user_id == uid).order_by(MealHistory.id.desc()).limit(50).all()
    return [{"id": r.id, "date": str(r.date), "meal_type": r.meal_type, "meal_name": r.meal_name,
             "servings": r.servings, "mode": r.mode, "cost": r.cost, "calories": r.calories} for r in rows]


@router.post("/history/complete")
def complete_meal(body: HistoryCompleteIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    m = db.query(Meal).filter(Meal.id == body.meal_id).first()
    if not m:
        raise HTTPException(404, "Meal not found")
    md = meal_to_dict(m)
    d = date.today()
    if body.date:
        try:
            d = datetime.strptime(body.date, "%Y-%m-%d").date()
        except Exception:
            pass
    nut = fm.scale_nutrition(md, md["servings_default"], body.servings)
    cost = fm.scale_cost(md["cost_cook"] if body.mode == "cooked" else (md["cost_order_low"] + md["cost_order_high"]) / 2,
                         md["servings_default"], body.servings)
    db.add(MealHistory(user_id=uid, date=d, meal_type=body.meal_type, meal_id=m.id,
                       meal_name=m.name, servings=body.servings, mode=body.mode,
                       cost=cost, calories=nut["calories"], protein_g=nut["protein_g"]))
    db.add(NutritionLog(user_id=uid, date=d, meal_type=body.meal_type, meal_name=m.name, **nut))
    deducted = []
    if body.mode == "cooked" and body.deduct_inventory:
        inv_rows = {r.name: r for r in db.query(InventoryItem).filter(InventoryItem.user_id == uid).all()}
        req = fm.scale_ingredients(md["ingredients"], md["servings_default"], body.servings)
        for r in req:
            key = str(r.get("name", "")).lower()
            row = inv_rows.get(key) or inv_rows.get(key.rstrip("s")) or inv_rows.get(key + "s")
            if not row:
                continue
            need_base, need_kind = fm.to_base(float(r.get("_base_qty", r.get("qty", 0))), r.get("_base_unit", r.get("unit", "g")))
            have_base, _ = fm.to_base(float(row.qty or 0), row.unit or "g")
            left = max(0.0, have_base - need_base)
            # convert back to row unit
            if need_kind == "g" and (row.unit or "").lower() == "kg":
                row.qty = round(left / 1000, 3)
            elif need_kind == "ml" and (row.unit or "").lower() == "l":
                row.qty = round(left / 1000, 3)
            elif need_kind == "pcs":
                row.qty = round(left, 1)
            else:
                row.qty = round(left, 1)
            deducted.append({"name": row.display, "left": row.qty, "unit": row.unit})
    db.commit()
    return {"ok": True, "nutrition": nut, "cost": cost, "deducted": deducted,
            "message": f"{m.name} tracked. Inventory updated." if deducted else f"{m.name} tracked."}


# ---------- Favorites ----------
fav_router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@fav_router.get("")
def list_fav(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.query(Favorite).filter(Favorite.user_id == uid).all()
    out = []
    for f in rows:
        if f.meal_id:
            m = db.query(Meal).filter(Meal.id == f.meal_id).first()
            if m:
                md = meal_to_dict(m)
                out.append({"id": f.id, "meal_id": m.id, "name": m.name, "category": m.category,
                            "image_emoji": m.image_emoji, "time_min": m.time_min,
                            "protein_g": m.protein_g, "calories": m.calories, "cost_cook": m.cost_cook})
        else:
            out.append({"id": f.id, "meal_id": None, "name": f.name or (f.custom or {}).get("name", "Custom meal"),
                        "custom": f.custom})
    return out


@fav_router.post("")
def add_fav(body: dict, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if body.get("meal_id"):
        ex = db.query(Favorite).filter(Favorite.user_id == uid, Favorite.meal_id == body["meal_id"]).first()
        if ex:
            return {"ok": True, "message": "Already in favorites"}
        db.add(Favorite(user_id=uid, meal_id=body["meal_id"], name=""))
    else:
        name = str(body.get("name", "")).strip()
        if not name:
            raise HTTPException(400, "name or meal_id required")
        db.add(Favorite(user_id=uid, meal_id=None, name=name, custom=body))
    db.commit()
    return {"ok": True}


@fav_router.delete("/{fav_id}")
def del_fav(fav_id: int, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    f = db.query(Favorite).filter(Favorite.id == fav_id, Favorite.user_id == uid).first()
    if not f:
        raise HTTPException(404, "Not found")
    db.delete(f)
    db.commit()
    return {"ok": True}
