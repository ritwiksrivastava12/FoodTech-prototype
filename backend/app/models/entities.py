"""Relational data model. Conversation/mood docs can move to Mongo later without API change."""
import datetime as dt
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Float, ForeignKey,
                        Integer, String, Text, UniqueConstraint)

from app.core.database import Base


def now():
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(30), default="")
    password_hash = Column(String(400), nullable=False)
    created_at = Column(DateTime, default=now)


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    diet = Column(String(30), default="vegetarian")  # vegetarian|non-veg|eggetarian|vegan|jain|other
    allergies = Column(JSON, default=list)  # e.g. ["peanut","milk"]
    disliked = Column(JSON, default=list)  # ingredient/meal names lowercased
    favorites_food = Column(JSON, default=list)
    cuisines = Column(JSON, default=list)
    cooking_ability = Column(String(30), default="beginner")  # beginner|intermediate|advanced
    equipment = Column(JSON, default=list)
    budget_per_meal = Column(Float, default=150.0)
    monthly_food_budget = Column(Float, default=6000.0)
    meal_schedule = Column(JSON, default=dict)
    nutrition_goal = Column(String(40), default="balanced")  # balanced|high-protein|muscle-gain|weight-loss|low-carb
    fitness_goal = Column(String(40), default="stay-fit")
    calorie_target = Column(Integer, default=2000)
    protein_target = Column(Integer, default=70)
    repetition_rule = Column(String(30), default="no-same-day")  # allow|no-same-day|avoid-2-days|avoid-3-days
    household_size = Column(Integer, default=1)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False, index=True)
    category = Column(String(60), default="dinner")  # breakfast|lunch|snacks|dinner
    cuisine = Column(String(60), default="indian")
    diet = Column(String(30), default="veg")  # veg|non-veg|eggetarian|vegan|jain
    description = Column(Text, default="")
    image_emoji = Column(String(16), default="🍛")
    image_url = Column(String(500), default="")
    time_min = Column(Integer, default=20)
    difficulty = Column(String(20), default="easy")
    servings_default = Column(Integer, default=2)
    # per default servings:
    calories = Column(Float, default=0)
    protein_g = Column(Float, default=0)
    carbs_g = Column(Float, default=0)
    fat_g = Column(Float, default=0)
    fiber_g = Column(Float, default=0)
    cost_cook = Column(Float, default=0)  # INR home cooking, default servings
    cost_order_low = Column(Float, default=0)
    cost_order_high = Column(Float, default=0)
    ingredients = Column(JSON, default=list)  # [{name, qty, unit, category}]
    steps = Column(JSON, default=list)  # [{title, detail, minutes, timer_sec?}]
    mood_tags = Column(JSON, default=list)  # tired|comfort|spicy|happy|stressed|light|healthy|filling...
    tags = Column(JSON, default=list)
    rating = Column(Float, default=4.2)
    is_seed = Column(Boolean, default=False)


class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=True)
    custom = Column(JSON, default=dict)  # for manually added meals
    name = Column(String(160), default="")
    created_at = Column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "meal_id", name="uq_fav"),)


class InventoryItem(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(120), nullable=False)  # canonical lower
    display = Column(String(120), default="")
    qty = Column(Float, default=0)
    unit = Column(String(20), default="g")  # g|kg|ml|L|pcs
    expiry = Column(Date, nullable=True)
    updated_at = Column(DateTime, default=now, onupdate=now)


class MealPlan(Base):
    __tablename__ = "meal_plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)  # breakfast|lunch|snacks|dinner
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=True)
    custom_name = Column(String(160), default="")
    locked = Column(Boolean, default=False)
    source = Column(String(30), default="ai")  # ai|favorite|manual


class MealHistory(Base):
    __tablename__ = "meal_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), default="dinner")
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=True)
    meal_name = Column(String(160), default="")
    servings = Column(Integer, default=2)
    mode = Column(String(20), default="cooked")  # cooked|ordered|skipped
    cost = Column(Float, default=0)
    calories = Column(Float, default=0)
    protein_g = Column(Float, default=0)
    created_at = Column(DateTime, default=now)


class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(160), default="Weekly groceries")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=now)


class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("shopping_lists.id"), index=True, nullable=False)
    name = Column(String(120), nullable=False)
    qty = Column(Float, default=1)
    unit = Column(String(20), default="g")
    est_price = Column(Float, default=0)
    checked = Column(Boolean, default=False)
    reason = Column(String(200), default="")


class MoodEntry(Base):
    __tablename__ = "moods"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    mood = Column(String(60), nullable=False)
    note = Column(String(300), default="")
    created_at = Column(DateTime, default=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # user|assistant
    content = Column(Text, nullable=False)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), default="dinner")
    meal_name = Column(String(160), default="")
    calories = Column(Float, default=0)
    protein_g = Column(Float, default=0)
    carbs_g = Column(Float, default=0)
    fat_g = Column(Float, default=0)
    fiber_g = Column(Float, default=0)
