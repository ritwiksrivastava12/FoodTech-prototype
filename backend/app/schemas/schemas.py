from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    phone: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    diet: Optional[str] = None
    allergies: Optional[list[str]] = None
    disliked: Optional[list[str]] = None
    favorites_food: Optional[list[str]] = None
    cuisines: Optional[list[str]] = None
    cooking_ability: Optional[str] = None
    equipment: Optional[list[str]] = None
    budget_per_meal: Optional[float] = None
    monthly_food_budget: Optional[float] = None
    meal_schedule: Optional[dict] = None
    nutrition_goal: Optional[str] = None
    fitness_goal: Optional[str] = None
    calorie_target: Optional[int] = None
    protein_target: Optional[int] = None
    repetition_rule: Optional[str] = None
    household_size: Optional[int] = None


class RecommendIn(BaseModel):
    mood: str = ""
    intent_text: str = ""
    meal_type: str = ""
    budget: Optional[float] = None
    max_time: Optional[int] = None
    servings: int = 2
    quick_only: bool = False
    allow_repeat: bool = False
    limit: int = 8


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    mood: str = ""
    servings: int = 2


class KitchenItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    qty: float = 0
    unit: str = "g"
    expiry_days: Optional[int] = None


class KitchenCheckIn(BaseModel):
    meal_id: int
    servings: int = 2


class PlanIn(BaseModel):
    date: str
    meal_type: str
    meal_id: Optional[int] = None
    custom_name: str = ""
    locked: bool = False


class HistoryCompleteIn(BaseModel):
    meal_id: int
    meal_type: str = "dinner"
    servings: int = 2
    mode: str = "cooked"  # cooked|ordered
    date: Optional[str] = None
    deduct_inventory: bool = True


class ShoppingGenIn(BaseModel):
    meal_ids: Optional[list[int]] = None
    servings: int = 2
    name: str = "Meal plan groceries"
