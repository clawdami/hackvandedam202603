# hackvandedam202603

Weather dashboard project built at **Hack van de Dam 2026** 🌊

## The Team

- **Jonathan** — The mastermind behind the project. Keeps everything running and knows where all the bodies (and API keys) are buried. 🧠
- **Philip** — The quiet powerhouse. Writes clean code, asks the right questions, and somehow always has snacks. 🍪
- **Euan** — Chaos engineer extraordinaire. If it breaks, Euan probably asked it the wrong question. Also the one who stress-tested the bot the most. 😄

## What It Does

A colorful ASCII weather dashboard that fetches live weather data (no API key needed!) and displays it right in your terminal — or via a meatball-themed web GUI.

## Usage

```bash
python3 weather_dashboard.py Amsterdam
```

## Features

- 🌤️ **ASCII weather dashboard** — colorful terminal output
- 🍝 **Meatball-themed web GUI** — browser-based, opens automatically
- 🍝 **Meatball-o-meter** — rates weather 1–5 meatballs
- 👵 **Nonna's Verdict** — grandma weighs in on the temperature
- 📍 **Nearby Meatball Spots** — finds Italian restaurants & meatball joints near your searched city (powered by OpenStreetMap/Overpass)
- 🥚 **Easter egg** — type `meatball` as a city

## Web GUI

```bash
python3 gui.py Amsterdam
# Opens http://localhost:7878 in your browser
```

Zero dependencies — pure Python stdlib only.

## Nearby Meatball Spots

When you search a city in the GUI, it automatically finds nearby Italian restaurants, pasta joints, and meatball-adjacent venues using the free Overpass API (OpenStreetMap). No API key needed.
