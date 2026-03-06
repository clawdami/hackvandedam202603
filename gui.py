#!/usr/bin/env python3
"""
🍝 Meatball Weather Dashboard — GUI Edition 🍝
Launches a local web server and opens the app in your browser.
Run with: python3 gui.py [city]
"""

import http.server
import json
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler

PORT = 7878
DEFAULT_CITY = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Amsterdam"


# ── Weather fetch ──────────────────────────────────────────────────────────────

def fetch_weather(city: str) -> dict:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        return {
            "city":         area["areaName"][0]["value"],
            "country":      area["country"][0]["value"],
            "temp_c":       int(current["temp_C"]),
            "temp_f":       int(current["temp_F"]),
            "feels_like_c": int(current["FeelsLikeC"]),
            "humidity":     int(current["humidity"]),
            "wind_kmph":    int(current["windspeedKmph"]),
            "wind_dir":     current["winddir16Point"],
            "desc":         current["weatherDesc"][0]["value"],
            "visibility":   int(current["visibility"]),
            "uv_index":     int(current["uvIndex"]),
        }
    except Exception as e:
        return {"error": str(e)}


# ── HTML page ──────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🍝 Meatball Weather</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');

  :root {
    --bg-dark:    #2B1A0E;
    --bg-mid:     #3D2310;
    --bg-card:    #4A2C15;
    --sauce:      #C0392B;
    --orange:     #E67E22;
    --cheese:     #F5CBA7;
    --meatball:   #8B4513;
    --basil:      #27AE60;
    --cream:      #FAD7A0;
    --parchment:  #A07850;
    --spicy:      #FF6B35;
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
    padding: 0 0 40px;
  }

  /* ── Header ── */
  header {
    width: 100%;
    background: var(--sauce);
    text-align: center;
    padding: 18px 16px 10px;
  }
  header h1 { font-size: 1.8rem; color: var(--cheese); letter-spacing: 2px; }
  header p  { font-size: 0.8rem; color: var(--cream); opacity: .75; margin-top: 4px; }

  /* ── Meatball art ── */
  .art {
    background: var(--bg-mid);
    width: 100%;
    text-align: center;
    padding: 10px 0;
    font-size: 0.85rem;
    color: var(--meatball);
    line-height: 1.6;
    letter-spacing: 1px;
  }

  /* ── Search ── */
  .search {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 0;
    padding: 0 16px;
    width: 100%;
    max-width: 520px;
  }
  .search label { color: var(--parchment); font-size: 0.9rem; white-space: nowrap; }
  .search input {
    flex: 1;
    background: var(--bg-card);
    border: 2px solid var(--meatball);
    border-radius: 4px;
    color: var(--cheese);
    font-family: inherit;
    font-size: 1rem;
    padding: 8px 12px;
    outline: none;
    transition: border-color .2s;
  }
  .search input:focus { border-color: var(--orange); }
  .search button {
    background: var(--sauce);
    border: none;
    border-radius: 4px;
    color: var(--cheese);
    cursor: pointer;
    font-family: inherit;
    font-size: 0.95rem;
    font-weight: bold;
    padding: 9px 16px;
    transition: background .2s;
    white-space: nowrap;
  }
  .search button:hover { background: var(--spicy); }

  /* ── Card ── */
  .card {
    background: var(--bg-card);
    border: 2px solid var(--meatball);
    border-radius: 8px;
    margin: 16px 16px 0;
    max-width: 520px;
    width: 100%;
    overflow: hidden;
  }

  .card-top {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px 20px 8px;
  }
  .weather-icon { font-size: 3.6rem; line-height: 1; }
  .temp-block {}
  .temp-c { font-size: 2.4rem; font-weight: bold; color: var(--cheese); }
  .temp-f { font-size: 0.9rem; color: var(--parchment); }

  .city-line {
    padding: 4px 20px 2px;
    font-size: 1.25rem;
    font-weight: bold;
    color: var(--orange);
  }
  .desc-line {
    padding: 0 20px 12px;
    font-size: 0.85rem;
    color: var(--parchment);
  }

  hr { border: none; border-top: 1px solid var(--meatball); margin: 0 20px; }

  .stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 14px 16px 16px;
  }
  .stat {
    background: var(--bg-mid);
    border-radius: 6px;
    padding: 10px 12px;
  }
  .stat-label { font-size: 0.75rem; color: var(--parchment); }
  .stat-value { font-size: 1.05rem; font-weight: bold; color: var(--cheese); margin-top: 2px; }

  /* ── Status bar ── */
  .status {
    font-size: 0.78rem;
    color: var(--parchment);
    margin-top: 14px;
    text-align: center;
  }
  .status.loading { color: var(--orange); }
  .status.ok      { color: var(--basil); }
  .status.err     { color: var(--sauce); }

  /* ── Spinner ── */
  .spinner { display: none; }
  .spinner.active {
    display: inline-block;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Spaghetti divider ── */
  .spaghetti {
    font-size: 0.7rem;
    letter-spacing: 3px;
    color: var(--meatball);
    margin: 18px 0 4px;
    text-align: center;
  }
</style>
</head>
<body>

<header>
  <h1>🍝 MEATBALL WEATHER 🍝</h1>
  <p>Serving forecasts since the dawn of pasta</p>
</header>

<div class="art">
<pre>   ( ●      ● )   
  (  🍝  &amp;  🍝  ) 
 ( ● M E T E O ● )
  (  ~~ spaghetti ~~  )
   (___mmmmmm___)  </pre>
</div>

<div class="search">
  <label>📍</label>
  <input id="cityInput" type="text" placeholder="Enter city…" />
  <button onclick="doSearch()">🍖 FETCH</button>
</div>

<div class="card" id="card">
  <div class="card-top">
    <div class="weather-icon" id="icon">🍝</div>
    <div class="temp-block">
      <div class="temp-c" id="tempC">--°C</div>
      <div class="temp-f" id="tempF">--°F</div>
    </div>
  </div>
  <div class="city-line" id="cityLine">Loading…</div>
  <div class="desc-line" id="descLine"></div>
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

<div class="spaghetti">~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~</div>
<div class="status" id="status">🍝 Ready to serve weather</div>

<script>
const ICONS = {
  sunny:   "☀️", cloudy: "☁️", rain: "🌧️",
  snow:    "❄️", thunder: "⛈️", fog: "🌫️",
  wind:    "💨", default: "🌡️"
};

function iconKey(desc) {
  const d = desc.toLowerCase();
  if (d.includes("thunder"))                          return "thunder";
  if (d.includes("snow") || d.includes("blizzard"))  return "snow";
  if (d.includes("rain") || d.includes("drizzle") || d.includes("shower")) return "rain";
  if (d.includes("fog")  || d.includes("mist"))      return "fog";
  if (d.includes("cloud") || d.includes("overcast")) return "cloudy";
  if (d.includes("wind"))                             return "wind";
  if (d.includes("sun")  || d.includes("clear"))     return "sunny";
  return "default";
}

function setStatus(msg, cls) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status " + (cls || "");
}

