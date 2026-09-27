"""Integration adapters — swap demo providers for real APIs without touching core logic."""
from __future__ import annotations

from app.data.seed_data import GROCERY_DEMO, RESTAURANT_DEMO


class GroceryAdapter:
    name = "demo-grocery"

    def compare(self, query: str = "") -> list[dict]:
        q = (query or "").lower().strip()
        items = [dict(g, demo=True) for g in GROCERY_DEMO]
        if not q:
            return items[:8]
        scored = [g for g in items if q in g["name"].lower() or q in g.get("brand", "").lower()]
        return (scored or items)[:10]

    def redirect_url(self, platform: str, product: str) -> str:
        return f"https://example.com/grocery/{platform.lower().replace(' ','-')}?q={product.replace(' ','+')}"


class DeliveryAdapter:
    name = "demo-delivery"

    def compare(self, dish: str = "") -> list[dict]:
        q = (dish or "").lower().strip()
        rows = []
        for r in RESTAURANT_DEMO:
            total = r["price"] + r["delivery_fee"] + r["taxes"]
            rows.append({**r, "total": total, "demo": True})
        if not q:
            return rows
        matched = [r for r in rows if q in r["dish"].lower() or q in r["restaurant"].lower()]
        return matched or rows

    def redirect_url(self, platform: str, dish: str) -> str:
        return f"https://example.com/food/{platform.lower().replace(' ','-')}?dish={dish.replace(' ','+')}"


class LLMAdapter:
    """Provider switch lives in ai_orchestrator.llm_complete; this exposes status."""
    @staticmethod
    def status() -> dict:
        from app.core.config import settings
        configured = {"openai": bool(settings.OPENAI_API_KEY), "anthropic": bool(settings.ANTHROPIC_API_KEY),
                      "gemini": bool(settings.GEMINI_API_KEY), "rule": True}
        return {"active": settings.AI_PROVIDER, "configured": configured, "demo": settings.DEMO_MODE}


grocery = GroceryAdapter()
delivery = DeliveryAdapter()
