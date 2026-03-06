#!/usr/bin/env python3
"""
🥙 Meatball Lunch Agent — THE MEATBALL (Deluxe Edition)
Super Modern Lunch Dashboard voor de Lunch 🍽️
"""

import json
import random
import threading
from datetime import date, datetime

# ── Constants ────────────────────────────────────────────────────────────────

BUDGET_CAP    = 120.00
SPAARBOLL_PCT = 1.23
WEEKDAYS      = ["MA", "DI", "WO", "DO", "VR"]

# ── State ────────────────────────────────────────────────────────────────────

_lock = threading.Lock()

_luncher_count = 12

_agenda: dict = {
    "Niels":    {"MA": True,  "DI": True,  "WO": True,  "DO": True,  "VR": True},
    "Phil":     {"MA": True,  "DI": True,  "WO": False, "DO": True,  "VR": False},
    "Euan":     {"MA": False, "DI": True,  "WO": True,  "DO": False, "VR": True},
    "Jonathan": {"MA": True,  "DI": False, "WO": True,  "DO": True,  "VR": False},
}

_inventory: list = [
    {"id": 1,  "name": "Kaas",         "emoji": "🧀", "qty": 0.5,  "unit": "kg",  "min": 0.5},
    {"id": 2,  "name": "Grillworst",   "emoji": "🌭", "qty": 1.5,  "unit": "pak", "min": 1.0},
    {"id": 3,  "name": "Gehaktballen", "emoji": "🍖", "qty": 20,   "unit": "st",  "min": 10},
    {"id": 4,  "name": "Tomatensaus",  "emoji": "🍅", "qty": 3,    "unit": "pot", "min": 2},
    {"id": 5,  "name": "Spaghetti",    "emoji": "🍝", "qty": 4,    "unit": "pak", "min": 3},
    {"id": 6,  "name": "Uitjes",       "emoji": "🧅", "qty": 6,    "unit": "st",  "min": 4},
    {"id": 7,  "name": "Knoflook",     "emoji": "🧄", "qty": 3,    "unit": "bol", "min": 2},
    {"id": 8,  "name": "Olijfolie",    "emoji": "🫙", "qty": 1,    "unit": "fl",  "min": 1},
    {"id": 9,  "name": "Brood",        "emoji": "🍞", "qty": 2,    "unit": "st",  "min": 2},
    {"id": 10, "name": "Parmezaan",    "emoji": "🧀", "qty": 0.5,  "unit": "blok","min": 1.0},
]

_budget_spent = 87.50
_spaarball    = 23.00

_order_history: list = []
_training_score = 0

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
_poll_votes: dict = {}

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

# ── NEW: Product Requests ─────────────────────────────────────────────────────

_product_requests: list = []   # [{"id", "name", "emoji", "requester", "votes", "time", "status"}]
_request_id_counter = 1

PRODUCT_EMOJIS = {
    "kaas": "🧀", "koffie": "☕", "thee": "🍵", "koek": "🍪", "chips": "🥔",
    "pizza": "🍕", "bier": "🍺", "cola": "🥤", "brood": "🍞", "vlees": "🥩",
    "vis": "🐟", "groente": "🥦", "fruit": "🍎", "saus": "🍅", "pasta": "🍝",
    "default": "📦",
}

def _product_emoji(name: str) -> str:
    for kw, em in PRODUCT_EMOJIS.items():
        if kw in name.lower():
            return em
    return PRODUCT_EMOJIS["default"]

# ── NEW: Complaint Box ────────────────────────────────────────────────────────

_complaints: list = []
COMPLAINT_AUTO_RESPONSES = [
    "😤 Bericht ontvangen. Nonna is op de hoogte gesteld.",
    "🍝 Klacht doorgegeven aan het pastateam. Ze doen hun best.",
    "👵 Nonna zegt: 'Eet eerst, klaag daarna.'",
    "📋 Klacht geregistreerd. Prioriteit: laag. Pasta: hoog.",
    "🥺 Au. Dat doet pijn. Maar we gaan door.",
    "🤌 De klacht is ontvangen en zal worden genegeerd. Bedankt.",
    "🔥 Doorgestuurd naar de CEO. De CEO is een gehaktbal.",
    "😇 Wij waarderen uw feedback. Het maakt ons meatballs niet beter, maar toch.",
]

# ── NEW: Sfeer-o-meter (mood tracker) ────────────────────────────────────────

_mood_votes: dict = {}   # person → mood (1-5)
MOOD_LABELS = {
    1: ("💀", "Vreselijk"),
    2: ("😞", "Slecht"),
    3: ("😐", "Meh"),
    4: ("😊", "Goed"),
    5: ("🔥", "GEWELDIG"),
}

# ── NEW: Oracle ───────────────────────────────────────────────────────────────

