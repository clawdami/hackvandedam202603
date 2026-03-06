#!/usr/bin/env python3
"""
🥙 Meatball Lunch Agent
Super Modern Lunch Dashboard voor de Lunch 🍽️

Features:
  - Aantal lunchers achterhalen (luncher counter)
  - Wekelijkse suggestie werknemer (weekly employee suggestion)
  - Budget cap + spaarplan (sauzen, uitjes, etc.)
  - Voorraad overzicht (inventory overview)
  - Foto → auto inventory (simulated)
  - Auto bestellen Picnic (mock Picnic order)
  - Training tool
"""

import json
import random
import threading
from datetime import date, datetime

# ── State (in-memory, shared across requests) ───────────────────────────────

_lock            = threading.Lock()
_luncher_count   = 12
_inventory: list = [
    {"id": 1, "name": "Gehaktballen",    "emoji": "🍖", "qty": 24, "unit": "st",  "min": 10},
    {"id": 2, "name": "Tomatensaus",     "emoji": "🍅", "qty": 3,  "unit": "pot", "min": 2},
    {"id": 3, "name": "Spaghetti",       "emoji": "🍝", "qty": 6,  "unit": "pak", "min": 3},
    {"id": 4, "name": "Parmezaan",       "emoji": "🧀", "qty": 1,  "unit": "blok","min": 2},
    {"id": 5, "name": "Uitjes",          "emoji": "🧅", "qty": 8,  "unit": "st",  "min": 5},
    {"id": 6, "name": "Knoflook",        "emoji": "🧄", "qty": 4,  "unit": "bol", "min": 2},
    {"id": 7, "name": "Olijfolie",       "emoji": "🫙", "qty": 2,  "unit": "fl",  "min": 1},
    {"id": 8, "name": "Brood",           "emoji": "🍞", "qty": 2,  "unit": "st",  "min": 2},
]

_budget_cap  = 150.00   # weekly budget in euros
_budget_spent = 87.50
_savings_pot  = 23.00   # spaarplan: leftovers saved for sauzen/uitjes etc.

_order_history: list = []
_training_score = 0

# ── Weekly suggestions ──────────────────────────────────────────────────────

SUGGESTIONS = [
    {"week": 1, "dish": "Spaghetti & Gehaktballen", "emoji": "🍝", "prep": "30 min", "votes": 0},
    {"week": 2, "dish": "Caprese Salade",            "emoji": "🥗", "prep": "10 min", "votes": 0},
    {"week": 3, "dish": "Bruschetta al Pomodoro",    "emoji": "🍅", "prep": "15 min", "votes": 0},
    {"week": 4, "dish": "Risotto ai Funghi",         "emoji": "🍚", "prep": "40 min", "votes": 0},
    {"week": 5, "dish": "Pizza Margherita",          "emoji": "🍕", "prep": "25 min", "votes": 0},
    {"week": 6, "dish": "Minestrone Soep",           "emoji": "🥣", "prep": "35 min", "votes": 0},
    {"week": 7, "dish": "Penne all'Arrabbiata",      "emoji": "🌶️", "prep": "20 min", "votes": 0},
    {"week": 8, "dish": "Tiramisu (dessert!)",       "emoji": "☕", "prep": "45 min", "votes": 0},
]

_suggestion_votes: dict = {}  # dish -> vote count

# ── Training tips ────────────────────────────────────────────────────────────

TRAINING_TIPS = [
    {"id": 1, "tip": "Altijd gehaktballen draaien met vochtige handen — plakken ze niet vast.",    "emoji": "💧"},
    {"id": 2, "tip": "Saus minimaal 30 minuten laten sudderen voor de beste smaak.",               "emoji": "⏱️"},
    {"id": 3, "tip": "Pasta koken in zwaar gezouten water — het verschil is enorm.",               "emoji": "🧂"},
    {"id": 4, "tip": "Bewaar altijd wat pastawater — het bindt de saus als magie.",                "emoji": "✨"},
    {"id": 5, "tip": "Parmezaan pas op het allerlaatste moment raspen.",                           "emoji": "🧀"},
    {"id": 6, "tip": "Ui glazig fruiten op laag vuur — minimaal 10 minuten geduld.",               "emoji": "🧅"},
    {"id": 7, "tip": "Knoflook nooit verbranden: bitter en vreselijk.",                            "emoji": "🧄"},
    {"id": 8, "tip": "Restjes saus invriezen — geweldig voor de volgende week.",                   "emoji": "❄️"},
]

