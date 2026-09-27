"""Deterministic, testable food-math: units, scaling, inventory, costs, nutrition, repetition."""
from __future__ import annotations

from datetime import date

WEIGHT = {"g": 1.0, "kg": 1000.0, "mg": 0.001}
VOLUME = {"ml": 1.0, "l": 1000.0, "tsp": 5.0, "tbsp": 15.0, "cup": 240.0}
COUNT = {"pcs": 1.0, "pc": 1.0, "nos": 1.0, "slice": 1.0, "pack": 1.0}

SALT_WORDS = {"salt", "turmeric", "chilli powder", "chili powder", "garam masala", "jeera", "cumin", "pepper", "sugar"}
# Approximate weight per piece for common produce (enables pcs↔g comparison).
PCS_GRAMS = {"onion": 100.0, "tomato": 80.0, "potato": 150.0, "lemon": 50.0,
             "eggs": 1.0, "egg": 1.0, "bread": 1.0, "maggi": 1.0, "capsicum": 100.0,
             "carrot": 80.0, "curd": 1.0, "milk": 1.0}
# Pantry staples assumed present in tiny quantities even if not tracked — but still shown, never silently ignored.
PANTRY_STAPLES = {"salt", "turmeric", "chilli powder", "chili powder", "garam masala",
                  "cumin", "jeera", "mustard seeds", "oil", "water", "sugar", "pepper"}


def to_base(qty: float, unit: str) -> tuple[float, str]:
    u = (unit or "g").lower()
    if u in WEIGHT:
        return qty * WEIGHT[u], "g"
    if u in VOLUME:
        return qty * VOLUME[u], "ml"
    return qty, "pcs"


def pretty_qty(base_qty: float, kind: str) -> tuple[float, str]:
    if kind == "g" and base_qty >= 1000:
        return round(base_qty / 1000, 2), "kg"
    if kind == "ml" and base_qty >= 1000:
        return round(base_qty / 1000, 2), "L"
    return round(base_qty, 1), kind


def scale_ingredients(ingredients: list[dict], from_serv: int, to_serv: int) -> list[dict]:
    f = (to_serv or 1) / max(1, from_serv or 1)
    out = []
    for ing in ingredients:
        q, u = to_base(float(ing.get("qty", 0)), ing.get("unit", "g"))
        scaled = q * f
        pq, pu = pretty_qty(scaled, u)
        out.append({**ing, "qty": pq, "unit": pu, "_base_qty": round(scaled, 2), "_base_unit": u})
    return out


