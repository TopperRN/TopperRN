"""Render data/contributions.json as an animated contribution heatmap SVG.

Usage:
    python scripts/render_heatmap_svg.py [--out assets/contrib-heatmap.svg]

STATIC=1 writes the finished frame with no animation.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "contributions.json"

W = 860
BAR = 38
GRID_X = 44
GRID_Y = 84
GAP = 3
FONT = "'JetBrains Mono','SFMono-Regular',Menlo,Consolas,monospace"
# none -> brightest; level 5 is reserved for the best day
PALETTE = ["#161b22", "#0f3d36", "#17695b", "#2d9a85", "#4ec9b0", "#8ff5df"]
TEAL, TEXT, MUTED, DIM = "#4ec9b0", "#e6edf3", "#8b949e", "#484f58"

# fill-mode "both" hides cells during their delay, while renderers that skip
# CSS animation still show the finished grid instead of an empty panel
CSS = """
.c,.best{transform-box:fill-box;transform-origin:center;animation:drop .55s cubic-bezier(.2,.8,.2,1) both}
.best{animation-name:drop,pulse;animation-duration:.55s,1.6s;animation-iteration-count:1,3}
.f{animation:fade .6s ease both}
@keyframes drop{from{opacity:0;transform:translateY(-9px) scale(.5)}to{opacity:1;transform:none}}
@keyframes pulse{50%{fill:#e6fffa;transform:scale(1.25)}}
@keyframes fade{from{opacity:0}}
@media (prefers-reduced-motion:reduce){.c,.best,.f{animation:none}}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "assets" / "contrib-heatmap.svg"))
    args = ap.parse_args()
    static = os.environ.get("STATIC") == "1"

    data = json.loads(SRC.read_text(encoding="utf-8"))
    days = data["days"]
    stats = data["stats"]
    start = dt.date.fromisoformat(days[0]["date"])
    offset = (start.weekday() + 1) % 7  # GitHub weeks start on Sunday
    cols = (offset + len(days) - 1) // 7 + 1
    pitch = (W - GRID_X - 24) / cols
    cell = pitch - GAP
    max_count = max(d["count"] for d in days)

    grid_bottom = GRID_Y + 7 * pitch
    H = round(grid_bottom + 70)

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    a(f"<title>{data['user']}: {data['total']} contributions in the last year</title>")
    if not static:
        a(f"<style>{CSS}</style>")
    a(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>')

    # title bar
    a(f'<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="#21262d"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        a(f'<circle cx="{20 + i * 17}" cy="{BAR / 2}" r="5" fill="{c}" opacity=".85"/>')
    a(f'<text x="{W / 2}" y="{BAR / 2 + 4.5}" fill="{MUTED}" font-size="13" text-anchor="middle">contributions.sh — last 12 months</text>')
    updated = data["fetched_at"][:10]
    a(f'<text x="{W - 18}" y="{BAR / 2 + 4.5}" fill="{DIM}" font-size="11" text-anchor="end">updated {updated}</text>')

    # month labels where a new month starts in a column
    last_label_col = -9
    prev_month = None
    for col in range(cols):
        i = max(0, col * 7 - offset)
        month = days[i]["date"][:7]
        if month != prev_month and col - last_label_col >= 3 and col < cols - 1:
            name = dt.date.fromisoformat(days[i]["date"]).strftime("%b")
            a(f'<text x="{GRID_X + col * pitch:.1f}" y="{GRID_Y - 10}" fill="{MUTED}" font-size="11">{name}</text>')
            last_label_col = col
        prev_month = month
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        a(f'<text x="{GRID_X - 8}" y="{GRID_Y + row * pitch + cell - 2:.1f}" fill="{DIM}" font-size="10" text-anchor="end">{name}</text>')

    # the grid, revealed diagonally
    for n, d in enumerate(days):
        col, row = divmod(offset + n, 7)
        level = 5 if d["count"] == max_count and max_count > 0 else d["level"]
        x, y = GRID_X + col * pitch, GRID_Y + row * pitch
        if static:
            attrs = ""
        else:
            delay = 0.15 + (col + row * 1.6) * 0.022
            if level == 5:
                # second delay starts the pulse once the whole grid has landed
                attrs = f' class="best" style="animation-delay:{delay:.3f}s,2.4s"'
            else:
                attrs = f' class="c" style="animation-delay:{delay:.3f}s"'
        a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" fill="{PALETTE[level]}"{attrs}/>')

    # footer: stats and legend
    fade = "" if static else ' class="f" style="animation-delay:1.5s"'
    fy = grid_bottom + 34
    best = stats["best_day"]
    best_label = dt.date.fromisoformat(best["date"]).strftime("%b %-d")
    unit = lambda n: f"{n} day" + ("" if n == 1 else "s")
    a(f"<g{fade}>")
    a(f'<text x="{GRID_X}" y="{fy:.1f}" font-size="13" xml:space="preserve">'
      f'<tspan fill="{TEXT}" font-weight="700">{data["total"]:,}</tspan><tspan fill="{MUTED}"> contributions in the last year</tspan></text>')
    a(f'<text x="{GRID_X}" y="{fy + 20:.1f}" font-size="11" fill="{DIM}" xml:space="preserve">'
      f'<tspan fill="{TEAL}">streak</tspan> {unit(stats["current_streak"])}  ·  '
      f'<tspan fill="{TEAL}">longest</tspan> {unit(stats["longest_streak"])}  ·  '
      f'<tspan fill="{TEAL}">best day</tspan> {best_label} ({best["count"]})  ·  '
      f'<tspan fill="{TEAL}">active</tspan> {unit(stats["active_days"])}</text>')
    lx = W - 24 - len(PALETTE) * 15 - 34
    a(f'<text x="{lx - 8}" y="{fy:.1f}" fill="{DIM}" font-size="11" text-anchor="end">less</text>')
    for k, c in enumerate(PALETTE):
        a(f'<rect x="{lx + k * 15}" y="{fy - 10:.1f}" width="12" height="12" rx="2.5" fill="{c}"/>')
    a(f'<text x="{lx + len(PALETTE) * 15 + 5}" y="{fy:.1f}" fill="{DIM}" font-size="11">more</text>')
    a("</g></svg>")

    svg = "\n".join(out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} ({W}x{H}, {cols} weeks, {len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