function doSearch() {
  const city = document.getElementById("cityInput").value.trim();
  if (!city) return;
  setStatus("🍖 Simmering data for " + city + "…", "loading");
  fetch("/weather?city=" + encodeURIComponent(city))
    .then(r => r.json())
    .then(d => {
      if (d.error) { setStatus("❌ " + d.error, "err"); return; }
      document.getElementById("icon").textContent      = ICONS[iconKey(d.desc)];
      document.getElementById("tempC").textContent     = d.temp_c + "°C";
      document.getElementById("tempF").textContent     = d.temp_f + "°F";
      document.getElementById("cityLine").textContent  = d.city + ", " + d.country;
      document.getElementById("descLine").textContent  = d.desc;
      document.getElementById("feels").textContent     = d.feels_like_c + "°C";
      document.getElementById("humidity").textContent  = d.humidity + "%";
      document.getElementById("wind").textContent      = d.wind_kmph + " km/h " + d.wind_dir;
      document.getElementById("visibility").textContent= d.visibility + " km";
      document.getElementById("uv").textContent        = d.uv_index;
      const now = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
      document.getElementById("updated").textContent   = now;
      setStatus("🍝 Buon appetito! Served at " + now, "ok");
    })
    .catch(e => setStatus("❌ " + e, "err"));
}

// Enter key to search
document.getElementById("cityInput").addEventListener("keydown", e => {
  if (e.key === "Enter") doSearch();
});

// Auto-load default city
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
    def log_message(self, *a):
        pass  # silence request logs

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/weather":
            params = urllib.parse.parse_qs(parsed.query)
            city = params.get("city", [DEFAULT_CITY])[0]
            data = fetch_weather(city)
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            # Inject default city into page
            page = HTML.replace(
                "<body>",
                f'<body data-city="{DEFAULT_CITY}">'
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
    print(f"\n  🍝  Meatball Weather is simmering at {url}")
    print(f"  🍖  Default city: {DEFAULT_CITY}")
    print(f"  ✋  Press Ctrl+C to stop\n")
    # Open browser after a short delay
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  👋  Arrivederci!\n")


if __name__ == "__main__":
    run()
