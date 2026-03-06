#!/usr/bin/env python3
"""
🌤️  ASCII Weather Dashboard
Fetches weather from wttr.in and renders a colorful terminal display.
"""

import urllib.request
import json
import sys
from datetime import datetime

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "cyan": "\033[96m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "red": "\033[91m",
    "white": "\033[97m",
    "gray": "\033[90m",
}

WEATHER_ICONS = {
    "sunny": "☀️ ",
    "cloudy": "☁️ ",
    "rain": "🌧️ ",
    "snow": "❄️ ",
    "thunder": "⛈️ ",
    "fog": "🌫️ ",
    "wind": "💨 ",
    "default": "🌡️ ",
}

WMO_CODES = {
    0: ("Clear sky", "sunny"),
    1: ("Mainly clear", "sunny"),
    2: ("Partly cloudy", "cloudy"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Icy fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Heavy drizzle", "rain"),
    61: ("Slight rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    71: ("Slight snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    80: ("Rain showers", "rain"),
    81: ("Heavy showers", "rain"),
    95: ("Thunderstorm", "thunder"),
    99: ("Thunderstorm + hail", "thunder"),
}


def fetch_weather(city: str) -> dict:
    """Fetch weather data from Open-Meteo (free, no API key needed)."""
    # First get coordinates from wttr.in
    geo_url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    try:
        import urllib.parse
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        return {
            "city": area["areaName"][0]["value"],
            "country": area["country"][0]["value"],
            "temp_c": int(current["temp_C"]),
            "temp_f": int(current["temp_F"]),
            "feels_like_c": int(current["FeelsLikeC"]),
            "humidity": int(current["humidity"]),
            "wind_kmph": int(current["windspeedKmph"]),
            "wind_dir": current["winddir16Point"],
            "desc": current["weatherDesc"][0]["value"],
            "visibility": int(current["visibility"]),
            "uv_index": int(current["uvIndex"]),
        }
    except Exception as e:
        return {"error": str(e)}


def get_icon(desc: str) -> str:
    desc_lower = desc.lower()
    if "sun" in desc_lower or "clear" in desc_lower:
        return WEATHER_ICONS["sunny"]
    elif "thunder" in desc_lower:
        return WEATHER_ICONS["thunder"]
    elif "snow" in desc_lower or "blizzard" in desc_lower:
        return WEATHER_ICONS["snow"]
    elif "rain" in desc_lower or "drizzle" in desc_lower or "shower" in desc_lower:
        return WEATHER_ICONS["rain"]
    elif "fog" in desc_lower or "mist" in desc_lower:
        return WEATHER_ICONS["fog"]
    elif "cloud" in desc_lower or "overcast" in desc_lower:
        return WEATHER_ICONS["cloudy"]
    elif "wind" in desc_lower:
        return WEATHER_ICONS["wind"]
    return WEATHER_ICONS["default"]


def render_dashboard(w: dict):
    c = COLORS
    width = 50
    line = f"{c['cyan']}{'─' * width}{c['reset']}"

    icon = get_icon(w["desc"])
    now = datetime.now().strftime("%A, %d %b %Y  %H:%M")

    print(f"\n{c['bold']}{c['cyan']}{'─' * width}{c['reset']}")
    print(f"{c['bold']}{c['yellow']}  🌍 Weather Dashboard  {c['gray']}{now}{c['reset']}")
    print(line)
    print(f"  {c['bold']}{c['white']}📍 {w['city']}, {w['country']}{c['reset']}")
    print(f"  {icon}{c['bold']}{c['yellow']}{w['desc']}{c['reset']}")
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
    import urllib.parse
    main()
