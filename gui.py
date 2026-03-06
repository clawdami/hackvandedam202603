#!/usr/bin/env python3
"""
🍝 Meatball Weather Dashboard — Deluxe Edition 🍝
Launches a local web server and opens the app in your browser.
Run with: python3 gui.py [city]
"""

import http.server
import json
import random
import sys
import threading
import time
import urllib.parse
import os
try:
    import webbrowser
    _HAS_BROWSER = True
except ImportError:
    _HAS_BROWSER = False
from http.server import BaseHTTPRequestHandler

from weather_dashboard import fetch_weather, fetch_meatball_spots
import lunch_agent

PORT = int(os.environ.get("PORT", 7878))
# Default to 0.0.0.0 if HOST is set, or if running on a cloud platform
# (detected by presence of PORT env var, which Render/Railway set automatically)
_cloud = "PORT" in os.environ
HOST = os.environ.get("HOST", "0.0.0.0" if _cloud else "127.0.0.1")
DEFAULT_CITY = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Amsterdam"

# Session-wide meatball counter
_meatballs_served = 0
_meatballs_lock   = threading.Lock()


# ── Quirky content ─────────────────────────────────────────────────────────────

PASTA_WISDOM = [
    "🍝 \"The weather, like spaghetti, cannot be rushed.\"",
    "🧄 \"A true Italian checks the weather before hanging the laundry.\"",
    "🍅 \"Rain is just the sky making tomato sauce.\"",
    "👵 \"My nonna said: if it's cloudy, add more cheese.\"",
    "🌞 \"Sunshine is nature's way of saying: eat outside today.\"",
    "💨 \"Strong winds? The pasta is done, it's trying to escape.\"",
    "❄️ \"Snow is just frozen meatball tears.\"",
    "🌧️ \"Rain washes away sadness. Meatballs wash away everything else.\"",
    "🍖 \"There is no bad weather, only inappropriate sauce choices.\"",
    "🧀 \"Per aspera ad astra — through bad weather, to good pasta.\"",
    "🌩️ \"Thunder is just Zeus dropping his meatballs again.\"",
    "🌈 \"After the storm comes the rainbow. And then dessert.\"",
]

def pasta_wisdom() -> str:
    return random.choice(PASTA_WISDOM)


def nonna_verdict(temp_c: int) -> str:
    if temp_c >= 35:  return "👵 \"Madonna mia, it's a furnace! Stay inside and eat cold pasta!\""
    if temp_c >= 28:  return "👵 \"Beautiful! But don't forget your hat — you'll get a headache!\""
    if temp_c >= 22:  return "👵 \"Perfetto! Go outside, but be back for dinner at 7.\""
    if temp_c >= 16:  return "👵 \"Nice enough. Take a light jacket, just in case.\""
    if temp_c >= 10:  return "👵 \"A bit chilly! Put on a scarf or I'll worry all day.\""
    if temp_c >= 2:   return "👵 \"Freddo! Wear your coat, your hat, AND eat extra meatballs!\""
    return               "👵 \"Gesù! It's freezing! You're not going outside, I'll make soup.\""


def meatball_rating(temp_c: int, desc: str, wind_kmph: int) -> tuple[int, str]:
    """Score 1–5 🍝 based on how meatball-friendly the weather is."""
    score = 3
    d = desc.lower()
    # Temperature sweet spot: 18-24°C
    if   18 <= temp_c <= 24: score += 2
    elif 14 <= temp_c <= 28: score += 1
    elif temp_c < 0 or temp_c > 35: score -= 2
    elif temp_c < 8 or temp_c > 32: score -= 1
    # Bad conditions
    if "thunder" in d or "blizzard" in d: score -= 2
    elif "rain" in d or "snow" in d:      score -= 1
    elif "sun" in d or "clear" in d:      score += 1
    # Wind
    if wind_kmph > 50: score -= 1
    score = max(1, min(5, score))
    labels = {
        1: "Stay in, eat meatballs.",
        2: "Barely meatball weather.",
        3: "Decent meatball conditions.",
        4: "Great meatball weather!",
        5: "PERFECT MEATBALL DAY! 🎉",
    }
    return score, labels[score]


def card_colors(temp_c: int) -> tuple[str, str]:
    """Return (card_bg, accent) that shift with temperature."""
    if   temp_c >= 32: return "#5C1A0A", "#FF4500"   # scorching red
    elif temp_c >= 24: return "#4A2C15", "#E67E22"   # warm orange (default)
    elif temp_c >= 15: return "#2C3A1A", "#7DBF5E"   # mild green
    elif temp_c >= 5:  return "#1A2C3A", "#5B9BD5"   # cool blue
    else:              return "#1A1A3A", "#9B8FD5"   # freezing purple


