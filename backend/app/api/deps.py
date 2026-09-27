"""Shared route dependencies."""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.entities import Profile, User
from app.services.food_math import to_base


def profile_dict(db: Session, user_id: int) -> dict:
    p = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not p:
        return {}
    return {"diet": p.diet, "allergies": p.allergies or [], "disliked": p.disliked or [],
            "favorites_food": p.favorites_food or [], "cuisines": p.cuisines or [],
            "cooking_ability": p.cooking_ability, "equipment": p.equipment or [],
            "budget_per_meal": p.budget_per_meal, "monthly_food_budget": p.monthly_food_budget,
            "meal_schedule": p.meal_schedule or {}, "nutrition_goal": p.nutrition_goal,
            "fitness_goal": p.fitness_goal, "calorie_target": p.calorie_target,
            "protein_target": p.protein_target, "repetition_rule": p.repetition_rule,
            "household_size": p.household_size}


def inventory_map(db: Session, user_id: int):
    from app.models.entities import InventoryItem
    items = db.query(InventoryItem).filter(InventoryItem.user_id == user_id).all()
    m = {}
    for it in items:
        q, k = to_base(float(it.qty or 0), it.unit or "g")
        key = (it.name or "").strip().lower()
        # pcs stored as count; also map singular/plural loosely
        m[key] = {"qty_base": q, "unit_kind": k, "display": it.display, "expiry": it.expiry}
    # alias: "onions"→"onion" etc. handled at lookup by trying singular
    return m, items


def lookup_inv(inv_map: dict, name: str):
    key = (name or "").strip().lower()
    if key in inv_map:
        return inv_map[key]
    if key.endswith("s") and key[:-1] in inv_map:
        return inv_map[key[:-1]]
    if (key + "s") in inv_map:
        return inv_map[key + "s"]
    # cooked rice vs rice
    return inv_map.get(key)