ORACLE_ANSWERS = [
    ("JA", "🔮 De gehaktballen hebben gesproken. Het antwoord is: JA."),
    ("NEE", "🔮 Nonna schudde haar hoofd. Het antwoord is: NEE."),
    ("MISSCHIEN", "🔮 De pasta trilt onzeker. Misschien? Voeg meer kaas toe voor duidelijkheid."),
    ("ZEKER", "🔮 De saus is helder. ABSOLUUT JA. Geen twijfel."),
    ("ABSOLUUT NIET", "🔮 De gehaktbal rolde weg. ABSOLUUT NIET. Schaam je."),
    ("VRAAG LATER OPNIEUW", "🔮 De pasta is nog niet gaar. Vraag over 5 minuten opnieuw."),
    ("ALLEEN ALS JE BETAALT", "🔮 De Oracle zegt: Ja, maar alleen als jij de lunch betaalt."),
    ("DE STERREN ZEGGEN NEE", "🔮 De sterren staan ongunstig. En ook je pasta staat aangebrand."),
    ("JA MAAR NIETS ZEGGEN", "🔮 Ja. Maar zeg het tegen niemand. Zeker niet tegen Niels."),
    ("ONMOGELIJK", "🔮 Onmogelijk. Net zo onmogelijk als spaghetti eten zonder besmetting."),
]

# ── NEW: Slot Machine dishes ──────────────────────────────────────────────────

SLOT_ITEMS = ["🍝","🍕","🌭","🧆","🥙","🍖","🥗","🍔","🌮","🍛","🍣","🥩","🥘","🫕","🍱"]
SLOT_DISHES = [
    "Spaghetti & Gehaktballen", "Pizza Margherita", "Grillworst & Brood",
    "Falafel Bowl", "Döner Wrap", "Spare Ribs", "Caprese Salade",
    "Cheeseburger", "Taco Tuesday", "Curry van de Chef",
    "Sushi (budget: onmogelijk)", "Côte de Boeuf", "Minestrone",
    "Hotpot Surprise", "Bento Box",
]

# ── NEW: Nonna Alerts ─────────────────────────────────────────────────────────

def nonna_alert(budget_pct: float) -> dict | None:
    if budget_pct < 20:
        return {"level": "🚨 CRISIS", "msg": "👵 'MADONNA MIA! Het geld is bijna op! Geen gehaktballen meer! We eten water met zout!'", "color": "#C0392B"}
    if budget_pct < 40:
        return {"level": "⚠️ WAARSCHUWING", "msg": "👵 'Let op — het budget raakt op. Misschien iets minder parmezaan deze week?'", "color": "#E67E22"}
    if budget_pct < 10:
        return {"level": "☠️ NOODTOESTAND", "msg": "👵 'NIENTE SOLDI! Verkoop de tafel! Verkoop de stoelen! VERKOOP NIELS!'", "color": "#8B0000"}
    return None

# ── NEW: Leaderboard ──────────────────────────────────────────────────────────

def leaderboard() -> list:
    """Count total ✅ days per person in the agenda."""
    scores = []
    for name, days in _agenda.items():
        count = sum(1 for v in days.values() if v)
        scores.append({"name": name, "days": count, "emoji": "🏆" if count == max(sum(1 for v in d.values() if v) for d in _agenda.values()) else "👤"})
    return sorted(scores, key=lambda x: x["days"], reverse=True)

# ── Existing helpers ──────────────────────────────────────────────────────────

def current_week() -> int:
    return date.today().isocalendar()[1]

def current_day() -> str:
    idx = date.today().weekday()
    return WEEKDAYS[idx] if idx < 5 else "VR"

def weekly_suggestion() -> dict:
    idx = current_week() % len(SUGGESTIONS)
    s = SUGGESTIONS[idx].copy()
    s["votes"] = _poll_votes.get(s["dish"], 0)
    s["poll"]  = [{"dish": x["dish"], "emoji": x["emoji"],
                   "votes": _poll_votes.get(x["dish"], 0)} for x in SUGGESTIONS]
    return s

def low_stock_items() -> list:
    return [i for i in _inventory if i["qty"] < i["min"]]

def picnic_list() -> list:
    items = []
    for i in _inventory:
        if i["qty"] < i["min"]:
            needed = round(i["min"] * 2 - i["qty"], 2)
            items.append({"name": i["name"], "emoji": i["emoji"], "needed": needed, "unit": i["unit"]})
    return items

def budget_status() -> dict:
    remaining = round(BUDGET_CAP - _budget_spent, 2)
    pct_used  = round((_budget_spent / BUDGET_CAP) * 100, 1)
    remaining_pct = round(100 - pct_used, 1)
    return {
        "cap":           BUDGET_CAP,
        "spent":         _budget_spent,
        "remaining":     remaining,
        "pct_used":      pct_used,
        "spaarball":     round(_spaarball, 2),
        "spaarball_pct": SPAARBOLL_PCT,
        "spaarball_earn": round(_spaarball * SPAARBOLL_PCT / 100, 2),
        "status":        "⚠️ Budget bijna op!" if pct_used >= 80 else "✅ Budget OK",
        "nonna_alert":   nonna_alert(remaining_pct),
    }

