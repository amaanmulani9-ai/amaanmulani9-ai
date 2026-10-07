#!/usr/bin/env python3
"""
Comprehensive profile asset builder for Amaan Mulani (amaanmulani9-ai).
Generates:
  1. data/contributions.json
  2. contrib-heatmap.svg
  3. source-prepped.png
  4. amaan-ascii.svg
  5. stats.svg
"""
import datetime
import html
import json
import os
import sys
import urllib.request
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

USERNAME = "amaanmulani9-ai"

# ==========================================
# 1. FETCH CONTRIBUTIONS
# ==========================================
print("=== 1. Fetching Contribution Data ===")
api_url = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"
days = []
try:
    req = urllib.request.Request(api_url, headers={"User-Agent": "profile-bot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        payload = json.loads(r.read().decode())
        days = payload.get("contributions", [])
except Exception as e:
    print(f"API Warning: {e}, attempting scraping fallback...")

if not days:
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(f"https://github.com/users/{USERNAME}/contributions", headers={"User-Agent": "profile-bot/1.0"}, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cells = soup.select("td.ContributionCalendar-day")
            for td in cells:
                date = td.get("data-date")
                if not date: continue
                td_id = td.get("id")
                tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
                text = tooltip_el.get_text(strip=True) if tooltip_el else ""
                count = int(m.group(1)) if (m := re.match(r"(\d+)", text)) else 0
                days.append({"date": date, "count": count, "level": int(td.get("data-level") or 0)})
    except Exception as e:
        print("Scraping fallback failed:", e)

for d in days:
    if "level" not in d:
        c = d.get("count", 0)
        if c == 0: d["level"] = 0
        elif c < 3: d["level"] = 1
        elif c < 6: d["level"] = 2
        elif c < 10: d["level"] = 3
        else: d["level"] = 4
days.sort(key=lambda x: x["date"])

total = sum(d["count"] for d in days)
active_days = sum(1 for d in days if d["count"] > 0)
best = max(days, key=lambda d: d["count"]) if days else {"date": "N/A", "count": 0}

idx = len(days) - 1
if days and days[idx]["count"] == 0:
    idx -= 1
cur_streak = 0
end_idx = idx
while idx >= 0 and days[idx]["count"] > 0:
    cur_streak += 1
    idx -= 1
start_idx = idx + 1
cur_start = days[start_idx]["date"] if cur_streak else None
cur_end = days[end_idx]["date"] if cur_streak else None

longest = run = 0
long_start = long_end = None
run_start_idx = None
for i, d in enumerate(days):
    if d["count"] > 0:
        if run == 0: run_start_idx = i
        run += 1
        if run > longest:
            longest = run
            long_start = days[run_start_idx]["date"]
            long_end = days[i]["date"]
    else:
        run = 0

monthly = {}
for d in days:
    key = d["date"][:7]
    monthly[key] = monthly.get(key, 0) + d["count"]
monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

data = {
    "username": USERNAME,
    "name": "Amaan Mulani",
    "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "range": {"start": days[0]["date"] if days else "", "end": days[-1]["date"] if days else ""},
    "total_contributions": total,
    "active_days": active_days,
    "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
    "current_streak": {"length": cur_streak, "start": cur_start, "end": cur_end},
    "longest_streak": {"length": longest, "start": long_start, "end": long_end},
    "best_day": {"date": best["date"], "count": best["count"]},
    "monthly": monthly_list,
    "days": days
}

os.makedirs("data", exist_ok=True)
with open("data/contributions.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"Saved data/contributions.json: {total} total contributions, active {active_days} days")

# ==========================================
# 2. GENERATE CONTRIB HEATMAP SVG
# ==========================================
print("=== 2. Generating contrib-heatmap.svg ===")
CELL, GAP, RAD, LEFT, TOP = 13, 3, 2.5, 34, 24
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
GRAY = "#7d8590"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

n = len(days)
NW = (n + 6) // 7
W = LEFT + NW*(CELL+GAP) + 6
H = TOP + 7*(CELL+GAP) + 24
REVEAL, DUR = 3.6, 0.55
maxorder = (NW-1) + 6*0.55

rects, labels = [], []
sd = datetime.date.fromisoformat(days[0]["date"]) if days else datetime.date.today()
last_m = None
for wk in range(NW):
    d = sd + datetime.timedelta(days=wk*7)
    if d.month != last_m:
        last_m = d.month
        labels.append(f'<text class="lbl" x="{LEFT+wk*(CELL+GAP)}" y="{TOP-8}">{MONTHS[d.month-1]}</text>')
for name, r in [("Mon",1),("Wed",3),("Fri",5)]:
    labels.append(f'<text class="lbl" x="2" y="{TOP+r*(CELL+GAP)+CELL-2}">{name}</text>')

for i, c in enumerate(days):
    wk, row, lvl = i//7, i%7, min(4, max(0, c.get("level", 0)))
    x = LEFT + wk*(CELL+GAP); y = TOP + row*(CELL+GAP)
    delay = round((wk + row*0.55)/maxorder * REVEAL, 3)
    cls = "c g" if lvl >= 1 else "c e"
    rects.append(
        f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RAD}" '
        f'fill="{COLORS[lvl]}" style="animation-delay:{delay}s"/>'
    )

heatmap_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill:{GRAY}; font-size:13px; font-weight:600; }}
  text.total {{ fill:#e6edf3; font-size:15px; font-weight:700; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop {DUR}s ease-out both; }}
  .g {{ animation:pop {DUR}s ease-out both, flash {DUR+0.15}s ease-out both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} 60%{{opacity:1;transform:scale(1.1)}} 100%{{opacity:1;transform:scale(1)}} }}
  @keyframes flash {{ 0%{{filter:brightness(2.4)}} 45%{{filter:brightness(2.4)}} 100%{{filter:brightness(1)}} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ opacity:1 !important; animation:none !important; }} }}
