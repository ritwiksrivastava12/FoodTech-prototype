from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import inventory_map, profile_dict
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.entities import Conversation, Favorite, Meal, MealHistory
from app.schemas.schemas import ChatIn
from app.services import food_math as fm
from app.services.ai_orchestrator import craft_reply
from app.services.nlp import parse_intent
from app.services.recommender import build_context, current_meal_type, recommend

router = APIRouter(prefix="/api", tags=["ai"])


@router.get("/moods")
def moods():
    return [{"id": m, "emoji": e} for m, e in [
        ("tired", "😮‍💨"), ("happy", "😊"), ("stressed", "😣"), ("comfort", "🤗"),
        ("spicy", "🌶️"), ("light", "🥗"), ("healthy", "💪"), ("filling", "🍛"),
        ("high-protein", "🏋️"), ("budget", "💰"), ("quick", "⚡")]]


@router.post("/moods")
def save_mood(body: dict, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from app.models.entities import MoodEntry
    m = MoodEntry(user_id=uid, mood=str(body.get("mood", "")), note=str(body.get("note", ""))[:300])
    db.add(m)
    db.commit()
    return {"ok": True}


@router.post("/ai/chat")
def chat(body: ChatIn, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    meals = db.query(Meal).all()
    prof = profile_dict(db, uid)
    inv, items = inventory_map(db, uid)
    from app.api.meals import _alias_map
    inv = _alias_map(inv)
    hist = [{"meal_name": h.meal_name} for h in
            db.query(MealHistory).filter(MealHistory.user_id == uid).order_by(MealHistory.id.desc()).limit(10).all()]
    fav_ids = {f.meal_id for f in db.query(Favorite).filter(Favorite.user_id == uid).all() if f.meal_id}
    intent = parse_intent(body.message)
    # explicit "don't want X" respected via negatives in recommender
    ctx = build_context(prof, inv, hist, intent_text=body.message, mood=body.mood,
                        budget=intent.get("budget") or prof.get("budget_per_meal"),
                        availability={m.id: fm.check_availability(m.ingredients or [], inv) for m in meals},
                        favorite_ids=fav_ids)
    recs = recommend(meals, ctx, limit=3)
    for r in recs:
        r["servings"] = body.servings or 2
        r["nutrition_scaled"] = fm.scale_nutrition(r, r["servings_default"], body.servings or 2)
        r["cost_cook_scaled"] = fm.scale_cost(r["cost_cook"], r["servings_default"], body.servings or 2)
    summary_bits = []
    if ctx["mood"] or intent["moods"]:
        summary_bits.append(f"mood={','.join(intent['moods'])}")
    summary_bits.append(f"meal={ctx['meal_type']}")
    if ctx.get("budget"):
        summary_bits.append(f"budget=₹{ctx['budget']}")
    if intent.get("max_time"):
        summary_bits.append(f"time<={intent['max_time']}m")
    summary = ", ".join(summary_bits) or "your profile"
    reply = craft_reply(body.message, recs, summary)
    db.add(Conversation(user_id=uid, role="user", content=body.message))
    db.add(Conversation(user_id=uid, role="assistant", content=reply,
                        meta={"rec_ids": [r["id"] for r in recs]}))
    db.commit()
    return {"reply": reply, "intent": intent, "recommendations": recs,
            "actions": ["check-kitchen", "compare-cost", "cook", "plan", "save"]}


@router.post("/ai/vision")
def vision(body: dict, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Image understanding endpoint. Prototype uses a transparent heuristic/mock detector:
    client sends `labels` (from any vision model or manual tags) or `description` text.
    We never pretend perfect recognition — every label carries confidence + needs-confirmation flag."""
    labels = body.get("labels", []) or []
    desc = str(body.get("description", "") or "")
    detected = []
    known = ["rice", "eggs", "onion", "tomato", "paneer", "milk", "capsicum", "potato",
             "carrot", "bread", "maggi", "chicken", "curd", "oats", "peanuts", "lemon", "atta", "oil"]
    if labels:
        for l in labels:
            if isinstance(l, str):
                detected.append({"label": l, "confidence": 0.65, "needs_confirmation": True})
            else:
                detected.append({"label": l.get("label", ""), "confidence": float(l.get("confidence", 0.6)),
                                 "needs_confirmation": float(l.get("confidence", 0.6)) < 0.85})
    elif desc:
        dl = desc.lower()
        for k in known:
            if k in dl:
                detected.append({"label": k, "confidence": 0.7, "needs_confirmation": True})
    from app.services.ai_orchestrator import vision_advice
    # suggest meals from detected items
    meals = db.query(Meal).all()
    prof = profile_dict(db, uid)
    inv, _ = inventory_map(db, uid)
    from app.api.meals import _alias_map
    inv = _alias_map(inv)
    have_text = "I have " + ", ".join(d["label"] for d in detected) if detected else ""
    hist = [{"meal_name": h.meal_name} for h in
            db.query(MealHistory).filter(MealHistory.user_id == uid).order_by(MealHistory.id.desc()).limit(8).all()]
    ctx = build_context(prof, inv, hist, intent_text=have_text,
                        availability={m.id: fm.check_availability(m.ingredients or [], inv) for m in meals})
    recs = recommend(meals, ctx, limit=3) if detected else []
    return {"detected": detected, "advice": vision_advice(detected),
            "disclaimer": "Demo vision: confirm ingredients before cooking. Connect a production vision model via VISION_PROVIDER later.",
            "recommendations": recs}


@router.get("/ai/history")
def conv_history(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.query(Conversation).filter(Conversation.user_id == uid).order_by(Conversation.id.desc()).limit(30).all()
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]