LUNCH_HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍝 THE MEATBALL</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --cream:   #FFF8F0;
  --brown:   #5C2D0E;
  --brown-l: #8B4513;
  --red:     #C0392B;
  --gold:    #E8B84B;
  --teal:    #27AE60;
  --white:   #FFFFFF;
  --muted:   #A08060;
  --border:  #E8D5C0;
  --shadow:  0 2px 12px rgba(92,45,14,.10);
  --card-r:  14px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--cream);
  color: var(--brown);
  font-family: 'Poppins', sans-serif;
  min-height: 100vh;
  padding-bottom: 48px;
}
/* ── Header ── */
header {
  background: var(--brown);
  padding: 18px 24px;
  display: flex; align-items: center; gap: 16px;
}
header .logo { font-size: 2rem; }
header h1 {
  font-size: 1.4rem; font-weight: 800; letter-spacing: 2px;
  color: var(--gold); text-transform: uppercase;
}
header p { font-size: 0.72rem; color: #C8A880; margin-top: 1px; font-style: italic; }
.nav-link {
  margin-left: auto; color: #C8A880; text-decoration: none;
  font-size: 0.8rem; border: 1px solid #8B5C3E;
  padding: 6px 12px; border-radius: 20px; font-weight: 600;
  transition: background .2s;
}
.nav-link:hover { background: rgba(255,255,255,.1); color: var(--gold); }
/* ── Grid ── */
.grid {
  display: grid; gap: 16px; padding: 20px;
  max-width: 1100px; margin: 0 auto;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}
/* ── Card ── */
.card {
  background: var(--white);
  border-radius: var(--card-r);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.card.wide { grid-column: span 2; }
.card-header {
  padding: 12px 16px;
  font-size: 0.78rem; font-weight: 800; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--brown);
  border-bottom: 2px solid var(--cream);
  display: flex; align-items: center; gap: 8px;
}
.card-body { padding: 16px; }
/* ── Buttons ── */
.btn {
  border: none; border-radius: 20px; cursor: pointer;
  font-family: 'Poppins', sans-serif; font-weight: 700;
  font-size: 0.82rem; padding: 8px 16px; transition: all .15s;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.btn-brown { background: var(--brown); color: var(--gold); }
.btn-brown:hover { background: var(--brown-l); }
.btn-red { background: var(--red); color: #fff; }
.btn-red:hover { filter: brightness(1.1); }
.btn-gold { background: var(--gold); color: var(--brown); }
.btn-gold:hover { filter: brightness(1.05); }
.btn-teal { background: var(--teal); color: #fff; }
.btn-teal:hover { filter: brightness(1.1); }
.btn-purple { background: #8E44AD; color: #fff; }
.btn-purple:hover { filter: brightness(1.1); }
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
/* ── Inputs ── */
.inp {
  background: var(--cream); border: 1.5px solid var(--border);
  border-radius: 8px; color: var(--brown);
  font-family: 'Poppins', sans-serif; font-size: 0.85rem;
  padding: 8px 12px; width: 100%; outline: none;
  transition: border-color .2s;
}
.inp:focus { border-color: var(--gold); }
/* ── Luncher counter ── */
.big-num {
  text-align: center; font-size: 4rem; font-weight: 800;
  color: var(--brown); line-height: 1; margin: 8px 0 4px;
}
.sub { text-align: center; font-size: 0.78rem; color: var(--muted); margin-bottom: 14px; }
/* ── Budget donut ── */
.donut-wrap { display: flex; flex-direction: column; align-items: center; padding: 8px 0; }
.donut-label { font-size: 0.7rem; font-weight: 700; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }
.donut-amount { font-size: 1.6rem; font-weight: 800; color: var(--brown); }
.donut-sub { font-size: 0.72rem; color: var(--red); font-weight: 600; }
/* ── SpaarBall banner ── */
.spaarball-banner {
  background: var(--gold); border-radius: var(--card-r);
  padding: 16px 20px; display: flex; align-items: center; gap: 16px;
  box-shadow: var(--shadow);
}
.spaarball-mascot { font-size: 3rem; }
.spaarball-text { flex: 1; }
.spaarball-text h3 { font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: var(--brown); }
.spaarball-text p { font-size: 0.72rem; color: var(--brown-l); margin-top: 2px; }
.spaarball-pct {
  background: var(--white); border-radius: 50%;
  width: 72px; height: 72px; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  font-weight: 800; color: var(--brown); font-size: 1rem; line-height: 1.1;
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
}
.spaarball-pct small { font-size: 0.6rem; color: var(--muted); font-weight: 600; }
/* ── Progress bar ── */
.pbar-bg { width: 100%; height: 10px; background: var(--cream); border-radius: 5px; overflow: hidden; }
.pbar { height: 100%; border-radius: 5px; transition: width .5s; }
/* ── Agenda ── */
.agenda-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 8px; }
.agenda-table th { color: var(--muted); padding: 5px 8px; text-align: center; font-weight: 700; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 1px; }
.agenda-table td { padding: 6px 8px; text-align: center; border-top: 1px solid var(--cream); }
.agenda-table td:first-child { text-align: left; font-weight: 600; color: var(--brown); }
.day-check { cursor: pointer; font-size: 1.1rem; }
.today-th { color: var(--brown) !important; border-bottom: 2px solid var(--brown) !important; }
/* ── Inventory ── */
.inv-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-top: 1px solid var(--cream); font-size: 0.83rem; }
.inv-item:first-child { border-top: none; }
.inv-emoji { font-size: 1.3rem; width: 28px; text-align: center; }
.inv-name { flex: 1; font-weight: 600; }
.inv-bar-wrap { flex: 0 0 80px; }
.inv-qty { font-weight: 700; font-size: 0.78rem; color: var(--muted); text-align: right; margin-top: 2px; }
/* ── Picnic list ── */
.picnic-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-top: 1px solid var(--cream); font-size: 0.83rem; }
.picnic-item:first-child { border-top: none; }
.picnic-price { font-weight: 700; color: var(--red); margin-left: auto; white-space: nowrap; }
/* ── Poll ── */
.poll-item { padding: 8px 0; border-top: 1px solid var(--cream); cursor: pointer; transition: background .1s; }
.poll-item:first-child { border-top: none; }
.poll-item:hover { background: var(--cream); border-radius: 8px; padding-left: 6px; }
.poll-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 0.83rem; font-weight: 600; }
.poll-pct { margin-left: auto; font-size: 0.72rem; color: var(--muted); }
.poll-bar-gold { background: var(--gold) !important; }
/* ── Requests ── */
.req-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-top: 1px solid var(--cream); font-size: 0.82rem; }
.req-item:first-child { border-top: none; }
.req-status { font-size: 0.68rem; font-weight: 700; padding: 2px 6px; border-radius: 10px; background: var(--cream); color: var(--muted); white-space: nowrap; }
.req-status.ok { background: #D5F5E3; color: var(--teal); }
/* ── Mood ── */
.mood-avg { text-align: center; font-size: 3rem; margin: 8px 0 4px; }
.mood-btn { cursor: pointer; font-size: 1.5rem; padding: 4px 8px; border-radius: 8px; border: 2px solid transparent; transition: all .15s; display: inline-block; }
.mood-btn:hover { border-color: var(--gold); transform: scale(1.15); }
/* ── Oracle ── */
.oracle-box { background: var(--cream); border-radius: 10px; padding: 14px; text-align: center; margin-top: 12px; display: none; }
.oracle-ritual { font-size: 0.72rem; color: var(--muted); font-style: italic; margin-bottom: 6px; }
.oracle-msg { font-size: 0.9rem; font-weight: 700; color: #8E44AD; }
/* ── Slot Machine ── */
.reels { display: flex; justify-content: center; gap: 12px; font-size: 3rem; margin: 10px 0; background: var(--cream); padding: 14px; border-radius: 10px; }
.spin-result { text-align: center; font-size: 0.85rem; color: var(--red); font-weight: 700; min-height: 20px; }
/* ── Complaints ── */
.complaint-item { padding: 8px 0; border-top: 1px solid var(--cream); font-size: 0.8rem; }
.complaint-item:first-child { border-top: none; }
.complaint-response { font-size: 0.72rem; color: var(--muted); font-style: italic; margin-top: 2px; }
/* ── Leaderboard ── */
.lb-item { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-top: 1px solid var(--cream); font-size: 0.83rem; }
.lb-item:first-child { border-top: none; }
/* ── Nonna alert ── */
.nonna-alert { border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.82rem; font-weight: 600; border-left: 4px solid; }
/* ── Misc ── */
.msg { font-size: 0.74rem; color: var(--teal); margin-top: 6px; min-height: 16px; font-weight: 600; }
.picnic-link { display: inline-block; margin-top: 8px; color: var(--brown); font-size: 0.78rem; font-weight: 700; text-decoration: none; border: 1.5px solid var(--border); padding: 6px 12px; border-radius: 20px; }
.picnic-link:hover { border-color: var(--brown); }
.label-small { font-size: 0.7rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
/* ── Toast ── */
#toast { position: fixed; bottom: 20px; right: 20px; background: var(--brown); color: var(--gold); padding: 12px 18px; border-radius: 12px; font-size: 0.84rem; font-weight: 700; font-family: 'Poppins', sans-serif; display: none; z-index: 999; max-width: 300px; box-shadow: 0 4px 20px rgba(92,45,14,.3); }
@keyframes slot-spin { 0%{transform:translateY(-10px);opacity:0} 100%{transform:translateY(0);opacity:1} }
.reel.spinning { animation: slot-spin .15s ease-out; }
@media (max-width: 640px) { .card.wide { grid-column: span 1; } }
</style>
</head>
<body>
<header>
  <span class="logo">🍝</span>
  <div>
    <h1>The Meatball</h1>
    <p>Super Modern Lunch Dashboard voor de Lunch — fatto con amore</p>
  </div>
  <a class="nav-link" href="/">← Meteo</a>
</header>

<div class="grid">

  <!-- Budget donut -->
  <div class="card">
    <div class="card-header">💶 WEEKLY BUDGET</div>
    <div class="card-body">
      <div id="nonnalert"></div>
      <div class="donut-wrap" style="margin-bottom:10px">
        <svg width="160" height="160" viewBox="0 0 160 160" style="margin:0 auto">
          <circle cx="80" cy="80" r="60" fill="none" stroke="#F5E6D0" stroke-width="20"/>
          <circle id="donut-ring" cx="80" cy="80" r="60" fill="none" stroke="#E8B84B" stroke-width="20"
            stroke-dasharray="377" stroke-dashoffset="377" stroke-linecap="round"
            transform="rotate(-90 80 80)" style="transition:stroke-dashoffset .6s"/>
          <circle id="donut-spent" cx="80" cy="80" r="60" fill="none" stroke="#C0392B" stroke-width="20"
            stroke-dasharray="377" stroke-dashoffset="377" stroke-linecap="round"
            transform="rotate(-90 80 80)" style="transition:stroke-dashoffset .6s"/>
          <text x="80" y="72" text-anchor="middle" font-family="Poppins,sans-serif" font-size="11" font-weight="800" fill="#5C2D0E">€120</text>
          <text x="80" y="86" text-anchor="middle" font-family="Poppins,sans-serif" font-size="8" font-weight="600" fill="#A08060">WEEKLY BUDGET</text>
          <text x="80" y="100" text-anchor="middle" font-family="Poppins,sans-serif" font-size="8" font-weight="700" fill="#C0392B" id="donut-spent-label">SPENT: €--</text>
          <text style="font-size:28px" x="80" y="82" text-anchor="middle" dominant-baseline="middle">🍖</text>
        </svg>
      </div>
      <div class="btn-row" style="justify-content:space-between;margin-bottom:8px">
        <div><div class="label-small">Uitgegeven</div><div style="font-size:1.2rem;font-weight:800;color:var(--red)" id="budSpent">€--</div></div>
        <div style="text-align:right"><div class="label-small">Resterend</div><div style="font-size:1.2rem;font-weight:800;color:var(--teal)" id="budRem">€--</div></div>
      </div>
    </div>
  </div>

  <!-- Luncher counter -->
  <div class="card">
    <div class="card-header">👥 AANTAL LUNCHERS <span style="margin-left:auto;font-size:0.68rem;color:var(--muted);font-weight:600" id="weekBadge">WEEK --</span></div>
    <div class="card-body">
      <div class="big-num" id="luncherCount">--</div>
      <div class="sub">persone mangiano oggi</div>
      <div class="btn-row" style="justify-content:center;margin-bottom:8px">
        <button class="btn btn-brown" onclick="chgLunch(-5)">−5</button>
        <button class="btn btn-brown" onclick="chgLunch(-1)">−1</button>
        <button class="btn btn-gold" onclick="chgLunch(+1)">+1</button>
        <button class="btn btn-gold" onclick="chgLunch(+5)">+5</button>
      </div>
      <div class="msg" id="lunchMsg"></div>
      <!-- Sfeer-o-meter in same card -->
      <div style="border-top:1px solid var(--cream);margin-top:12px;padding-top:12px">
        <div class="label-small" style="margin-bottom:6px">🌡️ Sfeer-o-meter</div>
        <div style="text-align:center;font-size:2rem;margin-bottom:4px" id="moodAvgEmoji">🤔</div>
        <div style="text-align:center;font-size:0.75rem;color:var(--muted);margin-bottom:8px" id="moodAvgLabel">Nog geen stemmen</div>
        <input class="inp" id="moodName" placeholder="Jouw naam..." style="margin-bottom:6px">
        <div class="btn-row" style="justify-content:center">
          <span class="mood-btn" onclick="voteMood(1)" title="Vreselijk">💀</span>
          <span class="mood-btn" onclick="voteMood(2)" title="Slecht">😞</span>
          <span class="mood-btn" onclick="voteMood(3)" title="Meh">😐</span>
          <span class="mood-btn" onclick="voteMood(4)" title="Goed">😊</span>
          <span class="mood-btn" onclick="voteMood(5)" title="GEWELDIG">🔥</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Agenda -->
  <div class="card wide">
    <div class="card-header">📅 AGENDA: WHO'S AT OFFICE</div>
    <div class="card-body">
      <table class="agenda-table">
        <thead><tr>
          <th>NOME</th>
          <th id="th-MA">MA</th><th id="th-DI">DI</th><th id="th-WO">WO</th>
          <th id="th-DO">DO</th><th id="th-VR">VR</th>
        </tr></thead>
        <tbody id="agendaBody"></tbody>
      </table>
      <div class="msg" id="agendaMsg"></div>
    </div>
  </div>

  <!-- Picnic List -->
  <div class="card">
    <div class="card-header">🛒 PICNIC LIST</div>
    <div class="card-body">
      <div style="font-size:0.72rem;color:var(--muted);margin-bottom:8px">Lijst op basis van lage voorraad</div>
      <div id="picnicList">Laden…</div>
      <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
        <button class="btn btn-red" onclick="orderPicnic()">🛒 BESTELLEN</button>
        <a class="picnic-link" id="picnicCartLink" href="https://picnic.app" target="_blank" style="display:none">🔗 Winkelmandje</a>
      </div>
      <div class="msg" id="picnicMsg"></div>
    </div>
  </div>

  <!-- Poll -->
  <div class="card">
    <div class="card-header">💡 LUNCH SUGGESTION POLL</div>
    <div class="card-body">
      <div style="font-size:0.72rem;color:var(--muted);margin-bottom:10px">Klik om te stemmen — VOTA!</div>
      <div id="pollList">Laden…</div>
    </div>
  </div>

  <!-- Inventory -->
  <div class="card">
    <div class="card-header">📦 VOORRAAD</div>
    <div class="card-body">
      <div id="invList">Laden…</div>
      <button class="btn btn-teal" style="margin-top:12px;width:100%" onclick="scanInv()">📸 SCAN VOORRAADLA</button>
      <div class="msg" id="invMsg"></div>
    </div>
  </div>

  <!-- SpaarBall banner -->
  <div class="spaarball-banner wide">
    <div class="spaarball-mascot">🍖</div>
    <div class="spaarball-text">
      <h3>Savings Meatball Piggy Bank</h3>
      <p>Budget surplus gaat naar de SpaarBall — SpaarPlan Biertafels</p>
      <div style="font-size:1.4rem;font-weight:800;color:var(--brown);margin-top:4px" id="spaarbBal">€--</div>
      <div style="font-size:0.72rem;color:var(--brown-l)" id="spaarbEarn">+€-- dit jaar</div>
    </div>
    <div class="spaarball-pct">
      <span id="spaarbPct">1,23%</span>
      <small>SAVED</small>
    </div>
  </div>

  <!-- Leaderboard -->
  <div class="card">
    <div class="card-header">🏆 LUNCH LEADERBOARD</div>
    <div class="card-body"><div id="leaderboard">Laden…</div></div>
  </div>

  <!-- Product Requests -->
  <div class="card">
    <div class="card-header">🛍️ PRODUCT REQUESTS</div>
    <div class="card-body">
      <div style="font-size:0.72rem;color:var(--muted);margin-bottom:8px">3 stemmen = automatisch goedgekeurd!</div>
      <div style="display:flex;gap:6px;margin-bottom:8px">
        <input class="inp" id="reqName" placeholder="Product...">
        <input class="inp" id="reqWho" placeholder="Naam" style="max-width:90px">
      </div>
      <button class="btn btn-teal" onclick="submitRequest()" style="width:100%;margin-bottom:10px">AANVRAGEN +</button>
      <div id="reqList" style="font-size:0.82rem">Geen requests</div>
      <div class="msg" id="reqMsg"></div>
    </div>
  </div>

  <!-- Slot Machine -->
  <div class="card">
    <div class="card-header">🎰 COSA MANGIAMO? (Slot Machine)</div>
    <div class="card-body">
      <div class="reels"><span id="r1">🍝</span><span id="r2">🍖</span><span id="r3">🍅</span></div>
      <div class="spin-result" id="spinResult">Premi il pulsante…</div>
      <button class="btn btn-gold" style="width:100%;margin-top:10px;font-size:0.95rem" onclick="spinSlot()">🎰 GIRA LA RUOTA!</button>
    </div>
  </div>

  <!-- Oracle -->
  <div class="card">
    <div class="card-header">🔮 ORACOLO DEL MEATBALL</div>
    <div class="card-body">
      <div style="font-size:0.72rem;color:var(--muted);margin-bottom:8px">Fai una domanda sì/no all'Oracle…</div>
      <input class="inp" id="oracleQ" placeholder="Mogen we pizza bestellen?" style="margin-bottom:8px">
      <button class="btn btn-purple" style="width:100%" onclick="askOracle()">🔮 CHIEDI ALL'ORACOLO</button>
      <div class="oracle-box" id="oracleBox">
        <div class="oracle-ritual" id="oracleRitual"></div>
        <div class="oracle-msg" id="oracleMsg"></div>
      </div>
    </div>
  </div>

  <!-- Complaint Box -->
  <div class="card">
    <div class="card-header">😤 KLACHTENBUS (anonimo)</div>
    <div class="card-body">
      <div style="font-size:0.72rem;color:var(--muted);margin-bottom:8px">Klaag vrij. Nessuno legge. (Tranne tutti.)</div>
      <textarea class="inp" id="complaintText" rows="2" placeholder="La tua lamentela..." style="resize:none;margin-bottom:8px"></textarea>
      <button class="btn btn-red" style="width:100%;margin-bottom:10px" onclick="submitComplaint()">😤 INDIETRO!</button>
      <div id="complaintList" style="font-size:0.78rem">Ancora nessun reclamo. Straordinario.</div>
    </div>
  </div>

  <!-- Order History -->
  <div class="card">
    <div class="card-header">📋 BESTELHISTORIE</div>
    <div class="card-body"><div id="orderHist" style="font-size:0.78rem;color:var(--muted)">Nessun ordine</div></div>
  </div>

  <!-- Training Tool -->
  <div class="card">
    <div class="card-header">🎓 SCUOLA DI CUCINA</div>
    <div class="card-body">
      <div style="text-align:center;margin-bottom:12px">
        <div style="font-size:2rem;font-weight:800;color:var(--gold)">⭐ <span id="trainScore">0</span></div>
        <div style="font-size:0.7rem;color:var(--muted);font-weight:700;letter-spacing:1px">PUNTI CUCINA</div>
      </div>
      <div id="trainTips">Laden…</div>
    </div>
  </div>

</div>
<div id="toast"></div>

<script>
let state = {};

function toast(msg, col) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.style.background = col || "var(--brown)";
  el.style.display = "block";
  setTimeout(() => el.style.display = "none", 3500);
}
function msg(id, txt, ms) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = txt;
  if (ms) setTimeout(() => { if (el.textContent === txt) el.textContent = ""; }, ms);
}

async function loadState() {
  const r = await fetch("/lunch/state");
  state = await r.json();
  render();
}

function renderDonut(pct) {
  const circ = 2 * Math.PI * 60; // 377
  // gold = full ring as bg (already set in HTML)
  // spent = red overlay
  const spentOff = circ * (1 - pct / 100);
  document.getElementById("donut-spent").setAttribute("stroke-dashoffset", spentOff.toFixed(1));
}

function render() {
  document.getElementById("luncherCount").textContent = state.lunchers;
  document.getElementById("weekBadge").textContent = "WEEK " + state.week;

  // Budget
  const b = state.budget;
  renderDonut(b.pct_used);
  document.getElementById("donut-spent-label").textContent = "SPENT: €" + b.spent.toFixed(2);
  document.getElementById("budSpent").textContent = "€" + b.spent.toFixed(2);
  document.getElementById("budRem").textContent   = "€" + b.remaining.toFixed(2);
  document.getElementById("spaarbBal").textContent  = "€" + b.spaarball.toFixed(2);
  document.getElementById("spaarbEarn").textContent = "+€" + b.spaarball_earn.toFixed(2) + " dit jaar";
  // Nonna alert
  const na = state.budget.nonna_alert;
  const nael = document.getElementById("nonnalert");
  if (na) {
    nael.innerHTML = `<div class="nonna-alert" style="background:${na.color}18;border-color:${na.color};color:${na.color}">${na.level} ${na.msg}</div>`;
  } else { nael.innerHTML = ""; }

  // Mood
  const m = state.mood;
  document.getElementById("moodAvgEmoji").textContent = m.emoji || "🤔";
  document.getElementById("moodAvgLabel").textContent = m.avg ? m.avg + "/5 — " + m.label : "Nog geen stemmen";

  // Agenda
  const days = state.weekdays;
  days.forEach(d => {
    const th = document.getElementById("th-" + d);
    if (th) { th.className = d === state.today ? "today-th" : ""; }
  });
  document.getElementById("agendaBody").innerHTML = Object.entries(state.agenda).map(([name, sched]) =>
    `<tr><td>${name}</td>${days.map(d =>
      `<td><span class="day-check" onclick="toggleAgenda('${name}','${d}')" title="${name} · ${d}">`+
      (sched[d] ? `<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;background:var(--teal);border-radius:50%;color:#fff;font-size:0.7rem">✓</span>`
                : `<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;background:var(--cream);border-radius:50%;color:var(--muted);font-size:0.75rem">·</span>`)+
      `</span></td>`).join("")}</tr>`
  ).join("");

  // Leaderboard
  const medals = ["🥇","🥈","🥉"];
  document.getElementById("leaderboard").innerHTML = state.leaderboard.map((p, i) =>
    `<div class="lb-item"><span style="font-size:1.3rem">${medals[i]||"🍝"}</span><span style="flex:1;font-weight:600">${p.name}</span>`+
    `<span style="font-weight:800;color:var(--brown)">${p.days} <span style="font-size:0.7rem;color:var(--muted);font-weight:600">giorni</span></span></div>`
  ).join("");

  // Inventory
  document.getElementById("invList").innerHTML = state.inventory.map(i => {
    const low = i.qty < i.min;
    const pct = Math.min(100, Math.round((i.qty / (i.min * 2)) * 100));
    return `<div class="inv-item">
      <span class="inv-emoji">${i.emoji}</span>
      <div style="flex:1">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
          <span class="inv-name" style="${low?'color:var(--red)':''}">${i.name}</span>
          <span style="font-size:0.72rem;font-weight:700;color:${low?'var(--red)':'var(--muted)'}">${i.qty}${i.unit}</span>
        </div>
        <div class="pbar-bg"><div class="pbar" style="width:${pct}%;background:${low?'var(--red)':pct>60?'var(--teal)':'var(--gold)'}"></div></div>
      </div></div>`;
  }).join("");

  // Picnic list
  const pl = document.getElementById("picnicList");
  pl.innerHTML = !state.picnic_list || state.picnic_list.length === 0
    ? `<div style="color:var(--teal);font-weight:700;font-size:0.82rem">✅ La dispensa è piena!</div>`
    : state.picnic_list.map(i =>
        `<div class="picnic-item"><span style="font-size:1.2rem">${i.emoji}</span>`+
        `<span style="flex:1;font-weight:600">${i.name}</span>`+
        `<span class="picnic-price">+${i.needed} ${i.unit}</span></div>`
      ).join("");

  // Poll
  const poll = state.suggestion.poll || [];
  const maxV = Math.max(...poll.map(p => p.votes), 1);
  const winner = poll.reduce((a, b) => b.votes > a.votes ? b : a, poll[0] || {});
  document.getElementById("pollList").innerHTML = poll.map(p => {
    const pct = Math.round((p.votes / maxV) * 100);
    const isW = p.votes > 0 && p.dish === winner.dish;
    return `<div class="poll-item" onclick="votePoll('${p.dish.replace(/'/g,"\\'")}')">
      <div class="poll-top">
        <span>${p.emoji}</span>
        <span style="${isW?'color:var(--gold);font-weight:800':''}">${p.dish}</span>
        <span class="poll-pct">${p.votes} v</span>
      </div>
      <div class="pbar-bg" style="height:6px"><div class="pbar ${isW?'poll-bar-gold':''}" style="width:${pct}%;background:${isW?'var(--gold)':'var(--red)'}"></div></div>
    </div>`;
  }).join("");

  // Product requests
  const rl = document.getElementById("reqList");
  rl.innerHTML = !state.product_requests || state.product_requests.length === 0
    ? `<span style="color:var(--muted);font-size:0.8rem">Nessuna richiesta</span>`
    : state.product_requests.map(r =>
        `<div class="req-item">
          <span style="font-size:1.2rem">${r.emoji}</span>
          <div style="flex:1"><div style="font-weight:600">${r.name}</div><div style="font-size:0.7rem;color:var(--muted)">${r.requester}</div></div>
          <span onclick="voteRequest(${r.id})" style="cursor:pointer;font-size:0.78rem;font-weight:700;color:var(--brown);margin-right:6px">👍 ${r.votes}</span>
          <span class="req-status ${r.status.includes('Goedgekeurd')?'ok':''}">${r.status}</span>
        </div>`
      ).join("");

  // Order history
  document.getElementById("orderHist").innerHTML = !state.order_history || state.order_history.length === 0
    ? `<span style="color:var(--muted)">Nessun ordine</span>`
    : state.order_history.slice().reverse().map(o =>
        `<div style="padding:5px 0;border-top:1px solid var(--cream);font-size:0.78rem">
          <span style="font-weight:700;color:var(--brown)">${o.time}</span> — ${o.items.join(", ")}
          <span style="color:var(--red);float:right;font-weight:700">€${o.cost.toFixed(2)}</span>
        </div>`).join("");

  // Complaints
  document.getElementById("complaintList").innerHTML = !state.complaints || state.complaints.length === 0
    ? `<span style="color:var(--muted)">Ancora nessun reclamo. Straordinario.</span>`
    : state.complaints.slice().reverse().map(c =>
        `<div class="complaint-item"><span style="color:var(--muted);font-size:0.68rem">${c.time}</span> ${c.text}<div class="complaint-response">${c.response}</div></div>`
      ).join("");

  // Training
  document.getElementById("trainScore").textContent = state.training_score;
  document.getElementById("trainTips").innerHTML = state.training_tips.map(t =>
    `<div onclick="markTip(${t.id})" style="display:flex;gap:8px;align-items:flex-start;padding:8px;border-radius:8px;cursor:pointer;transition:background .1s;font-size:0.8rem;border-top:1px solid var(--cream)"
         onmouseover="this.style.background='var(--cream)'" onmouseout="this.style.background=''">`+
    `<span style="font-size:1.1rem">${t.emoji}</span><span style="font-weight:500">${t.tip}</span></div>`
  ).join("");
}

// ── Actions ──
async function chgLunch(d) {
  const n = (state.lunchers||0) + d;
  const r = await fetch("/lunch/lunchers?n=" + n);
  const x = await r.json();
  state.lunchers = x.lunchers;
  document.getElementById("luncherCount").textContent = x.lunchers;
  msg("lunchMsg", "👥 " + x.lunchers + " lunchers", 2000);
}
async function toggleAgenda(person, day) {
  const r = await fetch("/lunch/agenda?person=" + encodeURIComponent(person) + "&day=" + day);
  const d = await r.json();
  state.agenda = d.agenda;
  render();
  msg("agendaMsg", person + " · " + day + " bijgewerkt", 2000);
}
async function votePoll(dish) {
  const r = await fetch("/lunch/vote?dish=" + encodeURIComponent(dish));
  const d = await r.json();
  const item = state.suggestion.poll.find(p => p.dish === dish);
  if (item) item.votes = d.votes;
  render();
  toast("👍 Votato: " + dish + "!");
}
async function scanInv() {
  msg("invMsg", "📸 Scanning…");
  const r = await fetch("/lunch/scan");
  const d = await r.json();
  state.inventory = d.inventory;
  render();
  msg("invMsg", d.message, 3000);
  toast(d.message);
}
async function orderPicnic() {
  msg("picnicMsg", "🛒 Ordinando…");
  const r = await fetch("/lunch/order");
  const d = await r.json();
  if (d.ok) {
    toast(d.message, "var(--red)");
    if (d.picnic_url) {
      const lnk = document.getElementById("picnicCartLink");
      lnk.href = d.picnic_url; lnk.style.display = "inline-block";
    }
    await loadState();
  } else {
    toast("✅ " + d.message, "var(--teal)");
  }
  msg("picnicMsg", d.message, 4000);
}
async function submitRequest() {
  const name = document.getElementById("reqName").value.trim();
  const who  = document.getElementById("reqWho").value.trim();
  if (!name) { toast("Inserisci un prodotto!", "var(--red)"); return; }
  const r = await fetch("/lunch/request?name=" + encodeURIComponent(name) + "&who=" + encodeURIComponent(who));
  const d = await r.json();
  if (d.ok) { state.product_requests.push(d.request); document.getElementById("reqName").value = ""; render(); toast("✅ Richiesta: " + name); }
}
async function voteRequest(id) {
  const r = await fetch("/lunch/request/vote?id=" + id);
  const d = await r.json();
  if (d.ok) {
    const req = state.product_requests.find(x => x.id === id);
    if (req) { req.votes = d.votes; req.status = d.status; }
    render(); toast("👍 " + d.votes + " stemmen!");
  }
}
async function voteMood(score) {
  const person = document.getElementById("moodName").value.trim() || "Anoniem";
  const r = await fetch("/lunch/mood?person=" + encodeURIComponent(person) + "&score=" + score);
  const d = await r.json();
  state.mood = d.mood;
  render();
  toast(d.emoji + " Sfeer: " + d.label);
}
async function askOracle() {
  const q = document.getElementById("oracleQ").value.trim() || "Wat is het antwoord?";
  const r = await fetch("/lunch/oracle?q=" + encodeURIComponent(q));
  const d = await r.json();
  const box = document.getElementById("oracleBox");
  box.style.display = "block";
  document.getElementById("oracleRitual").textContent = d.ritual;
  document.getElementById("oracleMsg").textContent = d.message;
  toast("🔮 L'Oracolo ha parlato!", "#8E44AD");
}
async function spinSlot() {
  const btn = document.querySelector(".btn-gold");
  btn.disabled = true; btn.textContent = "🎲 Girando…";
  const items = ["🍝","🍕","🌭","🧆","🥙","🍖","🥗","🍔","🌮","🍛","🍣","🥩","🥘","🫕","🍱"];
  let frames = 0;
  const anim = setInterval(() => {
    ["r1","r2","r3"].forEach(id => document.getElementById(id).textContent = items[Math.floor(Math.random()*items.length)]);
    if (++frames > 15) clearInterval(anim);
  }, 80);
  setTimeout(async () => {
    const r = await fetch("/lunch/spin");
    const d = await r.json();
    ["r1","r2","r3"].forEach((id,i) => document.getElementById(id).textContent = d.reels[i]);
    document.getElementById("spinResult").textContent = d.message;
    document.getElementById("spinResult").style.color = d.win ? "var(--gold)" : "var(--red)";
    if (d.win) toast("🎰🎰🎰 JACKPOT! " + d.dish, "var(--gold)");
    btn.disabled = false; btn.textContent = "🎰 GIRA LA RUOTA!";
  }, 1400);
}
async function submitComplaint() {
  const text = document.getElementById("complaintText").value.trim();
  if (!text) { toast("La tua lamentela è vuota. Anche questo è un reclamo.", "var(--red)"); return; }
  const r = await fetch("/lunch/complaint?text=" + encodeURIComponent(text));
  const d = await r.json();
  document.getElementById("complaintText").value = "";
  state.complaints.push({ text, time: new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}), response: d.response });
  render();
  toast(d.response, "var(--brown)");
}
async function markTip(id) {
  const r = await fetch("/lunch/training?tip_id=" + id);
  const d = await r.json();
  document.getElementById("trainScore").textContent = d.score;
  toast("🎓 " + d.message);
}
loadState();
setInterval(loadState, 30000);
</script>
</body>
</html>
"""
EASTER_EGG_HTML = """
<div style="text-align:center;padding:40px 20px">
  <div style="font-size:5rem">🍝</div>
  <h2 style="color:#F5CBA7;margin:16px 0 8px;font-size:1.6rem">YOU FOUND THE MEATBALL</h2>
  <p style="color:#A07850;font-size:0.9rem">There is no weather here.<br>Only pasta.<br>Always pasta.</p>
  <div style="font-size:2.5rem;margin:24px 0">🍖 🍅 🧀 🧄 🍝</div>
  <p style="color:#C0392B;font-size:0.8rem">~ A message from Nonna ~</p>
</div>
"""


# ── HTML template ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍝 Meatball Weather Deluxe</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');
  :root {
    --bg-dark:   #2B1A0E;
    --bg-mid:    #3D2310;
    --bg-card:   #4A2C15;
    --sauce:     #C0392B;
    --orange:    #E67E22;
    --cheese:    #F5CBA7;
    --meatball:  #8B4513;
    --basil:     #27AE60;
    --cream:     #FAD7A0;
    --parchment: #A07850;
    --spicy:     #FF6B35;
    --card-accent: #E67E22;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-dark);
    color: var(--cream);
    font-family: 'Courier Prime', 'Courier New', monospace;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-bottom: 40px;
  }
  header {
    width: 100%;
    background: var(--sauce);
    text-align: center;
    padding: 18px 16px 10px;
  }
  header h1  { font-size: 1.8rem; color: var(--cheese); letter-spacing: 2px; }
  header p   { font-size: 0.78rem; color: var(--cream); opacity: .75; margin-top: 4px; }
  .counter   { font-size: 0.72rem; color: var(--cheese); opacity: .6; margin-top: 3px; }

  .wisdom {
    width: 100%; max-width: 520px;
    background: var(--bg-mid);
    border-left: 3px solid var(--meatball);
    padding: 10px 16px;
    margin: 14px 16px 0;
    font-size: 0.82rem;
    color: var(--parchment);
    font-style: italic;
  }

  .search {
    display: flex; align-items: center; gap: 10px;
    margin: 14px 0 0; padding: 0 16px;
    width: 100%; max-width: 520px;
  }
  .search label { color: var(--parchment); font-size: 0.9rem; white-space: nowrap; }
  .search input {
    flex: 1;
    background: var(--bg-card); border: 2px solid var(--meatball);
    border-radius: 4px; color: var(--cheese);
    font-family: inherit; font-size: 1rem;
    padding: 8px 12px; outline: none;
    transition: border-color .2s;
  }
  .search input:focus { border-color: var(--orange); }
  .search button {
    background: var(--sauce); border: none; border-radius: 4px;
    color: var(--cheese); cursor: pointer;
    font-family: inherit; font-size: 0.95rem; font-weight: bold;
    padding: 9px 16px; transition: background .2s; white-space: nowrap;
  }
  .search button:hover { background: var(--spicy); }

  .card {
    background: var(--bg-card);
    border: 2px solid var(--meatball); border-radius: 8px;
    margin: 14px 16px 0; max-width: 520px; width: 100%;
    overflow: hidden;
    transition: background 0.6s;
  }
  .card-top {
    display: flex; align-items: center; gap: 16px;
    padding: 18px 20px 6px;
  }
  .weather-icon { font-size: 3.4rem; line-height: 1; }
  .temp-c { font-size: 2.4rem; font-weight: bold; color: var(--cheese); }
  .temp-f { font-size: 0.9rem; color: var(--parchment); }
  .city-line {
    padding: 4px 20px 2px; font-size: 1.2rem;
    font-weight: bold; color: var(--card-accent);
    transition: color 0.6s;
  }
  .desc-line { padding: 0 20px 10px; font-size: 0.85rem; color: var(--parchment); }
  hr { border: none; border-top: 1px solid var(--meatball); margin: 0 20px; }

  /* Meatball-o-meter */
  .meter {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 20px 4px;
  }
  .meter-label { font-size: 0.75rem; color: var(--parchment); white-space: nowrap; }
  .meter-balls { font-size: 1.2rem; letter-spacing: 2px; }
  .meter-text  { font-size: 0.78rem; color: var(--orange); font-style: italic; }

  /* Nonna */
  .nonna {
    padding: 4px 20px 12px;
    font-size: 0.82rem; color: var(--cheese);
    font-style: italic; border-left: 2px solid var(--sauce);
    margin: 0 20px 10px; background: rgba(0,0,0,.15); border-radius: 0 4px 4px 0;
  }

  .stats {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 8px; padding: 4px 16px 16px;
  }
  .stat { background: var(--bg-mid); border-radius: 6px; padding: 10px 12px; }
  .stat-label { font-size: 0.75rem; color: var(--parchment); }
  .stat-value { font-size: 1.05rem; font-weight: bold; color: var(--cheese); margin-top: 2px; }

  .status {
    font-size: 0.78rem; color: var(--parchment);
    margin-top: 14px; text-align: center;
    max-width: 520px; padding: 0 16px;
  }
  .status.loading { color: var(--orange); }
  .status.ok      { color: var(--basil); }
  .status.err     { color: var(--sauce); }

  .spaghetti { font-size: 0.7rem; letter-spacing: 3px; color: var(--meatball); margin: 18px 0 4px; text-align: center; }

  /* ── Meatball Spots ── */
  .spots-section {
    background: var(--bg-card); border: 2px solid var(--meatball);
    border-radius: 8px; margin: 14px 16px 0;
    max-width: 520px; width: 100%; overflow: hidden;
  }
  .spots-header {
    background: var(--sauce); padding: 10px 16px;
    font-size: 1rem; font-weight: bold; color: var(--cheese);
    display: flex; align-items: center; gap: 8px;
  }
  .spots-list { padding: 8px 0; }
  .spot-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 16px; border-bottom: 1px solid var(--bg-mid);
    transition: background .15s;
  }
  .spot-item:last-child { border-bottom: none; }
  .spot-item:hover { background: rgba(255,255,255,.04); }
  .spot-icon { font-size: 1.3rem; flex-shrink: 0; margin-top: 1px; }
  .spot-name { font-size: 0.95rem; font-weight: bold; color: var(--cheese); }
  .spot-meta { font-size: 0.75rem; color: var(--parchment); margin-top: 2px; }
  .spot-dist { font-size: 0.72rem; color: var(--orange); margin-top: 2px; }
  .spots-empty { padding: 16px; text-align: center; color: var(--parchment); font-size: 0.85rem; font-style: italic; }
  .spots-loading { padding: 14px 16px; color: var(--orange); font-size: 0.85rem; }

  /* Loading animation */
  @keyframes pasta-spin {
    0%   { content: "🍝"; }
    25%  { content: "🍖"; }
    50%  { content: "🍅"; }
    75%  { content: "🧀"; }
    100% { content: "🍝"; }
  }
  .loading-anim { display: inline-block; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body data-city="__DEFAULT_CITY__">

<header>
  <h1>🍝 MEATBALL WEATHER DELUXE 🍝</h1>
  <p>Serving forecasts since the dawn of pasta</p>
  <div class="counter" id="counter">0 meatballs served this session &nbsp;·&nbsp; <a href="/lunch" style="color:var(--cheese);text-decoration:none">🥙 Lunch Dashboard →</a></div>
</header>

<div class="wisdom" id="wisdom">__WISDOM__</div>

<div class="search">
  <label>📍</label>
  <input id="cityInput" type="text" placeholder="Enter city… or try 'meatball'" />
  <button onclick="doSearch()">🍖 FETCH</button>
</div>

<div class="card" id="card">
  <div class="card-top">
    <div class="weather-icon" id="icon">🍝</div>
    <div>
      <div class="temp-c" id="tempC">--°C</div>
      <div class="temp-f" id="tempF">--°F</div>
    </div>
  </div>
  <div class="city-line" id="cityLine">Loading…</div>
  <div class="desc-line" id="descLine"></div>
  <div class="meter" id="meterRow" style="display:none">
    <span class="meter-label">Meatball-o-meter:</span>
    <span class="meter-balls" id="meterBalls"></span>
    <span class="meter-text" id="meterText"></span>
  </div>
  <div class="nonna" id="nonna" style="display:none"></div>
  <hr>
  <div class="stats">
    <div class="stat"><div class="stat-label">🤔 Feels Like</div><div class="stat-value" id="feels">--</div></div>
    <div class="stat"><div class="stat-label">💧 Humidity</div><div class="stat-value" id="humidity">--</div></div>
    <div class="stat"><div class="stat-label">💨 Wind</div><div class="stat-value" id="wind">--</div></div>
    <div class="stat"><div class="stat-label">👁 Visibility</div><div class="stat-value" id="visibility">--</div></div>
    <div class="stat"><div class="stat-label">☀️ UV Index</div><div class="stat-value" id="uv">--</div></div>
    <div class="stat"><div class="stat-label">🕐 Updated</div><div class="stat-value" id="updated">--</div></div>
  </div>
</div>

<div id="easterEgg" style="display:none;max-width:520px;width:100%;margin:14px 16px 0;background:#4A2C15;border:2px solid #8B4513;border-radius:8px;overflow:hidden"></div>

<div class="spots-section" id="spotsSection" style="display:none">
  <div class="spots-header">🍝 Nearby Meatball Spots</div>
  <div class="spots-list" id="spotsList">
    <div class="spots-loading">🍖 Sniffing out meatballs in the area…</div>
  </div>
</div>

<div class="spaghetti">~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~</div>
<div class="status" id="status">🍝 Ready to serve weather</div>

<script>
const ICONS = {
  sunny:"☀️", cloudy:"☁️", rain:"🌧️", snow:"❄️",
  thunder:"⛈️", fog:"🌫️", wind:"💨", default:"🌡️"
};

let served = 0;

function iconKey(desc) {
  const d = desc.toLowerCase();
  if (d.includes("thunder"))                             return "thunder";
  if (d.includes("snow") || d.includes("blizzard"))     return "snow";
  if (d.includes("rain")||d.includes("drizzle")||d.includes("shower")) return "rain";
  if (d.includes("fog") || d.includes("mist"))          return "fog";
  if (d.includes("cloud") || d.includes("overcast"))    return "cloudy";
  if (d.includes("wind"))                               return "wind";
  if (d.includes("sun") || d.includes("clear"))         return "sunny";
  return "default";
}

function setStatus(msg, cls) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status " + (cls||"");
}

function doSearch() {
  const city = document.getElementById("cityInput").value.trim();
  if (!city) return;

  // Easter egg
  if (city.toLowerCase() === "meatball") {
    document.getElementById("card").style.display = "none";
    const egg = document.getElementById("easterEgg");
    egg.style.display = "block";
    egg.innerHTML = `__EASTER_EGG__`;
    setStatus("🍝 You found it.", "ok");
    return;
  }

  document.getElementById("card").style.display = "block";
  document.getElementById("easterEgg").style.display = "none";

  // Cycling pasta emojis while loading
  const emojis = ["🍝","🍖","🍅","🧀","🧄"];
  let ei = 0;
  const anim = setInterval(() => {
    setStatus(emojis[ei++ % emojis.length] + "  Simmering data for " + city + "…", "loading");
  }, 200);

  fetch("/weather?city=" + encodeURIComponent(city))
    .then(r => r.json())
    .then(d => {
      clearInterval(anim);
      if (d.error) { setStatus("❌ " + d.error, "err"); return; }

      // Update served counter
      served++;
      document.getElementById("counter").textContent =
        served + " meatball" + (served===1?"":"s") + " served this session";

      // Apply dynamic card color
      const card = document.getElementById("card");
      card.style.background = d.card_bg;
      document.getElementById("cityLine").style.color = d.accent;

      document.getElementById("icon").textContent     = ICONS[iconKey(d.desc)];
      document.getElementById("tempC").textContent    = d.temp_c + "°C";
      document.getElementById("tempF").textContent    = d.temp_f + "°F";
      document.getElementById("cityLine").textContent = d.city + ", " + d.country;
      document.getElementById("descLine").textContent = d.desc;
      document.getElementById("feels").textContent    = d.feels_like_c + "°C";
      document.getElementById("humidity").textContent = d.humidity + "%";
      document.getElementById("wind").textContent     = d.wind_kmph + " km/h " + d.wind_dir;
      document.getElementById("visibility").textContent = d.visibility + " km";
      document.getElementById("uv").textContent       = d.uv_index;

      // Meatball-o-meter
      const mrow = document.getElementById("meterRow");
      mrow.style.display = "flex";
      document.getElementById("meterBalls").textContent = "🍝".repeat(d.rating) + "⬜".repeat(5-d.rating);
      document.getElementById("meterText").textContent  = d.rating_label;

      // Nonna
      const nonna = document.getElementById("nonna");
      nonna.style.display = "block";
      nonna.textContent = d.nonna;

      const now = new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
      document.getElementById("updated").textContent = now;

      // Refresh wisdom quote
      document.getElementById("wisdom").textContent = d.wisdom;

      // Nearby meatball spots
      const spotsSection = document.getElementById("spotsSection");
      const spotsList    = document.getElementById("spotsList");
      spotsSection.style.display = "block";
      if (!d.spots || d.spots.length === 0) {
        spotsList.innerHTML = '<div class="spots-empty">😔 No meatball spots found nearby. Consider moving.</div>';
      } else {
        const typeIcon = t => {
          if (t === "fast_food") return "🍟";
          if (t === "restaurant") return "🍽️";
          if (t === "shop") return "🛒";
          return "📍";
        };
        const distLabel = m => m < 1000 ? m + " m" : (m/1000).toFixed(1) + " km";
        spotsList.innerHTML = d.spots.map(s => `
          <div class="spot-item">
            <div class="spot-icon">${typeIcon(s.type)}</div>
            <div>
              <div class="spot-name">${s.name}</div>
              <div class="spot-meta">${[s.cuisine, s.address].filter(Boolean).join(" · ") || s.type}</div>
              <div class="spot-dist">📍 ${distLabel(s.distance_m)} away</div>
            </div>
          </div>`).join("");
      }

      setStatus("🍝 Buon appetito! Served at " + now, "ok");
    })
    .catch(e => { clearInterval(anim); setStatus("❌ " + e, "err"); });
}

document.getElementById("cityInput").addEventListener("keydown", e => {
  if (e.key === "Enter") doSearch();
});

window.onload = () => {
  const city = document.body.dataset.city || "Amsterdam";
  document.getElementById("cityInput").value = city;
  doSearch();
};
</script>
</body>
</html>
"""


# ── HTTP handler ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        global _meatballs_served
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/weather":
            params = urllib.parse.parse_qs(parsed.query)
            city   = params.get("city", [DEFAULT_CITY])[0]
            data   = fetch_weather(city)

            if "error" not in data:
                with _meatballs_lock:
                    _meatballs_served += 1
                rating, label = meatball_rating(data["temp_c"], data["desc"], data["wind_kmph"])
                card_bg, accent = card_colors(data["temp_c"])
                spots = fetch_meatball_spots(city)
                data.update({
                    "rating":       rating,
                    "rating_label": label,
                    "nonna":        nonna_verdict(data["temp_c"]),
                    "wisdom":       pasta_wisdom(),
                    "card_bg":      card_bg,
                    "accent":       accent,
                    "spots":        spots,
                })

            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch":
            page = LUNCH_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        elif parsed.path == "/lunch/state":
            body = json.dumps(lunch_agent.snapshot()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/lunchers":
            params = urllib.parse.parse_qs(parsed.query)
            n      = int(params.get("n", [lunch_agent._luncher_count])[0])
            body   = json.dumps(lunch_agent.set_lunchers(n)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/agenda":
            params = urllib.parse.parse_qs(parsed.query)
            person = params.get("person", [""])[0]
            day    = params.get("day",    ["MA"])[0]
            body   = json.dumps(lunch_agent.toggle_agenda(person, day)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/vote":
            params = urllib.parse.parse_qs(parsed.query)
            dish   = params.get("dish", [""])[0]
            body   = json.dumps(lunch_agent.vote_poll(dish)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/scan":
            body = json.dumps(lunch_agent.scan_inventory()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/order":
            params = urllib.parse.parse_qs(parsed.query)
            items  = params.get("items", [])
            body   = json.dumps(lunch_agent.order_picnic(items)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/training":
            params = urllib.parse.parse_qs(parsed.query)
            tip_id = int(params.get("tip_id", [1])[0])
            body   = json.dumps(lunch_agent.answer_training(tip_id)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/request":
            params = urllib.parse.parse_qs(parsed.query)
            name   = params.get("name", [""])[0]
            who    = params.get("who",  ["Anoniem"])[0]
            body   = json.dumps(lunch_agent.add_product_request(name, who)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/request/vote":
            params = urllib.parse.parse_qs(parsed.query)
            req_id = int(params.get("id", [0])[0])
            body   = json.dumps(lunch_agent.vote_product_request(req_id)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/complaint":
            params = urllib.parse.parse_qs(parsed.query)
            text   = params.get("text", ["..."])[0]
            body   = json.dumps(lunch_agent.submit_complaint(text)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/mood":
            params = urllib.parse.parse_qs(parsed.query)
            person = params.get("person", ["Anoniem"])[0]
            score  = int(params.get("score", [3])[0])
            body   = json.dumps(lunch_agent.set_mood(person, score)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/oracle":
            params   = urllib.parse.parse_qs(parsed.query)
            question = params.get("q", ["Wat is het antwoord?"])[0]
            body     = json.dumps(lunch_agent.ask_oracle(question)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/lunch/spin":
            body = json.dumps(lunch_agent.spin_slot_machine()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            # Inject values into the HTML template
            page = (HTML_TEMPLATE
                .replace("__DEFAULT_CITY__", DEFAULT_CITY)
                .replace("__WISDOM__", pasta_wisdom())
                .replace("__EASTER_EGG__", EASTER_EGG_HTML)
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"\n  🍝  Meatball Weather Deluxe is simmering at {url}")
    print(f"  🍖  Default city: {DEFAULT_CITY}")
    print(f"  🥚  Psst: try typing 'meatball' as a city")
    print(f"  ✋  Press Ctrl+C to stop\n")
    if _HAS_BROWSER and HOST == "127.0.0.1":
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  👋  Arrivederci! ({_meatballs_served} meatballs served)\n")


if __name__ == "__main__":
    run()
