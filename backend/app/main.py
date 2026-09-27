"""App factory: CORS, routers, DB init + seed."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import entities  # noqa: F401  (register tables)
from app.api import auth as auth_api
from app.api import meals as meals_api
from app.api import ai as ai_api
from app.api import kitchen_planner as kp_api
from app.api import shop_nutrition as sn_api


def create_app() -> FastAPI:
    app = FastAPI(title="FoodMate API", version="0.1.0",
                  description="Personal food decision platform: DECIDE → CHECK → COMPARE → COOK/ORDER → TRACK")
    app.add_middleware(CORSMiddleware,
                       allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(auth_api.router)
    app.include_router(auth_api.router2)
    app.include_router(meals_api.router)
    app.include_router(ai_api.router)
    app.include_router(kp_api.router)
    app.include_router(kp_api.fav_router)
    app.include_router(sn_api.router)

    @app.get("/api/health")
    def health():
        return {"ok": True, "service": "foodmate", "demo": settings.DEMO_MODE,
                "ai_provider": settings.AI_PROVIDER}

    @app.on_event("startup")
    def startup():
        Base.metadata.create_all(bind=engine)
        seed()

    # Ensure tables exist even when lifespan events are skipped (tests, embeds)
    Base.metadata.create_all(bind=engine)
    try:
        seed()
    except Exception:
        pass

    return app


def seed():
    from datetime import date, timedelta
    from app.core.security import hash_password
    from app.data.seed_data import DEMO_INVENTORY, MEALS
    from app.models.entities import InventoryItem, Meal, MealHistory, Profile, User
    db = SessionLocal()
    try:
        # migrate demo user to eggetarian so egg meals are allowed (demo journey)
        try:
            from datetime import timedelta as _td
            demo = db.query(User).filter(User.email == "demo@foodmate.app").first()
            if demo:
                p = db.query(Profile).filter(Profile.user_id == demo.id).first()
                if p and p.diet == "vegetarian":
                    p.diet = "eggetarian"
                if not db.query(InventoryItem).filter(
                        InventoryItem.user_id == demo.id, InventoryItem.name == "spring onion").first():
                    db.add(InventoryItem(user_id=demo.id, name="spring onion",
                                         display="Spring onion", qty=50, unit="g",
                                         expiry=date.today() + _td(days=2)))
                db.commit()
        except Exception:
            pass
        if db.query(Meal).count() == 0:
            for m in MEALS:
                db.add(Meal(**{**m, "is_seed": True}))
            db.commit()
        if not db.query(User).filter(User.email == "demo@foodmate.app").first():
            u = User(name="Aarav", email="demo@foodmate.app", phone="9876543210",
                     password_hash=hash_password("demo1234"))
            db.add(u)
            db.flush()
            db.add(Profile(user_id=u.id, diet="eggetarian",
                           allergies=[], disliked=["paneer"],
                           favorites_food=["egg fried rice", "maggi"],
                           cuisines=["north-indian", "indo-chinese"],
                           cooking_ability="beginner", equipment=["gas stove", "pan", "pressure cooker"],
                           budget_per_meal=100, nutrition_goal="high-protein",
                           fitness_goal="muscle-gain", calorie_target=2200, protein_target=90,
                           repetition_rule="no-same-day"))
            for d in DEMO_INVENTORY:
                db.add(InventoryItem(user_id=u.id, name=d["name"], display=d["display"],
                                     qty=d["qty"], unit=d["unit"],
                                     expiry=date.today() + timedelta(days=d["days"])))
            # history: paneer at lunch today → no-repeat logic demo
            paneer = db.query(Meal).filter(Meal.name == "Paneer Bhurji").first()
            if paneer:
                db.add(MealHistory(user_id=u.id, date=date.today(), meal_type="lunch",
                                   meal_id=paneer.id, meal_name=paneer.name, servings=2,
                                   mode="cooked", cost=95, calories=380, protein_g=22))
            db.commit()
    finally:
        db.close()


app = create_app()
