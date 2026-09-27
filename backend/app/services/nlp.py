"""Natural-language intent parsing (deterministic). LLM may refine, never replaces safety filters."""
from __future__ import annotations

import re

MOOD_WORDS = {
    "tired": "tired", "exhausted": "tired", "sleepy": "tired", "low energy": "tired",
    "happy": "happy", "celebrat": "happy", "good mood": "happy",
    "stressed": "stressed", "stress": "stressed", "anxious": "stressed", "tension": "stressed",
    "comfort": "comfort", "cozy": "comfort", "homely": "comfort",
    "spicy": "spicy", "masaledar": "spicy", "chatpata": "spicy",
    "light": "light", "healthy": "healthy", "filling": "filling", "heavy": "filling",
    "high-protein": "high-protein", "high protein": "high-protein", "protein": "high-protein",
    "gym": "high-protein", "muscle": "high-protein",
    "cheap": "budget", "budget": "budget", "sasta": "budget", "save": "budget",
    "quick": "quick", "fast": "quick", "hurry": "quick",
}

NEG_RE = re.compile(r"(?:don'?t|do not|no|avoid|without|not)\s+([a-z ]+?)(?:\s+today|\s+for\s+\w+|\s+please|$|,)", re.I)
HAVE_RE = re.compile(r"(?:i have|i'?ve got|have|leftover|left over)\s+([^.,;!?]+)", re.I)
BUDGET_RE_RS = re.compile(r"(?:₹|rs\.?|rupees?)\s*(\d{2,5})", re.I)
BUDGET_RE_WORD = re.compile(r"(?:under|within|budget)\s*(?:₹|rs\.?)?\s*(\d{2,5})", re.I)
TIME_RE = re.compile(r"(\d{1,3})\s*(?:min|mins|minutes)", re.I)
SERV_RE = re.compile(r"(\d)\s*(?:servings?|people|persons?)", re.I)
PROTEIN_RE = re.compile(r"high.?protein|muscle|gym", re.I)


def parse_intent(text: str) -> dict:
    t = (text or "").lower().strip()
    moods = []
    for k, v in MOOD_WORDS.items():
        if k in t and v not in moods:
            moods.append(v)
    neg = []
    for m in NEG_RE.finditer(t):
        chunk = m.group(1).strip()
        for w in re.split(r"\s+and\s+|\s*,\s*|\s+or\s+", chunk):
            w = w.strip(" .!")
            if w and w not in ("to", "cook", "want", "eat", "recommend", "me", "i", "a", "the"):
                neg.append(w)
    have: list[str] = []
    KNOWN = ["rice", "cooked rice", "eggs", "egg", "onion", "onions", "tomato", "tomatoes",
             "paneer", "milk", "capsicum", "potato", "carrot", "bread", "maggi", "chicken",
             "curd", "oats", "peanuts", "peanut", "lemon", "atta", "oil", "soya", "dal",
             "rajma", "chana", "poha", "mushroom", "fish", "butter", "cream"]
    for m in HAVE_RE.finditer(t):
        chunk = m.group(1)
        # first try comma/and/+/& splits, then fall back to known-food token scan
        parts = [p.strip(" .!") for p in re.split(r",|\band\b|\+|&", chunk)]
        for p in parts:
            p = re.sub(r"^(some|only|just|still|leftover|left)\s+", "", p)
            p = re.sub(r"\s+(in the kitchen|in kitchen|at home|with me)$", "", p)
            found = [k for k in KNOWN if k in p]
            if found:
                for f in found:
                    norm = {"eggs": "egg", "onions": "onion", "tomatoes": "tomato",
                            "peanuts": "peanut"}.get(f, f)
                    if norm not in have:
                        have.append(norm)
            elif p and len(p) < 30:
                # single-word leftovers like "rice" survive; multi-word unknowns kept whole
                for w in p.split():
                    w = w.strip(" .!")
                    if w and w not in ("i", "have", "got", "some", "only", "just") and w not in have and len(w) > 2:
                        # keep unknowns too (e.g. "quinoa") so recommender can note them
                        have.append(w)
                        if len(have) >= 8:
                            break
    budget = None
    for rx in (BUDGET_RE_RS, BUDGET_RE_WORD):
        bm = rx.search(t if rx is BUDGET_RE_WORD else text)
        if bm:
            try:
                budget = int(bm.group(1))
                break
            except Exception:
                budget = None
    tm = TIME_RE.search(t)
    max_time = int(tm.group(1)) if tm else None
    sm = SERV_RE.search(t)
    servings = int(sm.group(1)) if sm else None
    no_cook = any(p in t for p in ("don't want to cook", "dont want to cook", "no cooking", "without cooking", "order", "don't feel like cooking"))
    want_cook = any(p in t for p in ("want to cook", "i'll cook", "i will cook", "cook something", "willing to cook"))
    meal_type = None
    for mt in ("breakfast", "lunch", "snacks", "snack", "dinner"):
        if mt in t:
            meal_type = "snacks" if mt == "snack" else mt
    healthy = "healthy" in t or "light" in t or "weight" in t or "diet" in t
    return {
        "moods": moods, "negatives": neg[:5], "have": have[:8],
        "budget": budget, "max_time": max_time, "servings": servings,
        "no_cook": no_cook, "want_cook": want_cook, "meal_type": meal_type,
        "high_protein": bool(PROTEIN_RE.search(t)),
        "healthy": healthy, "raw": text,
    }
