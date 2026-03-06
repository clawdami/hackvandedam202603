#!/usr/bin/env python3
"""
🥙 Meatball Lunch Agent — THE MEATBALL
Super Modern Lunch Dashboard voor de Lunch 🍽️
"""

import json
import random
import threading
from datetime import date, datetime

# ── Constants ────────────────────────────────────────────────────────────────

BUDGET_CAP    = 120.00   # weekly cap (€)
SPAARBOLL_PCT = 1.23     # savings interest rate (%)

WEEKDAYS = ["MA", "DI", "WO", "DO", "VR"]

# ── State (in-memory) ────────────────────────────────────────────────────────

_lock = threading.Lock()

_luncher_count = 12

# Agenda: {name: {day: bool}}
_agenda: dict = {
    "Niels": {"MA": True,  "DI": True,  "WO": True,  "DO": True,  "VR": True},
    "Phil":  {"MA": True,  "DI": True,  "WO": False, "DO": True,  "VR": False},
    "Euan":  {"MA": False, "DI": True,  "WO": True,  "DO": False, "VR": True},
    "Jonathan": {"MA": True, "DI": False, "WO": True, "DO": True, "VR": False},
}

# Inventory: qty stored as fractions (use float)
_inventory: list = [
    {"id": 1,  "name": "Kaas",          "emoji": "🧀", "qty": 0.5,  "unit": "kg",  "min": 0.5},
    {"id": 2,  "name": "Grillworst",    "emoji": "🌭", "qty": 1.5,  "unit": "pak", "min": 1.0},
    {"id": 3,  "name": "Gehaktballen",  "emoji": "🍖", "qty": 20,   "unit": "st",  "min": 10},
    {"id": 4,  "name": "Tomatensaus",   "emoji": "🍅", "qty": 3,    "unit": "pot", "min": 2},
    {"id": 5,  "name": "Spaghetti",     "emoji": "🍝", "qty": 4,    "unit": "pak", "min": 3},
    {"id": 6,  "name": "Uitjes",        "emoji": "🧅", "qty": 6,    "unit": "st",  "min": 4},
    {"id": 7,  "name": "Knoflook",      "emoji": "🧄", "qty": 3,    "unit": "bol", "min": 2},
    {"id": 8,  "name": "Olijfolie",     "emoji": "🫙", "qty": 1,    "unit": "fl",  "min": 1},
    {"id": 9,  "name": "Brood",         "emoji": "🍞", "qty": 2,    "unit": "st",  "min": 2},
    {"id": 10, "name": "Parmezaan",     "emoji": "🧀", "qty": 0.5,  "unit": "blok","min": 1.0},
]

_budget_spent = 87.50
_spaarball    = 23.00    # accumulated savings
_spaarball_earnings = round(_spaarball * SPAARBOLL_PCT / 100, 2)

_order_history: list = []
_training_score = 0

# Suggestion poll
SUGGESTIONS = [
    {"dish": "Spaghetti & Gehaktballen", "emoji": "🍝", "prep": "30 min"},
    {"dish": "Caprese Salade",           "emoji": "🥗", "prep": "10 min"},
    {"dish": "Bruschetta al Pomodoro",   "emoji": "🍅", "prep": "15 min"},
    {"dish": "Pizza Margherita",         "emoji": "🍕", "prep": "25 min"},
    {"dish": "Penne all'Arrabbiata",     "emoji": "🌶️", "prep": "20 min"},
    {"dish": "Risotto ai Funghi",        "emoji": "🍚", "prep": "40 min"},
    {"dish": "Minestrone Soep",          "emoji": "🥣", "prep": "35 min"},
    {"dish": "Tiramisu (dessert!)",      "emoji": "☕", "prep": "45 min"},
]
_poll_votes: dict = {}   # dish → count

