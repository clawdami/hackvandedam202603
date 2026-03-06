#!/usr/bin/env python3
"""
🌤️  ASCII Weather Dashboard
Fetches weather from wttr.in and renders a colorful terminal display.
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime

COLORS = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "cyan":   "\033[96m",
    "yellow": "\033[93m",
    "blue":   "\033[94m",
    "green":  "\033[92m",
    "red":    "\033[91m",
    "white":  "\033[97m",
    "gray":   "\033[90m",
}

WEATHER_ICONS = {
    "sunny":   "☀️ ",
    "cloudy":  "☁️ ",
    "rain":    "🌧️ ",
    "snow":    "❄️ ",
    "thunder": "⛈️ ",
    "fog":     "🌫️ ",
    "wind":    "💨 ",
    "default": "🌡️ ",
}


def fetch_weather(city: str) -> dict:
    """Fetch current weather from wttr.in (free, no API key needed).

    Tries HTTPS first; falls back to HTTP if SSL handshake fails.
    Retries up to 3 times with increasing timeouts.
    """
    encoded = urllib.parse.quote(city)
    attempts = [
        (f"https://wttr.in/{encoded}?format=j1", 15),
        (f"https://wttr.in/{encoded}?format=j1", 20),
        (f"http://wttr.in/{encoded}?format=j1",  20),   # HTTP fallback
    ]
    last_error = "unknown error"
    for url, timeout in attempts:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                data = json.loads(r.read())
            current = data["current_condition"][0]
            area    = data["nearest_area"][0]
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
            last_error = str(e)
            continue
    return {"error": last_error}


def get_icon(desc: str) -> str:
    """Return a weather emoji string for the given description."""
    d = desc.lower()
    if "thunder" in d:                          return WEATHER_ICONS["thunder"]
    if "snow" in d or "blizzard" in d:          return WEATHER_ICONS["snow"]
    if "rain" in d or "drizzle" in d or "shower" in d: return WEATHER_ICONS["rain"]
    if "fog" in d or "mist" in d:               return WEATHER_ICONS["fog"]
    if "cloud" in d or "overcast" in d:         return WEATHER_ICONS["cloudy"]
    if "wind" in d:                             return WEATHER_ICONS["wind"]
    if "sun" in d or "clear" in d:              return WEATHER_ICONS["sunny"]
    return WEATHER_ICONS["default"]


def render_dashboard(w: dict):
    c = COLORS
    width = 50
    line = f"{c['cyan']}{'─' * width}{c['reset']}"
    now  = datetime.now().strftime("%A, %d %b %Y  %H:%M")

    print(f"\n{c['bold']}{c['cyan']}{'─' * width}{c['reset']}")
    print(f"{c['bold']}{c['yellow']}  🌍 Weather Dashboard  {c['gray']}{now}{c['reset']}")
    print(line)
    print(f"  {c['bold']}{c['white']}📍 {w['city']}, {w['country']}{c['reset']}")
    print(f"  {get_icon(w['desc'])}{c['bold']}{c['yellow']}{w['desc']}{c['reset']}")
    print(line)
    print(f"  {c['cyan']}🌡️  Temperature:  {c['bold']}{c['yellow']}{w['temp_c']}°C  /  {w['temp_f']}°F{c['reset']}")
    print(f"  {c['cyan']}🤔 Feels like:  {c['bold']}{w['feels_like_c']}°C{c['reset']}")
    print(f"  {c['blue']}💧 Humidity:    {c['bold']}{w['humidity']}%{c['reset']}")
    print(f"  {c['green']}💨 Wind:        {c['bold']}{w['wind_kmph']} km/h {w['wind_dir']}{c['reset']}")
    print(f"  {c['gray']}👁️  Visibility:  {c['bold']}{w['visibility']} km{c['reset']}")
    print(f"  {c['red']}☀️  UV Index:    {c['bold']}{w['uv_index']}{c['reset']}")
    print(f"{c['cyan']}{'─' * width}{c['reset']}\n")


def main():
    city = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Amsterdam"
    print(f"Fetching weather for {city}...")
    data = fetch_weather(city)
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        sys.exit(1)
    render_dashboard(data)


if __name__ == "__main__":
    main()
