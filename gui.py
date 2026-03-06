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

from weather_dashboard import fetch_weather, fetch_meatball_spots
import lunch_agent

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


LUNCH_HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🥙 THE MEATBALL</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');
  :root{--bg:#1A2A1A;--bg-card:#243524;--green:#4CAF50;--lime:#8BC34A;--yellow:#FFC107;--red:#F44336;--cream:#F5F0E8;--muted:#8A9E8A;--border:#3A5A3A;--sauce:#C0392B;--gold:#FFD700;--purple:#9B59B6;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--cream);font-family:'Courier Prime','Courier New',monospace;min-height:100vh;padding-bottom:40px;}
  header{background:#2D4A2D;border-bottom:2px solid var(--green);padding:14px 20px;display:flex;align-items:center;gap:16px;}
  header h1{font-size:1.4rem;color:var(--lime);}
  header p{font-size:0.72rem;color:var(--muted);margin-top:2px;}
  .nav-link{margin-left:auto;color:var(--muted);text-decoration:none;font-size:0.82rem;border:1px solid var(--border);padding:5px 10px;border-radius:4px;}
  .nav-link:hover{color:var(--lime);border-color:var(--lime);}
  .grid{display:grid;gap:12px;padding:12px 14px;max-width:1100px;margin:0 auto;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));}
  .card{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;overflow:hidden;}
  .card.wide{grid-column:span 2;}
  .card-header{background:#2D4A2D;padding:9px 13px;font-size:0.88rem;font-weight:bold;color:var(--lime);display:flex;align-items:center;gap:8px;}
  .card-body{padding:13px;}
  .big-num{text-align:center;font-size:3rem;font-weight:bold;color:var(--lime);margin:8px 0 2px;}
  .sub{text-align:center;font-size:0.76rem;color:var(--muted);margin-bottom:12px;}
  .btn-row{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;}
  .btn{background:#2D4A2D;border:1px solid var(--border);border-radius:4px;color:var(--cream);cursor:pointer;font-family:inherit;font-size:0.88rem;padding:7px 12px;transition:background .15s;}
  .btn:hover{background:var(--green);color:#000;}
  .btn.ok{background:var(--green);color:#000;font-weight:bold;}
  .btn.ok:hover{background:var(--lime);}
  .btn.bad{background:var(--sauce);color:var(--cream);}
  .btn.bad:hover{background:#e74c3c;}
  .btn.gold{background:var(--gold);color:#000;font-weight:bold;}
  .btn.purple{background:var(--purple);color:#fff;font-weight:bold;}
  /* Agenda */
  .agenda-table{width:100%;border-collapse:collapse;font-size:0.82rem;margin-top:6px;}
  .agenda-table th{color:var(--muted);padding:4px 6px;text-align:center;border-bottom:1px solid var(--border);}
  .agenda-table td{padding:5px 6px;text-align:center;border-bottom:1px solid #1A2A1A;}
  .agenda-table td:first-child{text-align:left;color:var(--cream);font-weight:bold;}
  .day-check{cursor:pointer;font-size:1.1rem;}
  .today-col{background:rgba(139,195,74,0.1);}
  /* Budget */
  .brow{display:flex;justify-content:space-between;margin-bottom:5px;font-size:0.84rem;}
  .bar-bg{width:100%;height:11px;background:#1A2A1A;border-radius:5px;overflow:hidden;margin-bottom:7px;}
  .bar{height:100%;border-radius:5px;transition:width .4s;}
  .spaarball{background:#1A2A1A;border-radius:6px;padding:10px 12px;margin-top:8px;text-align:center;}
  .spaarball .euro{font-size:2rem;color:var(--gold);}
  /* Inventory */
  .inv-item{display:flex;align-items:center;gap:7px;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.83rem;}
  .inv-item:last-child{border-bottom:none;}
  .inv-emoji{font-size:1.1rem;width:26px;text-align:center;}
  .inv-name{flex:1;}
  .inv-qty{font-weight:bold;min-width:36px;text-align:right;}
  .inv-unit{color:var(--muted);font-size:0.72rem;min-width:26px;}
  .inv-low{color:var(--red);}
  .inv-ok{color:var(--green);}
  /* Picnic */
  .picnic-item{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.83rem;}
  .picnic-item:last-child{border-bottom:none;}
  /* Poll */
  .poll-item{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.83rem;cursor:pointer;transition:background .12s;}
  .poll-item:hover{background:#1A2A1A;border-radius:4px;padding-left:4px;}
  .poll-item:last-child{border-bottom:none;}
  .poll-bar-bg{flex:1;height:8px;background:#1A2A1A;border-radius:4px;overflow:hidden;}
  .poll-bar{height:100%;background:var(--green);border-radius:4px;transition:width .4s;}
  .poll-votes{font-size:0.72rem;color:var(--muted);min-width:28px;text-align:right;}
  /* Training */
  .tip-card{background:#1A2A1A;border-radius:5px;padding:9px 11px;margin-bottom:7px;cursor:pointer;transition:background .14s;display:flex;align-items:flex-start;gap:8px;}
  .tip-card:hover{background:#2D4A2D;}
  /* Product Requests */
  .req-item{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);font-size:0.83rem;}
  .req-item:last-child{border-bottom:none;}
  .req-status{font-size:0.7rem;margin-left:auto;white-space:nowrap;}
  /* Mood */
  .mood-btn{font-size:1.4rem;cursor:pointer;padding:4px 8px;border-radius:4px;border:2px solid transparent;transition:border-color .15s;}
  .mood-btn:hover,.mood-btn.active{border-color:var(--lime);}
  .mood-avg{text-align:center;font-size:2.5rem;margin:8px 0 4px;}
  /* Oracle */
  .oracle-box{background:#1A2A1A;border-radius:8px;padding:14px;text-align:center;margin-top:10px;min-height:60px;}
  .oracle-ritual{font-size:0.75rem;color:var(--muted);font-style:italic;margin-bottom:6px;}
  .oracle-msg{font-size:0.9rem;color:var(--purple);font-weight:bold;}
  /* Slot machine */
  .reels{display:flex;justify-content:center;gap:12px;font-size:3rem;margin:10px 0;background:#1A2A1A;padding:12px;border-radius:8px;}
  .reel{transition:transform .3s;}
  .spin-result{text-align:center;font-size:0.88rem;color:var(--yellow);font-weight:bold;min-height:20px;}
  /* Complaints */
  .complaint-item{padding:7px 0;border-bottom:1px solid var(--border);font-size:0.8rem;}
  .complaint-item:last-child{border-bottom:none;}
  .complaint-response{font-size:0.75rem;color:var(--muted);font-style:italic;margin-top:3px;}
  /* Leaderboard */
  .lb-item{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);font-size:0.85rem;}
  .lb-item:last-child{border-bottom:none;}
  .lb-rank{font-size:1.2rem;width:28px;}
  /* Input */
  .inp{background:#1A2A1A;border:1px solid var(--border);border-radius:4px;color:var(--cream);font-family:inherit;font-size:0.85rem;padding:7px 10px;width:100%;outline:none;}
  .inp:focus{border-color:var(--lime);}
  /* Nonna alert */
  .nonna-alert{border-radius:6px;padding:10px 12px;margin-bottom:10px;font-size:0.85rem;font-weight:bold;}
  /* Toast */
  #toast{position:fixed;bottom:18px;right:18px;background:var(--green);color:#000;padding:9px 14px;border-radius:6px;font-size:0.83rem;font-family:inherit;display:none;z-index:999;max-width:280px;}
  .msg{font-size:0.76rem;color:var(--lime);margin-top:7px;min-height:16px;}
  .badge{font-size:0.68rem;color:var(--muted);background:#1A2A1A;padding:2px 5px;border-radius:3px;margin-left:auto;}
  .picnic-link{display:inline-block;margin-top:8px;color:var(--lime);font-size:0.8rem;text-decoration:none;border:1px solid var(--border);padding:5px 10px;border-radius:4px;}
  .picnic-link:hover{border-color:var(--lime);}
  @keyframes slot-spin{0%{transform:translateY(-20px);opacity:0}100%{transform:translateY(0);opacity:1}}
  .reel.spinning{animation:slot-spin .3s ease-out;}
</style>
</head>
<body>
<header>
  <div><h1>🥙 THE MEATBALL</h1><p>Super Modern Lunch Dashboard voor de Lunch</p></div>
  <a class="nav-link" href="/">← Weer</a>
</header>
<div class="grid">

  <!-- Luncher Counter -->
  <div class="card">
    <div class="card-header">👥 Aantal Lunchers <span class="badge" id="weekBadge">week --</span></div>
    <div class="card-body">
      <div class="big-num" id="luncherCount">--</div>
      <div class="sub">mensen eten vandaag mee</div>
      <div class="btn-row">
        <button class="btn" onclick="chgLunch(-5)">−5</button>
        <button class="btn" onclick="chgLunch(-1)">−1</button>
        <button class="btn" onclick="chgLunch(+1)">+1</button>
        <button class="btn" onclick="chgLunch(+5)">+5</button>
      </div>
      <div class="msg" id="lunchMsg"></div>
    </div>
  </div>

  <!-- Budget -->
  <div class="card">
    <div class="card-header">💶 Budget (€120 cap)</div>
    <div class="card-body">
      <div id="nonnalert"></div>
      <div class="brow"><span>Uitgegeven</span><span id="budSpent">€--</span></div>
      <div class="brow"><span>Cap</span><span id="budCap">€--</span></div>
      <div class="bar-bg"><div class="bar" id="budBar" style="width:0%"></div></div>
      <div class="brow" style="font-weight:bold"><span>Resterend</span><span id="budRem">€--</span></div>
      <div class="spaarball">
        <div style="font-size:0.78rem;color:var(--muted);margin-bottom:4px">🏦 SpaarBall — budget over gaat hierheen</div>
        <div class="euro" id="spaarbBal">€--</div>
        <div style="font-size:0.7rem;color:var(--muted);margin-top:3px" id="spaarbEarn">SpaarPlan Biertafels · 1,23%</div>
      </div>
    </div>
  </div>

  <!-- Agenda -->
  <div class="card wide">
    <div class="card-header">📅 Lunch Agenda</div>
    <div class="card-body">
      <table class="agenda-table">
        <thead><tr><th>Naam</th><th id="th-MA">MA</th><th id="th-DI">DI</th><th id="th-WO">WO</th><th id="th-DO">DO</th><th id="th-VR">VR</th></tr></thead>
        <tbody id="agendaBody"></tbody>
      </table>
      <div class="msg" id="agendaMsg"></div>
    </div>
  </div>

  <!-- Leaderboard -->
  <div class="card">
    <div class="card-header">🏆 Lunch Leaderboard</div>
    <div class="card-body">
      <div id="leaderboard">Laden…</div>
    </div>
  </div>

  <!-- Sfeer-o-meter -->
  <div class="card">
    <div class="card-header">🌡️ Sfeer-o-meter</div>
    <div class="card-body">
      <div class="mood-avg" id="moodAvgEmoji">🤔</div>
      <div style="text-align:center;font-size:0.85rem;color:var(--muted);margin-bottom:12px" id="moodAvgLabel">Nog geen stemmen</div>
      <div style="font-size:0.78rem;color:var(--muted);margin-bottom:6px">Jouw naam:</div>
      <input class="inp" id="moodName" placeholder="Naam..." style="margin-bottom:8px">
      <div class="btn-row">
        <span class="mood-btn" onclick="voteMood(1)" title="Vreselijk">💀</span>
        <span class="mood-btn" onclick="voteMood(2)" title="Slecht">😞</span>
        <span class="mood-btn" onclick="voteMood(3)" title="Meh">😐</span>
        <span class="mood-btn" onclick="voteMood(4)" title="Goed">😊</span>
        <span class="mood-btn" onclick="voteMood(5)" title="GEWELDIG">🔥</span>
      </div>
      <div id="moodVotes" style="margin-top:10px;font-size:0.78rem;color:var(--muted)"></div>
      <div class="msg" id="moodMsg"></div>
    </div>
  </div>

  <!-- Inventory -->
  <div class="card">
    <div class="card-header">📦 Voorraad</div>
    <div class="card-body">
      <div id="invList">Laden…</div>
      <button class="btn ok" style="margin-top:9px;width:100%" onclick="scanInv()">📸 Scan voorraadla</button>
      <div class="msg" id="invMsg"></div>
    </div>
  </div>

  <!-- Picnic List -->
  <div class="card">
    <div class="card-header">🛒 Picnic Lijst</div>
    <div class="card-body">
      <div style="font-size:0.76rem;color:var(--muted);margin-bottom:8px">Automatisch op basis van lage voorraad</div>
      <div id="picnicList">Laden…</div>
      <button class="btn bad" style="margin-top:9px;width:100%" onclick="orderPicnic()">🛒 Bestel via Picnic</button>
      <a class="picnic-link" id="picnicCartLink" href="https://picnic.app" target="_blank" style="display:none">🔗 Open winkelmandje →</a>
      <div class="msg" id="picnicMsg"></div>
    </div>
  </div>

  <!-- Product Requests -->
  <div class="card">
    <div class="card-header">🛍️ Product Requests</div>
    <div class="card-body">
      <div style="font-size:0.76rem;color:var(--muted);margin-bottom:8px">Vraag een product aan — 3 stemmen = goedgekeurd!</div>
      <div style="display:flex;gap:6px;margin-bottom:8px">
        <input class="inp" id="reqName" placeholder="Product naam...">
        <input class="inp" id="reqWho" placeholder="Jouw naam" style="max-width:100px">
      </div>
      <button class="btn ok" onclick="submitRequest()" style="width:100%;margin-bottom:10px">➕ Aanvragen</button>
      <div id="reqList" style="font-size:0.82rem">Geen requests</div>
      <div class="msg" id="reqMsg"></div>
    </div>
  </div>

  <!-- Suggestion Poll -->
  <div class="card">
    <div class="card-header">💡 Lunch Poll — VORM POLL</div>
    <div class="card-body">
      <div style="font-size:0.76rem;color:var(--muted);margin-bottom:8px">Klik om te stemmen 👇</div>
      <div id="pollList">Laden…</div>
    </div>
  </div>

  <!-- Slot Machine 🎰 -->
  <div class="card">
    <div class="card-header">🎰 Wat Eten We? (Slot Machine)</div>
    <div class="card-body">
      <div class="reels" id="reels"><span id="r1">🍝</span><span id="r2">🍖</span><span id="r3">🍅</span></div>
      <div class="spin-result" id="spinResult">Druk op de knop om het lot te vragen</div>
      <button class="btn gold" style="width:100%;margin-top:10px;font-size:1rem" onclick="spinSlot()">🎰 DRAAIEN!</button>
    </div>
  </div>

  <!-- Meatball Oracle -->
  <div class="card">
    <div class="card-header">🔮 Meatball Oracle</div>
    <div class="card-body">
      <div style="font-size:0.76rem;color:var(--muted);margin-bottom:8px">Stel de Oracle een ja/nee vraag</div>
      <input class="inp" id="oracleQ" placeholder="Bijv: Mogen we pizza bestellen?" style="margin-bottom:8px">
      <button class="btn purple" style="width:100%" onclick="askOracle()">🔮 Vraag de Oracle</button>
      <div class="oracle-box" id="oracleBox" style="display:none">
        <div class="oracle-ritual" id="oracleRitual"></div>
        <div class="oracle-msg" id="oracleMsg"></div>
      </div>
    </div>
  </div>

  <!-- Complaint Box -->
  <div class="card">
    <div class="card-header">😤 Klachtenbus (anoniem)</div>
    <div class="card-body">
      <div style="font-size:0.76rem;color:var(--muted);margin-bottom:8px">Klaag hier. Niemand ziet het. (Behalve iedereen.)</div>
      <textarea class="inp" id="complaintText" rows="2" placeholder="Jouw klacht..." style="resize:none;margin-bottom:8px"></textarea>
      <button class="btn bad" style="width:100%;margin-bottom:10px" onclick="submitComplaint()">😤 Indienen</button>
      <div id="complaintList" style="font-size:0.8rem">Nog geen klachten. Indrukwekkend.</div>
    </div>
  </div>

  <!-- Order History -->
  <div class="card">
    <div class="card-header">📋 Bestelhistorie</div>
    <div class="card-body"><div id="orderHist" style="font-size:0.8rem;color:var(--muted)">Geen bestellingen</div></div>
  </div>

  <!-- Training Tool -->
  <div class="card">
    <div class="card-header">🎓 Training Tool</div>
    <div class="card-body">
      <div style="text-align:center;font-size:1.6rem;font-weight:bold;color:var(--yellow);margin-bottom:10px">⭐ <span id="trainScore">0</span> pts</div>
      <div id="trainTips">Laden…</div>
    </div>
  </div>

</div>
<div id="toast"></div>
<script>
let state = {};
function toast(msg,col){const el=document.getElementById("toast");el.textContent=msg;el.style.background=col||"var(--green)";el.style.display="block";setTimeout(()=>el.style.display="none",3500);}
function msg(id,txt,ms){const el=document.getElementById(id);if(!el)return;el.textContent=txt;if(ms)setTimeout(()=>{if(el.textContent===txt)el.textContent="";},ms);}
async function loadState(){const r=await fetch("/lunch/state");state=await r.json();render();}
function render(){
  document.getElementById("luncherCount").textContent=state.lunchers;
  document.getElementById("weekBadge").textContent="week "+state.week;
  // Nonna alert
  const na=state.budget.nonna_alert;
  const nael=document.getElementById("nonnalert");
  if(na){nael.innerHTML=`<div class="nonna-alert" style="background:${na.color}20;border-left:3px solid ${na.color};color:${na.color}">${na.level}<br><span style="font-weight:normal;font-size:0.8rem">${na.msg}</span></div>`;}
  else{nael.innerHTML="";}
  // Budget
  const b=state.budget;
  document.getElementById("budSpent").textContent="€"+b.spent.toFixed(2);
  document.getElementById("budCap").textContent="€"+b.cap.toFixed(2);
  document.getElementById("budRem").textContent="€"+b.remaining.toFixed(2);
  const bar=document.getElementById("budBar");
  bar.style.width=Math.min(b.pct_used,100)+"%";
  bar.style.background=b.pct_used>=80?"var(--red)":b.pct_used>=60?"var(--yellow)":"var(--green)";
  document.getElementById("spaarbBal").textContent="€"+b.spaarball.toFixed(2);
  document.getElementById("spaarbEarn").textContent="SpaarPlan Biertafels · "+b.spaarball_pct+"% · +€"+b.spaarball_earn.toFixed(2)+" dit jaar";
  // Agenda
  const tbody=document.getElementById("agendaBody");
  const days=state.weekdays;
  days.forEach(d=>{const th=document.getElementById("th-"+d);if(th)th.style.color=d===state.today?"var(--lime)":"";});
  tbody.innerHTML=Object.entries(state.agenda).map(([name,sched])=>
    `<tr><td>${name}</td>${days.map(d=>`<td class="${d===state.today?'today-col':''}">`+
    `<span class="day-check" onclick="toggleAgenda('${name}','${d}')">${sched[d]?"✅":"❌"}</span></td>`).join("")}</tr>`
  ).join("");
  // Leaderboard
  document.getElementById("leaderboard").innerHTML=state.leaderboard.map((p,i)=>{
    const medals=["🥇","🥈","🥉"];
    return `<div class="lb-item"><span class="lb-rank">${medals[i]||"👤"}</span><span style="flex:1">${p.name}</span><span style="color:var(--lime);font-weight:bold">${p.days} dagen</span></div>`;
  }).join("");
  // Mood
  const m=state.mood;
  document.getElementById("moodAvgEmoji").textContent=m.emoji||"🤔";
  document.getElementById("moodAvgLabel").textContent=m.avg?m.avg+" / 5 — "+m.label:"Nog geen stemmen";
  document.getElementById("moodVotes").innerHTML=Object.entries(m.votes||{}).map(([k,v])=>
    `<span style="margin-right:8px">${v.emoji} <b>${k}</b></span>`).join("");
  // Inventory
  document.getElementById("invList").innerHTML=state.inventory.map(i=>{
    const low=i.qty<i.min;
    return `<div class="inv-item"><span class="inv-emoji">${i.emoji}</span><span class="inv-name">${i.name}</span>`+
      `<span class="inv-qty ${low?'inv-low':'inv-ok'}">${i.qty}</span><span class="inv-unit">${i.unit}</span>`+
      `${low?'<span style="font-size:0.7rem;color:var(--red)">⚠️</span>':''}</div>`;
  }).join("");
  // Picnic list
  const pl=document.getElementById("picnicList");
  pl.innerHTML=!state.picnic_list||state.picnic_list.length===0
    ?'<div style="color:var(--green);font-size:0.82rem">✅ Voorraad prima</div>'
    :state.picnic_list.map(i=>`<div class="picnic-item"><span>${i.emoji}</span><span style="flex:1">${i.name}</span><span style="color:var(--yellow);font-size:0.8rem">+${i.needed} ${i.unit}</span></div>`).join("");
  // Product requests
  const rl=document.getElementById("reqList");
  rl.innerHTML=!state.product_requests||state.product_requests.length===0
    ?'<span style="color:var(--muted)">Geen requests</span>'
    :state.product_requests.map(r=>`<div class="req-item">`+
      `<span style="font-size:1.1rem">${r.emoji}</span>`+
      `<span style="flex:1"><b>${r.name}</b> <span style="color:var(--muted);font-size:0.75rem">— ${r.requester}</span></span>`+
      `<span style="cursor:pointer;margin-right:4px" onclick="voteRequest(${r.id})" title="Stem">👍 ${r.votes}</span>`+
      `<span class="req-status">${r.status}</span>`+
      `</div>`).join("");
  // Poll
  const poll=state.suggestion.poll||[];
  const maxV=Math.max(...poll.map(p=>p.votes),1);
  const winner=poll.reduce((a,b)=>b.votes>a.votes?b:a,poll[0]||{});
  document.getElementById("pollList").innerHTML=poll.map(p=>{
    const pct=Math.round((p.votes/maxV)*100);
    const isW=p.votes>0&&p.dish===winner.dish;
    return `<div class="poll-item" onclick="votePoll('${p.dish.replace(/'/g,"\\'")}')"><span>${p.emoji}</span>`+
      `<span style="flex:0 0 130px;font-size:0.8rem;${isW?'color:var(--gold);font-weight:bold':''}">${p.dish}</span>`+
      `<div class="poll-bar-bg"><div class="poll-bar" style="width:${pct}%;${isW?'background:var(--gold)':''}"></div></div>`+
      `<span class="poll-votes ${isW?'':'poll-votes'}">${p.votes}</span></div>`;
  }).join("");
  // Order history
  const oh=document.getElementById("orderHist");
  oh.innerHTML=!state.order_history||state.order_history.length===0?'Geen bestellingen'
    :state.order_history.slice().reverse().map(o=>`<div style="padding:4px 0;border-bottom:1px solid var(--border)">`+
      `<span style="color:var(--lime)">${o.time}</span> — ${o.items.join(", ")}<span style="color:var(--yellow);float:right">€${o.cost.toFixed(2)}</span></div>`
    ).join("");
  // Complaints
  document.getElementById("complaintList").innerHTML=!state.complaints||state.complaints.length===0
    ?'Nog geen klachten. Indrukwekkend.'
    :state.complaints.slice().reverse().map(c=>`<div class="complaint-item">`+
      `<span style="color:var(--muted);font-size:0.7rem">${c.time}</span> ${c.text}`+
      `<div class="complaint-response">${c.response}</div></div>`).join("");
  // Training
  document.getElementById("trainScore").textContent=state.training_score;
  document.getElementById("trainTips").innerHTML=state.training_tips.map(t=>
    `<div class="tip-card" onclick="markTip(${t.id})"><span style="font-size:1.2rem">${t.emoji}</span><span style="font-size:0.82rem">${t.tip}</span></div>`
  ).join("");
}
async function chgLunch(d){const n=(state.lunchers||0)+d;const r=await fetch("/lunch/lunchers?n="+n);const x=await r.json();state.lunchers=x.lunchers;document.getElementById("luncherCount").textContent=x.lunchers;msg("lunchMsg","👥 "+x.lunchers+" lunchers",2000);}
async function toggleAgenda(person,day){const r=await fetch("/lunch/agenda?person="+encodeURIComponent(person)+"&day="+day);const d=await r.json();state.agenda=d.agenda;render();msg("agendaMsg",person+" op "+day+" bijgewerkt",2000);}
async function votePoll(dish){const r=await fetch("/lunch/vote?dish="+encodeURIComponent(dish));const d=await r.json();const item=state.suggestion.poll.find(p=>p.dish===dish);if(item)item.votes=d.votes;render();toast("👍 Gestemd op "+dish+"!");}
async function scanInv(){msg("invMsg","📸 Scanning...");const r=await fetch("/lunch/scan");const d=await r.json();state.inventory=d.inventory;render();msg("invMsg",d.message,3000);toast(d.message);}
async function orderPicnic(){msg("picnicMsg","🛒 Bestellen...");const r=await fetch("/lunch/order");const d=await r.json();if(d.ok){toast(d.message,"var(--sauce)");if(d.picnic_url){const lnk=document.getElementById("picnicCartLink");lnk.href=d.picnic_url;lnk.style.display="inline-block";}await loadState();}else{toast("✅ "+d.message,"var(--green)");}msg("picnicMsg",d.message,4000);}
async function submitRequest(){const name=document.getElementById("reqName").value.trim();const who=document.getElementById("reqWho").value.trim();if(!name){toast("Geef een productnaam in!","var(--sauce)");return;}const r=await fetch("/lunch/request?name="+encodeURIComponent(name)+"&who="+encodeURIComponent(who));const d=await r.json();if(d.ok){state.product_requests.push(d.request);document.getElementById("reqName").value="";render();toast("✅ Request ingediend: "+name);}msg("reqMsg","",0);}
async function voteRequest(id){const r=await fetch("/lunch/request/vote?id="+id);const d=await r.json();if(d.ok){const req=state.product_requests.find(x=>x.id===id);if(req){req.votes=d.votes;req.status=d.status;}render();toast("👍 Gestemd! ("+d.votes+" stemmen)");}}
async function voteMood(score){const person=document.getElementById("moodName").value.trim()||"Anoniem";const r=await fetch("/lunch/mood?person="+encodeURIComponent(person)+"&score="+score);const d=await r.json();state.mood=d.mood;render();toast(d.emoji+" Sfeer geregistreerd: "+d.label);}
async function askOracle(){const q=document.getElementById("oracleQ").value.trim()||"Wat is het antwoord?";const r=await fetch("/lunch/oracle?q="+encodeURIComponent(q));const d=await r.json();const box=document.getElementById("oracleBox");box.style.display="block";document.getElementById("oracleRitual").textContent=d.ritual;document.getElementById("oracleMsg").textContent=d.message;toast("🔮 De Oracle heeft gesproken!","var(--purple)");}
async function spinSlot(){const btn=document.querySelector(".btn.gold");btn.disabled=true;btn.textContent="🎲 Draaien...";// Animate reels
const items=["🍝","🍕","🌭","🧆","🥙","🍖","🥗","🍔","🌮","🍛","🍣","🥩","🥘","🫕","🍱"];let frames=0;const anim=setInterval(()=>{["r1","r2","r3"].forEach(id=>document.getElementById(id).textContent=items[Math.floor(Math.random()*items.length)]);if(++frames>15)clearInterval(anim);},80);
setTimeout(async()=>{const r=await fetch("/lunch/spin");const d=await r.json();document.getElementById("r1").textContent=d.reels[0];document.getElementById("r2").textContent=d.reels[1];document.getElementById("r3").textContent=d.reels[2];document.getElementById("spinResult").textContent=d.message;if(d.win){document.getElementById("spinResult").style.color="var(--gold)";toast("🎰🎰🎰 JACKPOT!!!","var(--gold)");}else{document.getElementById("spinResult").style.color="var(--yellow)";}btn.disabled=false;btn.textContent="🎰 DRAAIEN!";},1400);}
async function submitComplaint(){const text=document.getElementById("complaintText").value.trim();if(!text){toast("Je klacht is leeg. Dat is ook een klacht, eigenlijk.","var(--sauce)");return;}const r=await fetch("/lunch/complaint?text="+encodeURIComponent(text));const d=await r.json();document.getElementById("complaintText").value="";state.complaints.push({text,time:new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}),response:d.response});render();toast(d.response,"#333");}
async function markTip(id){const r=await fetch("/lunch/training?tip_id="+id);const d=await r.json();document.getElementById("trainScore").textContent=d.score;toast("🎓 "+d.message);}
loadState();setInterval(loadState,30000);
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
