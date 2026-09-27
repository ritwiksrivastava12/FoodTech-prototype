"""AI orchestration layer.

Flow: retrieve structured context (profile, inventory, history, favorites)
  → deterministic math (availability, costs, nutrition)
  → candidate scoring (recommender)
  → LLM for NLU/reasoning/response (optional; rule fallback is fully functional)
  → explainable response with reasons + actions.

LLM providers are swappable via AI_PROVIDER env without changing the API contract.
"""
from __future__ import annotations

import json
import urllib.request

from app.core.config import settings
from app.services import food_math as fm
from app.services.nlp import parse_intent


def llm_complete(system: str, user: str) -> str | None:
    """Returns model text or None if no provider configured. Never raises."""
    try:
        if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({"model": "gpt-4o-mini",
                                 "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": user}],
                                 "max_tokens": 400, "temperature": 0.6}).encode(),
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        if settings.AI_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": "claude-3-5-haiku-latest", "max_tokens": 400,
                                 "system": system,
                                 "messages": [{"role": "user", "content": user}]}).encode(),
                headers={"x-api-key": settings.ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)["content"][0]["text"]
        if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            req = urllib.request.Request(url, data=json.dumps(
                {"system_instruction": {"parts": [{"text": system}]},
                 "contents": [{"parts": [{"text": user}]}]}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    return None


SYSTEM = ("You are FoodMate, a warm, concise food-decision assistant. "
          "Never invent nutrition numbers or live prices. Use only the structured context given. "
          "Respect diet/allergy hard constraints. Keep replies under 120 words unless asked for detail.")


def craft_reply(message: str, top_picks: list[dict], ctx_summary: str) -> str:
    intent = parse_intent(message or "")
    if top_picks:
        names = ", ".join(p["name"] for p in top_picks[:3])
        picks_ctx = "\n".join(
            f"- {p['name']}: {p['time_min']}min, cook ₹{int(p['cost_cook'])}, "
            f"order ₹{int(p['cost_order_low'])}–₹{int(p['cost_order_high'])}, "
            f"{p['protein_g']:.0f}g protein, availability={p['availability'].get('overall')}, "
            f"why: {'; '.join(p['reasons'][:2])}" for p in top_picks[:3])
        fallback = (
            f"Based on {ctx_summary}, my top picks for you are **{names}**.\n\n{picks_ctx}\n\n"
            f"Want me to check your kitchen quantities, compare cook-vs-order, or start Cook Mode?")
    else:
        fallback = (f"I couldn't find a safe match for that within your diet, allergies and '{ctx_summary}'. "
                    f"Try relaxing a filter (budget/time) or tell me what you have at home.")
    llm = llm_complete(SYSTEM, f"User said: {message}\nContext: {ctx_summary}\nCandidates:\n{picks_ctx if top_picks else 'none'}")
    return (llm.strip() if llm and llm.strip() else fallback)


def vision_advice(detected: list[dict]) -> str:
    names = [d.get("label", "") for d in detected if d.get("confidence", 0) >= 0.5]
    uncertain = [d.get("label", "") for d in detected if d.get("confidence", 0) < 0.5]
    msg = ""
    if names:
        msg += f"I can see (with good confidence): **{', '.join(names)}**. "
    if uncertain:
        msg += f"Less sure about: {', '.join(uncertain)} — please confirm. "
    if not detected:
        msg += "I couldn't confidently identify ingredients — try better lighting or list them. "
    msg += "Tell me your mood/budget/time and I'll suggest what to cook."
    return msg