TRAINING_TIPS = [
    {"id": 1, "tip": "Altijd gehaktballen draaien met vochtige handen — plakken ze niet vast.", "emoji": "💧"},
    {"id": 2, "tip": "Saus minimaal 30 minuten laten sudderen voor de beste smaak.",            "emoji": "⏱️"},
    {"id": 3, "tip": "Pasta koken in zwaar gezouten water — het verschil is enorm.",            "emoji": "🧂"},
    {"id": 4, "tip": "Bewaar altijd wat pastawater — het bindt de saus als magie.",             "emoji": "✨"},
    {"id": 5, "tip": "Parmezaan pas op het allerlaatste moment raspen.",                        "emoji": "🧀"},
    {"id": 6, "tip": "Ui glazig fruiten op laag vuur — minimaal 10 minuten geduld.",           "emoji": "🧅"},
    {"id": 7, "tip": "Knoflook nooit verbranden: bitter en vreselijk.",                        "emoji": "🧄"},
    {"id": 8, "tip": "Restjes saus invriezen — geweldig voor de volgende week.",               "emoji": "❄️"},
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def current_week() -> int:
    return date.today().isocalendar()[1]

def current_day() -> str:
    idx = date.today().weekday()   # 0=Mon
    return WEEKDAYS[idx] if idx < 5 else "VR"

def weekly_suggestion() -> dict:
    idx = current_week() % len(SUGGESTIONS)
    s = SUGGESTIONS[idx].copy()
    s["votes"] = _poll_votes.get(s["dish"], 0)
    # full poll
    s["poll"] = [{"dish": x["dish"], "emoji": x["emoji"],
                  "votes": _poll_votes.get(x["dish"], 0)} for x in SUGGESTIONS]
    return s

def low_stock_items() -> list:
    return [i for i in _inventory if i["qty"] < i["min"]]

def picnic_list() -> list:
    """Items to order + suggested quantity to bring back to 2× min."""
    items = []
    for i in _inventory:
        if i["qty"] < i["min"]:
            needed = round(i["min"] * 2 - i["qty"], 2)
            items.append({"name": i["name"], "emoji": i["emoji"],
                          "needed": needed, "unit": i["unit"]})
    return items

def budget_status() -> dict:
    remaining = round(BUDGET_CAP - _budget_spent, 2)
    pct_used  = round((_budget_spent / BUDGET_CAP) * 100, 1)
    surplus   = max(0.0, remaining)
    return {
        "cap":           BUDGET_CAP,
        "spent":         _budget_spent,
        "remaining":     remaining,
        "pct_used":      pct_used,
        "spaarball":     round(_spaarball, 2),
        "spaarball_pct": SPAARBOLL_PCT,
        "spaarball_earn": round(_spaarball * SPAARBOLL_PCT / 100, 2),
        "surplus":       surplus,
        "status":        "⚠️ Budget bijna op!" if pct_used >= 80 else "✅ Budget OK",
    }

def snapshot() -> dict:
    with _lock:
        return {
            "lunchers":       _luncher_count,
            "agenda":         _agenda,
            "weekdays":       WEEKDAYS,
            "today":          current_day(),
            "suggestion":     weekly_suggestion(),
            "inventory":      list(_inventory),
            "low_stock":      low_stock_items(),
            "picnic_list":    picnic_list(),
            "budget":         budget_status(),
            "order_history":  list(_order_history[-5:]),
            "training_tips":  TRAINING_TIPS,
            "training_score": _training_score,
            "week":           current_week(),
            "timestamp":      datetime.now().strftime("%H:%M"),
        }

# ── Actions ──────────────────────────────────────────────────────────────────

def set_lunchers(n: int) -> dict:
    global _luncher_count
    with _lock:
        _luncher_count = max(0, int(n))
    return {"ok": True, "lunchers": _luncher_count}

def toggle_agenda(person: str, day: str) -> dict:
    with _lock:
        if person not in _agenda:
            _agenda[person] = {d: False for d in WEEKDAYS}
        _agenda[person][day] = not _agenda[person].get(day, False)
    return {"ok": True, "agenda": _agenda}

def vote_poll(dish: str) -> dict:
    with _lock:
        _poll_votes[dish] = _poll_votes.get(dish, 0) + 1
    return {"ok": True, "dish": dish, "votes": _poll_votes[dish]}

def scan_inventory() -> dict:
    with _lock:
        for item in _inventory:
            delta = random.uniform(-0.5, 0.5)
            item["qty"] = round(max(0, item["qty"] + delta), 2)
    return {"ok": True, "message": "📸 Voorraad gescand!", "inventory": list(_inventory)}

def order_picnic(items: list | None = None) -> dict:
    global _budget_spent, _spaarball
    with _lock:
        to_order = items or [i["name"] for i in low_stock_items()]
        if not to_order:
            return {"ok": False, "message": "Niets te bestellen — voorraad is prima!"}

        cost = round(sum(random.uniform(2, 6) for _ in to_order), 2)
        _budget_spent = round(_budget_spent + cost, 2)

        # Replenish
        for item in _inventory:
            if item["name"] in to_order:
                item["qty"] = round(item["qty"] + item["min"] * 2, 2)

        # Budget surplus → SpaarBall
        surplus = max(0, BUDGET_CAP - _budget_spent)
        if surplus > 0:
            _spaarball = round(_spaarball + surplus * 0.1, 2)

        entry = {"time": datetime.now().strftime("%H:%M"), "items": to_order, "cost": cost}
        _order_history.append(entry)

    return {
        "ok":      True,
        "message": f"🛒 Picnic bestelling geplaatst! ({len(to_order)} items, €{cost:.2f})",
        "items":   to_order,
        "cost":    cost,
        "picnic_url": f"https://picnic.app/nl/winkelmandje?search={'+'.join(to_order[:3])}",
    }

def answer_training(tip_id: int) -> dict:
    global _training_score
    with _lock:
        _training_score += 10
    return {"ok": True, "score": _training_score, "message": "✅ Goed gedaan! +10 punten"}
