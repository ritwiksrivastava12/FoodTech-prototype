"""Business-logic tests: scaling, availability, shopping, repetition, cost, nutrition, diet, recommender."""
from app.services import food_math as fm
from app.services.nlp import parse_intent
from app.services.recommender import recommend


class M:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def meal(**kw):
    base = dict(id=1, name="Egg Fried Rice", category="dinner", cuisine="indo-chinese",
                diet="eggetarian", description="", image_emoji="🍳", image_url="",
                time_min=15, difficulty="easy", servings_default=2, calories=520,
                protein_g=19, carbs_g=68, fat_g=16, fiber_g=4, cost_cook=65,
                cost_order_low=149, cost_order_high=189, rating=4.5,
                ingredients=[{"name": "Paneer", "qty": 200, "unit": "g"},
                             {"name": "Onion", "qty": 100, "unit": "g"}],
                steps=[], mood_tags=["tired"], tags=[])
    base.update(kw)
    return M(**base)


def test_serving_scaling_2_to_5():
    ings = [{"name": "Paneer", "qty": 200, "unit": "g"}, {"name": "Onion", "qty": 100, "unit": "g"},
            {"name": "Oil", "qty": 10, "unit": "ml"}]
    out = fm.scale_ingredients(ings, 2, 5)
    assert out[0]["_base_qty"] == 500
    assert out[1]["_base_qty"] == 250
    assert out[2]["_base_qty"] == 25


def test_inventory_quantity_aware():
    req = [{"name": "Paneer", "qty": 200, "unit": "g"}, {"name": "Onion", "qty": 100, "unit": "g"},
           {"name": "Capsicum", "qty": 50, "unit": "g"}]
    inv = {"paneer": {"qty_base": 200, "unit_kind": "g"},
           "onion": {"qty_base": 50, "unit_kind": "g"}}
    c = fm.check_availability(req, inv)
    assert [i["status"] for i in c["items"]] == ["available", "low", "missing"]
    assert c["overall"] == "partial"
    miss = fm.missing_to_shopping(c)
    assert len(miss) == 2


def test_shopping_skips_sufficient():
    req = [{"name": "Rice", "qty": 200, "unit": "g"}]
    inv = {"rice": {"qty_base": 2000, "unit_kind": "g"}}
    c = fm.check_availability(req, inv)
    assert fm.missing_to_shopping(c) == []


def test_repetition_detection():
    ings = [{"name": "Paneer", "qty": 200, "unit": "g"}]
    h = [{"meal_name": "Paneer Bhurji"}]
    assert fm.repetition_blocked("Paneer Bhurji", ings, h, "no-same-day")
    assert fm.repetition_blocked("Paneer Butter Masala", ings, h, "avoid-2-days")
    assert fm.repetition_blocked("Egg Fried Rice", [{"name": "Eggs", "qty": 2, "unit": "pcs"}], h, "no-same-day") is None


def test_cost_nutrition_scaling():
    assert fm.scale_cost(65, 2, 4) == 130
    n = fm.scale_nutrition({"calories": 500, "protein_g": 20, "carbs_g": 60, "fat_g": 15, "fiber_g": 5}, 2, 4)
    assert n["calories"] == 1000 and n["protein_g"] == 40


def test_diet_allergy_hard_filters():
    ms = [meal(id=1, name="Chicken Curry", diet="non-veg"), meal(id=2, name="Dal Rice", diet="veg")]
    ctx = {"profile": {"diet": "vegetarian", "allergies": [], "disliked": [], "repetition_rule": "allow"},
           "intent": {"moods": [], "negatives": [], "have": [], "budget": None, "max_time": None,
                      "high_protein": False}, "history": [], "availability": {}, "favorite_ids": set()}
    out = recommend(ms, ctx)
    assert [r["name"] for r in out] == ["Dal Rice"]
    ms2 = [meal(id=3, name="Peanut Poha", diet="veg", ingredients=[{"name": "Peanuts", "qty": 30, "unit": "g"}])]
    ctx["profile"]["allergies"] = ["peanut"]
    assert recommend(ms2, ctx) == []


def test_negative_preference_respected():
    ms = [meal(id=1, name="Paneer Bhurji"), meal(id=2, name="Egg Fried Rice", mood_tags=["tired"])]
    ctx = {"profile": {"diet": "", "allergies": [], "disliked": [], "repetition_rule": "allow"},
           "intent": {"moods": ["tired"], "negatives": ["paneer"], "have": [], "budget": None,
                      "max_time": None, "high_protein": False},
           "history": [], "availability": {}, "favorite_ids": set()}
    out = recommend(ms, ctx)
    assert all("paneer" not in r["name"].lower() for r in out)


def test_nlp_parses_demo_journey():
    it = parse_intent("tired, spicy, high protein, under ₹100, 20 min, I have rice eggs onions, no paneer today")
    assert "tired" in it["moods"] and "spicy" in it["moods"]
    assert it["budget"] == 100
    assert it["max_time"] == 20
    assert any("paneer" in n for n in it["negatives"])
    assert it["high_protein"]