# ── Helpers ─────────────────────────────────────────────────────────────────

def current_week() -> int:
    return date.today().isocalendar()[1]

def weekly_suggestion() -> dict:
    idx = current_week() % len(SUGGESTIONS)
    s   = SUGGESTIONS[idx].copy()
    s["votes"] = _suggestion_votes.get(s["dish"], 0)
    return s

def low_stock_items() -> list:
    return [i for i in _inventory if i["qty"] < i["min"]]

def budget_status() -> dict:
    remaining = _budget_cap - _budget_spent
    pct_used  = round((_budget_spent / _budget_cap) * 100)
    return {
        "cap":       _budget_cap,
        "spent":     _budget_spent,
        "remaining": remaining,
        "pct_used":  pct_used,
        "savings":   _savings_pot,
        "status":    "⚠️ Budget bijna op!" if pct_used >= 80 else "✅ Budget OK",
    }

def snapshot() -> dict:
    """Return full dashboard state as a JSON-serialisable dict."""
    with _lock:
        return {
            "lunchers":        _luncher_count,
            "suggestion":      weekly_suggestion(),
            "inventory":       list(_inventory),
            "low_stock":       low_stock_items(),
            "budget":          budget_status(),
            "order_history":   list(_order_history[-5:]),
            "training_tips":   TRAINING_TIPS,
            "training_score":  _training_score,
            "week":            current_week(),
            "timestamp":       datetime.now().strftime("%H:%M"),
        }


# ── Actions (called by HTTP handler) ────────────────────────────────────────

def set_lunchers(n: int) -> dict:
    global _luncher_count
    with _lock:
        _luncher_count = max(0, int(n))
    return {"ok": True, "lunchers": _luncher_count}


def vote_suggestion(dish: str) -> dict:
    with _lock:
        _suggestion_votes[dish] = _suggestion_votes.get(dish, 0) + 1
    return {"ok": True, "votes": _suggestion_votes[dish]}


def scan_inventory() -> dict:
    """Simulate a photo scan: randomly adjust quantities ±1."""
    with _lock:
        for item in _inventory:
            delta = random.randint(-1, 1)
            item["qty"] = max(0, item["qty"] + delta)
    return {"ok": True, "message": "📸 Voorraad gescand!", "inventory": list(_inventory)}


def order_picnic(items: list) -> dict:
    """Simulate placing a Picnic order for low-stock items."""
    global _budget_spent, _savings_pot
    if not items:
        items = [i["name"] for i in low_stock_items()]
    if not items:
        return {"ok": False, "message": "Niets te bestellen — voorraad is prima!"}

    # Fake cost: €3–7 per item
    cost = round(sum(random.uniform(3, 7) for _ in items), 2)
    with _lock:
        _budget_spent = round(_budget_spent + cost, 2)
        # Replenish inventory
        for item in _inventory:
            if item["name"] in items:
                item["qty"] += random.randint(3, 8)
        entry = {
            "time":  datetime.now().strftime("%H:%M"),
            "items": items,
            "cost":  cost,
        }
        _order_history.append(entry)

    return {
        "ok":      True,
        "message": f"🛒 Picnic bestelling geplaatst! ({len(items)} items, €{cost:.2f})",
        "items":   items,
        "cost":    cost,
    }


def answer_training(tip_id: int) -> dict:
    global _training_score
    with _lock:
        _training_score += 10
    return {"ok": True, "score": _training_score, "message": "✅ Goed gedaan! +10 punten"}
