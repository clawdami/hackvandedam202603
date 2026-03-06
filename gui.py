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
import webbrowser
from http.server import BaseHTTPRequestHandler

from weather_dashboard import fetch_weather

PORT = 7878
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
  <div class="counter" id="counter">0 meatballs served this session</div>
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
                data.update({
                    "rating":       rating,
                    "rating_label": label,
                    "nonna":        nonna_verdict(data["temp_c"]),
                    "wisdom":       pasta_wisdom(),
                    "card_bg":      card_bg,
                    "accent":       accent,
                })

            body = json.dumps(data).encode()
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
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\n  🍝  Meatball Weather Deluxe is simmering at {url}")
    print(f"  🍖  Default city: {DEFAULT_CITY}")
    print(f"  🥚  Psst: try typing 'meatball' as a city")
    print(f"  ✋  Press Ctrl+C to stop\n")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  👋  Arrivederci! ({_meatballs_served} meatballs served)\n")


if __name__ == "__main__":
    run()
