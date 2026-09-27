"""Tests for OpenRouter provider wiring + user-context builder (HTTP mocked, no key needed)."""
import io
import json

from app.api.ai import allow_request
from app.core.config import settings
from app.services import ai_orchestrator as aio


class FakeResp:
    def __init__(self, payload):
        self._buf = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self._buf

    def __exit__(self, *a):
        return False


def test_openrouter_request_shape(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_MODEL", "")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        seen["body"] = json.loads(req.data.decode())
        seen["auth"] = req.headers.get("Authorization")
        return FakeResp({"choices": [{"message": {"content": "Hello from Nemotron"}}]})

    monkeypatch.setattr(aio.urllib.request, "urlopen", fake_urlopen)
    out = aio.llm_complete("sys", "hi")
    assert out == "Hello from Nemotron"
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["body"]["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert seen["auth"] == "Bearer test-key"


def test_no_key_falls_back_to_none(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    assert aio.llm_complete("sys", "hi") is None


def test_user_context_contains_profile_and_guardrails():
    ctx = aio.build_user_context(
        {"name": "Aarav", "diet": "eggetarian", "allergies": ["peanut"],
         "disliked": ["paneer"], "favorites_food": ["maggi"],
         "cuisines": ["indo-chinese"], "budget_per_meal": 100,
         "equipment": ["pan"], "cooking_ability": "beginner",
         "nutrition_goal": "high-protein", "fitness_goal": "muscle-gain",
         "calorie_target": 2200, "protein_target": 90},
        [{"display": "Eggs", "qty": 6, "unit": "pcs"}],
        [{"meal_name": "Paneer Bhurji"}],
        ["Egg Fried Rice"], "dinner",
        [{"role": "user", "content": "hi"}])
    for token in ("Aarav", "eggetarian", "peanut", "paneer", "Eggs",
                  "Paneer Bhurji", "Egg Fried Rice", "dinner", "2200"):
        assert token in ctx


def test_system_prompt_is_scoped():
    for token in ("ONLY job", "outside food", "politely decline", "Never reveal",
                  "Do not diagnose", "Use ONLY the numbers", "never claim you placed an order"):
        assert token in aio.SYSTEM


def test_rate_limit_blocks_after_quota(monkeypatch):
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_PER_HOUR", 2)
    uid = 999999
    assert allow_request(uid) is True
    assert allow_request(uid) is True
    assert allow_request(uid) is False