</style>
<rect width="{W}" height="{H}" fill="none"/>
{''.join(labels)}
{''.join(rects)}
<text class="total" x="{LEFT}" y="{H-6}">{total:,} contributions in the last year</text>
</svg>'''

with open("contrib-heatmap.svg", "w", encoding="utf-8") as f:
    f.write(heatmap_svg)
print("Wrote contrib-heatmap.svg")

# ==========================================
# 3. PREPARE PHOTO
# ==========================================
print("=== 3. Preparing source-prepped.png ===")
img = cv2.imread("source-photo.png")
h, w = img.shape[:2]
mask = np.zeros(img.shape[:2], np.uint8)
bgdModel = np.zeros((1, 65), np.float64)
fgdModel = np.zeros((1, 65), np.float64)
rect = (2, 2, w - 4, h - 4)
cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 6, cv2.GC_INIT_WITH_RECT)
mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
composite = np.where(mask2[:, :, np.newaxis] == 1, img, np.full_like(img, 255))
gray = cv2.cvtColor(composite, cv2.COLOR_BGR2GRAY)

smooth = gray
for _ in range(2):
    smooth = cv2.bilateralFilter(smooth, 7, 30, 7)

clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
contrast = clahe.apply(smooth)

fine = cv2.GaussianBlur(smooth, (0, 0), 1.0).astype(np.float32)
coarse = cv2.GaussianBlur(smooth, (0, 0), 4.0).astype(np.float32)
lines = np.clip((coarse - fine) / 30.0, 0, 1)

tone = contrast.astype(np.float32) / 255.0
out = np.clip(tone - 0.45 * lines, 0, 1) * 255.0
out_final = np.where(mask2 == 1, out, 255.0).astype(np.uint8)
Image.fromarray(out_final, mode="L").save("source-prepped.png")
print("Wrote source-prepped.png")

# ==========================================
# 4. GENERATE ASCII SVG
# ==========================================
print("=== 4. Generating amaan-ascii.svg ===")
COLS = 180
ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)
RAMP = " .`:-=+*cs#%@"

im = Image.open("source-prepped.png").convert("L")
im = ImageEnhance.Brightness(im).enhance(1.02)
im = ImageEnhance.Contrast(im).enhance(1.10)
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

rows_txt = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        lum = pow(px[x, y] / 255.0, 1.15)
        if lum >= 0.82:
            chars.append(" ")
        else:
            idx = max(0, min(len(RAMP) - 1, int((1.0 - lum) * (len(RAMP) - 1) + 0.5)))
            chars.append(RAMP[idx])
    rows_txt.append("".join(chars))

PAD, TITLEBAR_H, STATUS_H = 20, 30, 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD
BG, BG2, FRAME, TITLE_TEXT, INK, CURSOR = "#0d1117", "#111722", "#30363d", "#7d8590", "#c9d1d9", "#38bdf8"
ROW_DUR = 5.8 / ROWS
STAGGER = ROW_DUR
art_top = TITLEBAR_H + PAD * 0.35

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
    f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" fill="none" stroke="{FRAME}" stroke-width="1"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>'
]
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" text-anchor="middle">amaan@github: ~$ ./portrait.sh</text>')

font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    safe = html.escape(line)
    text = f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{safe}</text>'
    parts.append(f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0"><animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>')
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    parts.append(f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0"><animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/><set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/><set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>')

status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">amaan@github:~$ whoami <tspan fill="{INK}">Amaan Mulani</tspan></text>')
status_chars = len("amaan@github:~$ whoami Amaan Mulani ")
parts.append(f'<rect x="{PAD + status_chars * 13 * 0.6:.1f}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>')
parts.append("</svg>")

with open("amaan-ascii.svg", "w", encoding="utf-8") as f:
    f.write("".join(parts))
print("Wrote amaan-ascii.svg")

# ==========================================
# 5. GENERATE STATS SVG
# ==========================================
print("=== 5. Generating stats.svg ===")
W, H = 840, 880
PAD, TITLEBAR_H, COLS, ROWS, GAP = 20, 30, 2, 3, 16
TILE_W = (W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H = 150
TILES_TOP = TITLEBAR_H + PAD + 4
CHART_TOP = TILES_TOP + ROWS * TILE_H + (ROWS - 1) * GAP + GAP

TILE_STAGGER = 0.15
SLIDE_DUR = 0.45
COUNT_DUR = 1.2
FRAMES = 16
BAR_START = TILE_STAGGER * COLS * ROWS + 0.4
BAR_STAGGER = 0.06
BAR_DUR = 0.6

def short(d):
    return datetime.date.fromisoformat(d).strftime("%b %d") if d else "—"
def span(s):
    return f"{short(s['start'])} – {short(s['end'])}" if s.get("length") else "—"
def fmt(v, like):
    return f"{v:,.1f}" if isinstance(like, float) else f"{int(round(v)):,}"

GREEN = "#39d353"
BAR = "#26a641"
MUTED = "#7d8590"
INK = "#e6edf3"
BG = "#0d1117"
BG2 = "#111722"
TILE = "#161b22"
FRAME = "#30363d"
tiles = [
    ("current streak", cur_streak, " days", span(data["current_streak"]), GREEN),
    ("longest streak", longest, " days", span(data["longest_streak"]), INK),
    ("contributions", total, "", "in the last year", INK),
    ("active days", active_days, f" / {len(days)}", f"{active_days / max(1, len(days)):.0%} of the year", INK),
    ("best day", best["count"], "", short(best["date"]), INK),
    ("avg / active day", data["avg_per_active_day"], "", "contributions", INK),
]

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<style>',
    f'.t{{opacity:0;animation:in {SLIDE_DUR}s ease-out both}}',
    '@keyframes in{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}',
    f'.b{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow {BAR_DUR}s ease-out both}}',
    '@keyframes grow{to{transform:scaleY(1)}}',
    '@media (prefers-reduced-motion: reduce){.t,.b{opacity:1!important;transform:none!important;animation:none!important}}',
    '</style>',
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>'
]
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
parts.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" text-anchor="middle">amaan@github: ~$ ./stats.sh</text>')

for i, (label, value, suffix, caption, accent) in enumerate(tiles):
    col, row = i % COLS, i // COLS
    x = PAD + col * (TILE_W + GAP)
    y = TILES_TOP + row * (TILE_H + GAP)
    start = i * TILE_STAGGER
    count_start = start + SLIDE_DUR * 0.6
    parts.append(f'<g class="t" style="animation-delay:{start:.2f}s">')
    parts.append(f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="10" fill="{TILE}" stroke="{FRAME}"/>')
    parts.append(f'<text x="{x+24:.1f}" y="{y+40}" fill="{MUTED}" font-size="22">$ {label}</text>')
    num_y = y + 100
    for k in range(1, FRAMES + 1):
        p = k / FRAMES
        v = value * (1 - (1 - p) ** 3)
        t_on = count_start + COUNT_DUR * (k - 1) / FRAMES
        t_off = count_start + COUNT_DUR * k / FRAMES
        anim = f'<set attributeName="opacity" to="1" begin="{t_on:.3f}s"/>'
        if k < FRAMES: anim += f'<set attributeName="opacity" to="0" begin="{t_off:.3f}s"/>'
        parts.append(f'<text x="{x+24:.1f}" y="{num_y}" opacity="0" font-size="54" font-weight="700" fill="{accent}">{fmt(v, value)}<tspan font-size="24" font-weight="400" fill="{MUTED}">{suffix}</tspan>{anim}</text>')
    parts.append(f'<text x="{x+24:.1f}" y="{y+132}" fill="{MUTED}" font-size="20">{caption}</text>')
    parts.append('</g>')

chart_x, chart_w = PAD, W - PAD * 2
chart_h = H - PAD - CHART_TOP
parts.append(f'<g class="t" style="animation-delay:{BAR_START - 0.3:.2f}s">')
parts.append(f'<rect x="{chart_x}" y="{CHART_TOP}" width="{chart_w}" height="{chart_h}" rx="10" fill="{TILE}" stroke="{FRAME}"/>')
parts.append(f'<text x="{chart_x+24}" y="{CHART_TOP+40}" fill="{MUTED}" font-size="22">$ contributions / month</text>')
parts.append('</g>')

plot_top = CHART_TOP + 64
plot_bot = CHART_TOP + chart_h - 40
plot_l, plot_r = chart_x + 24, chart_x + chart_w - 24
slot = (plot_r - plot_l) / len(monthly_list)
bar_w = slot * 0.62
peak = max(m["total"] for m in monthly_list) if monthly_list else 1
for i, m in enumerate(monthly_list):
    h = max(2, (plot_bot - plot_top) * m["total"] / peak)
    bx = plot_l + i * slot + (slot - bar_w) / 2
    fill = GREEN if m["total"] == peak else BAR
    delay = BAR_START + i * BAR_STAGGER
    parts.append(f'<rect class="b" x="{bx:.1f}" y="{plot_bot - h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{fill}" style="animation-delay:{delay:.2f}s"/>')
    mon = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")[0]
    parts.append(f'<text x="{bx + bar_w/2:.1f}" y="{plot_bot + 28}" fill="{MUTED}" font-size="18" text-anchor="middle">{mon}</text>')
    if m["total"] == peak and peak > 0:
        parts.append(f'<text class="t" style="animation-delay:{delay + BAR_DUR:.2f}s" x="{bx + bar_w/2:.1f}" y="{plot_bot - h - 10:.1f}" fill="{INK}" font-size="18" text-anchor="middle">{peak:,}</text>')

parts.append('</svg>')
with open("stats.svg", "w", encoding="utf-8") as f:
    f.write("".join(parts))
print("Wrote stats.svg")
print("=== ALL ASSETS FINISHED SUCCESSFULLY ===")