def scale_nutrition(meal: dict, from_serv: int, to_serv: int) -> dict:
    f = (to_serv or 1) / max(1, from_serv or 1)
    return {k: round(float(meal.get(k, 0)) * f, 1) for k in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")}


def scale_cost(cost: float, from_serv: int, to_serv: int) -> float:
    return round(float(cost or 0) * ((to_serv or 1) / max(1, from_serv or 1)), 0)


def _comparable(have_base: float, have_kind: str, req_base: float, req_kind: str, name: str) -> tuple[float, str]:
    """Return (have_in_req_units, req_kind) handling pcs<->g estimates for produce."""
    if have_kind == req_kind:
        return have_base, req_kind
    key = (name or "").strip().lower()
    per = PCS_GRAMS.get(key, PCS_GRAMS.get(key.rstrip("s"), 0) if key.endswith("s") else 0)
    if req_kind == "g" and have_kind == "pcs" and per and per > 1:
        return have_base * per, "g"
    if req_kind == "pcs" and have_kind == "g" and per and per > 1:
        return have_base / per, "pcs"
    return have_base, have_kind  # incomparable → will read as missing unless pantry rule applies


def check_availability(required: list[dict], inventory: dict[str, dict]) -> dict:
    """Quantity-aware kitchen check. inventory: {canonical_name: {qty_base, unit_kind}}.

    Returns {items:[{name, required, required_unit, have, have_unit, status, missing_base}],
             overall: all|partial|missing, available_count, total_count}
    status: available | low (have>0 but <required) | missing
    """
    items, avail = [], 0
    for r in required:
        key = str(r.get("name", "")).strip().lower()
        rq, rk = to_base(float(r.get("qty", 0)), r.get("unit", "g"))
        inv = inventory.get(key)
        have_base = float(inv["qty_base"]) if inv else 0.0
        have_kind = inv["unit_kind"] if inv else rk
        have_cmp, cmp_kind = _comparable(have_base, have_kind, rq, rk, key)
        if cmp_kind != rk:
            have_cmp = 0.0  # incomparable units → treat as missing
        if rq <= 0:
            status = "available"
        elif have_cmp >= rq:
            status = "available"
        elif have_cmp > 0:
            status = "low"
        else:
            # pantry staples in micro qty: treat as available only if tiny requirement
            if key in PANTRY_STAPLES and rq <= (5 if rk == "g" else 15):
                status = "available"
            else:
                status = "missing"
        if status == "available":
            avail += 1
        hq, hu = pretty_qty(have_base, have_kind if have_kind in ("g", "ml", "pcs") else rk)
        items.append({
            "name": r.get("name", ""), "required": r.get("qty", 0), "required_unit": r.get("unit", "g"),
            "have": hq, "have_unit": hu, "status": status,
            "missing_base": round(max(0.0, rq - have_cmp), 2) if cmp_kind == rk else round(rq, 2),
            "missing_kind": rk,
        })
    total = len(required)
    overall = "all" if avail == total else ("partial" if avail > 0 else "missing")
    return {"items": items, "overall": overall, "available_count": avail, "total_count": total}


def missing_to_shopping(check: dict) -> list[dict]:
    out = []
    for it in check["items"]:
        if it["status"] in ("low", "missing") and it["missing_base"] > 0:
            q, u = pretty_qty(it["missing_base"], it["missing_kind"])
            out.append({"name": it["name"], "qty": q, "unit": u,
                        "reason": f"Need {it['required']}{it['required_unit']} for recipe"})
    return out


def violates_diet(meal_diet: str, user_diet: str) -> bool:
    m, u = (meal_diet or "").lower(), (user_diet or "").lower()
    if u in ("vegetarian", "veg"):
        return m in ("non-veg", "nonveg", "non-veg.", "eggetarian")
    if u == "eggetarian":
        return m in ("non-veg", "nonveg")
    if u == "vegan":
        return m in ("non-veg", "nonveg", "eggetarian", "veg")
    if u == "jain":
        return m in ("non-veg", "nonveg", "eggetarian")
    return False


def violates_allergy(ingredients: list[dict], allergies: list[str]) -> str | None:
    als = [a.strip().lower() for a in (allergies or []) if a.strip()]
    if not als:
        return None
    for ing in ingredients:
        n = str(ing.get("name", "")).lower()
        for a in als:
            if a and (a in n or n in a):
                return ing.get("name", "")
    return None


def violates_disliked(meal_name: str, ingredients: list[dict], disliked: list[str]) -> bool:
    ds = [d.strip().lower() for d in (disliked or []) if d.strip()]
    if not ds:
        return False
    hay = (meal_name or "").lower() + " " + " ".join(str(i.get("name", "")).lower() for i in ingredients)
    return any(d in hay for d in ds)


def repetition_blocked(meal_name: str, ingredients: list[dict], history: list[dict], rule: str) -> str | None:
    """history: [{meal_name, ingredients_text/date}]. Returns reason or None."""
    if rule in ("", "allow", None):
        return None
    hay = ((meal_name or "") + " " + " ".join(str(i.get("name", "")) for i in ingredients)).lower()
    main = ""
    for token in ("paneer", "chicken", "egg", "rajma", "dal", "mushroom", "fish", "mutter", "maggi", "rice"):
        if token in hay:
            main = token
            break
    days = 1 if rule == "no-same-day" else (2 if rule == "avoid-2-days" else 3)
    recent = history[: 8 if days > 1 else 4]
    for h in recent:
        text = ((h.get("meal_name", "") or "") + " " + (h.get("ingredients_text", "") or "")).lower()
        if meal_name and meal_name.lower() == (h.get("meal_name", "") or "").lower():
            return f"You had {meal_name} recently"
        if main and main in text:
            return f"You had {main} recently"
    return None


def aggregate_nutrition(logs: list[dict]) -> dict:
    tot = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for l in logs:
        for k in tot:
            tot[k] += float(l.get(k, 0) or 0)
    return {k: round(v, 1) for k, v in tot.items()}


def expiry_priority(expiry: date | None, today: date | None = None) -> int:
    """0 = expired/urgent, 1 = use soon (<=3d), 2 = ok, 3 = no expiry."""
    if expiry is None:
        return 3
    t = today or date.today()
    d = (expiry - t).days
    if d < 0:
        return 0
    if d <= 3:
        return 1
    return 2
