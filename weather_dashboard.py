#!/usr/bin/env python3
"""
🌤️  ASCII Weather Dashboard
Fetches weather from wttr.in and renders a colorful terminal display.
"""

import json
import math
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


def geocode_city(city: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a city using Nominatim (OSM). Returns None on failure."""
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(city)}&format=json&limit=1"
    )
    headers = {"User-Agent": "MeatballWeatherApp/1.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            results = json.loads(r.read())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


def fetch_meatball_spots(city: str, radius_m: int = 5000) -> list[dict]:
    """Find meatball-related restaurants and stores near a city via Overpass API.

    Searches for Italian restaurants, meatball joints, Swedish furniture stores
    (IKEA meatballs!), and any venue with meatball in the name — within radius_m metres.
    Returns a list of dicts with keys: name, type, address, distance_m, osm_id.
    """
    coords = geocode_city(city)
    if not coords:
        return []
    lat, lon = coords

    # Overpass QL: cast a wide net for meatball-adjacent venues
    query = f"""
[out:json][timeout:15];
(
  node["amenity"="restaurant"]["cuisine"~"italian|pizza|pasta|mediterranean",i](around:{radius_m},{lat},{lon});
  node["amenity"="fast_food"]["cuisine"~"italian|pizza|pasta",i](around:{radius_m},{lat},{lon});
  node["amenity"="restaurant"]["name"~"meatball|spaghetti|pasta|noodle|trattoria|osteria|ristorante",i](around:{radius_m},{lat},{lon});
  node["shop"]["name"~"meatball|ikea",i](around:{radius_m},{lat},{lon});
  node["amenity"~"restaurant|fast_food"]["name"~"ikea",i](around:{radius_m},{lat},{lon});
);
out body 20;
""".strip()

    url = "https://overpass-api.de/api/interpreter"
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("User-Agent", "MeatballWeatherApp/1.0")
        with urllib.request.urlopen(req, timeout=20) as r:
            result = json.loads(r.read())
    except Exception:
        return []

    spots = []
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue

        # Build a short address
        addr_parts = [
            tags.get("addr:street", ""),
            tags.get("addr:housenumber", ""),
            tags.get("addr:city", ""),
        ]
        address = " ".join(p for p in addr_parts if p).strip() or None

        cuisine = tags.get("cuisine", "")
        amenity = tags.get("amenity", tags.get("shop", "place"))

        # Rough distance from city centre (haversine)
        dlat = math.radians(el.get("lat", lat) - lat)
        dlon = math.radians(el.get("lon", lon) - lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(el.get("lat", lat))) * math.sin(dlon/2)**2
        distance_m = int(6371000 * 2 * math.asin(math.sqrt(a)))

        spots.append({
            "name":       name,
            "type":       amenity,
            "cuisine":    cuisine,
            "address":    address,
            "distance_m": distance_m,
            "osm_id":     el.get("id"),
        })

    # Sort by distance, deduplicate by name, cap at 10
    seen = set()
    unique = []
    for s in sorted(spots, key=lambda x: x["distance_m"]):
        if s["name"].lower() not in seen:
            seen.add(s["name"].lower())
            unique.append(s)
        if len(unique) >= 10:
            break

    return unique


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