def avg_mood() -> dict:
    if not _mood_votes:
        return {"avg": 0, "label": "Nog geen stemmen", "emoji": "🤔", "votes": {}}
    avg = sum(_mood_votes.values()) / len(_mood_votes)
    lvl = MOOD_LABELS[round(avg)] if round(avg) in MOOD_LABELS else MOOD_LABELS[3]
    return {
        "avg":    round(avg, 1),
        "emoji":  lvl[0],
        "label":  lvl[1],
        "votes":  {k: {"score": v, "emoji": MOOD_LABELS[v][0], "label": MOOD_LABELS[v][1]}
                   for k, v in _mood_votes.items()},
    }

def snapshot() -> dict:
    with _lock:
        return {
            "lunchers":        _luncher_count,
            "agenda":          _agenda,
            "weekdays":        WEEKDAYS,
            "today":           current_day(),
            "suggestion":      weekly_suggestion(),
            "inventory":       list(_inventory),
            "low_stock":       low_stock_items(),
            "picnic_list":     picnic_list(),
            "budget":          budget_status(),
            "order_history":   list(_order_history[-5:]),
            "training_tips":   TRAINING_TIPS,
            "training_score":  _training_score,
            "week":            current_week(),
            "timestamp":       datetime.now().strftime("%H:%M"),
            "product_requests": list(_product_requests),
            "complaints":      list(_complaints[-10:]),
            "mood":            avg_mood(),
            "leaderboard":     leaderboard(),
        }

# ── Actions ───────────────────────────────────────────────────────────────────

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
        for item in _inventory:
            if item["name"] in to_order:
                item["qty"] = round(item["qty"] + item["min"] * 2, 2)
        surplus = max(0, BUDGET_CAP - _budget_spent)
        if surplus > 0:
            _spaarball = round(_spaarball + surplus * 0.1, 2)
        entry = {"time": datetime.now().strftime("%H:%M"), "items": to_order, "cost": cost}
        _order_history.append(entry)
    return {
        "ok":         True,
        "message":    f"🛒 Picnic bestelling geplaatst! ({len(to_order)} items, €{cost:.2f})",
        "items":      to_order,
        "cost":       cost,
        "picnic_url": f"https://picnic.app/nl/winkelmandje?search={'+'.join(to_order[:3])}",
    }

def answer_training(tip_id: int) -> dict:
    global _training_score
    with _lock:
        _training_score += 10
    return {"ok": True, "score": _training_score, "message": "✅ Goed gedaan! +10 punten"}

# ── NEW action: Product Request ───────────────────────────────────────────────

def add_product_request(name: str, requester: str) -> dict:
    global _request_id_counter
    with _lock:
        req = {
            "id":        _request_id_counter,
            "name":      name,
            "emoji":     _product_emoji(name),
            "requester": requester or "Anoniem",
            "votes":     1,
            "time":      datetime.now().strftime("%H:%M"),
            "status":    "⏳ Pending",
        }
        _product_requests.append(req)
        _request_id_counter += 1
    return {"ok": True, "request": req}

def vote_product_request(req_id: int) -> dict:
    with _lock:
        for r in _product_requests:
            if r["id"] == req_id:
                r["votes"] += 1
                if r["votes"] >= 3:
                    r["status"] = "✅ Goedgekeurd!"
                return {"ok": True, "votes": r["votes"], "status": r["status"]}
    return {"ok": False, "message": "Request niet gevonden"}

# ── NEW action: Complaint ─────────────────────────────────────────────────────

def submit_complaint(text: str) -> dict:
    with _lock:
        entry = {
            "text":     text,
            "time":     datetime.now().strftime("%H:%M"),
            "response": random.choice(COMPLAINT_AUTO_RESPONSES),
        }
        _complaints.append(entry)
    return {"ok": True, "response": entry["response"]}

# ── NEW action: Mood ──────────────────────────────────────────────────────────

def set_mood(person: str, score: int) -> dict:
    score = max(1, min(5, int(score)))
    with _lock:
        _mood_votes[person] = score
    return {"ok": True, "person": person, "score": score,
            "emoji": MOOD_LABELS[score][0], "label": MOOD_LABELS[score][1],
            "mood": avg_mood()}

# ── NEW action: Oracle ────────────────────────────────────────────────────────

def ask_oracle(question: str) -> dict:
    answer, msg = random.choice(ORACLE_ANSWERS)
    ritual = random.choice([
        "Na drie rondes roeren in de saus...",
        "De gehaktbal is geraadpleegd...",
        "Nonna heeft de theebladeren gelezen...",
        "De pasta spreekt...",
        "Na het aansteken van de rituele kaars...",
    ])
    return {"ok": True, "question": question, "answer": answer, "message": msg, "ritual": ritual}

# ── NEW action: Slot Machine ──────────────────────────────────────────────────

def spin_slot_machine() -> dict:
    reels = [random.choice(SLOT_ITEMS) for _ in range(3)]
    dish  = random.choice(SLOT_DISHES)
    win   = len(set(reels)) == 1   # jackpot: all same
    return {
        "ok":    True,
        "reels": reels,
        "dish":  dish,
        "win":   win,
        "message": f"🎰 JACKPOT! Vandaag eten we: {dish}!!!" if win else f"🎰 Het lot heeft gesproken: {dish}",
    }
