"""Neofetch-style info card that prints line by line next to the portrait.

Usage:
    python scripts/make_info_card.py [--out assets/info-card.svg]

The card matches the portrait's height, so run make_ascii_svg.py first.
STATIC=1 writes the finished frame with no animation.
"""
import argparse
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent

W = 980
BAR = 56
PAD = 44
FS = 26
CW = FS * 0.6
KEY_COLS = 10
FONT = "'JetBrains Mono','SFMono-Regular',Menlo,Consolas,monospace"
TEAL, TEXT, MUTED = "#4ec9b0", "#c9d1d9", "#6e7681"

# keep values under ~46 characters so they fit the card
ROWS = [
    ("OS", "Denmark · Danish & English"),
    ("Host", "a desk covered in jumper wires"),
    ("Kernel", "Python, learned from error messages"),
    ("Shell", "Python · Arduino/C++ · TypeScript"),
    ("Now", "T.A.B — offline voice assistant"),
    ("Prev", "GrassMapper · RF Controller · Race Predictor"),
    ("Stack", "ESP32 · FastAPI · React/Vite · SQLite"),
    ("Homelab", "Proxmox · Home Assistant · Paper MC"),
    ("Radio", "CC1101 @ 433.92 MHz · NEO-6M GPS"),
    ("Repos", "claude-cyd-dashboard · discere · ordbombe"),
    ("Hobby", "running (hence the race predictor)"),
    ("Sleep", "schedule not found"),
]
BLOCKS = ["#21262d", "#2d7a6b", "#4ec9b0", "#8ff5df", "#e3b341", "#ff7b72", "#d2a8ff", "#e6edf3"]

BASE = 0.6
STEP = 0.13


def portrait_height():
    svg = ROOT / "assets" / "topper-ascii.svg"
    if svg.exists():
        m = re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg.read_text(encoding="utf-8")[:800])
        if m:
            return float(m.group(1))
    return 900.0


def build(H, static):
    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" font-family="{FONT}">')
    a("<title>neofetch-style card: Topper, hobbyist builder from Denmark</title>")
    a(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1:.0f}" rx="10" fill="#0d1117" stroke="#30363d"/>')
    a(f'<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="#21262d"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        a(f'<circle cx="{28 + i * 24}" cy="{BAR / 2}" r="7" fill="{c}" opacity=".85"/>')
    a(f'<text x="{W / 2}" y="{BAR / 2 + 7}" fill="#8b949e" font-size="20" text-anchor="middle">topper@workshop: ~</text>')

    lines = [
        f'<tspan fill="{TEAL}">topper@workshop</tspan><tspan fill="{MUTED}"> ~ $ </tspan><tspan fill="{TEXT}">neofetch</tspan>',
        None,
        f'<tspan fill="{TEAL}" font-weight="700">topper</tspan><tspan fill="{TEXT}">@</tspan><tspan fill="{TEAL}" font-weight="700">github</tspan>',
        f'<tspan fill="{MUTED}">{"-" * 13}</tspan>',
    ]
    for key, value in ROWS:
        lines.append(f'<tspan fill="{TEAL}" font-weight="700">{escape(key)}</tspan><tspan fill="{MUTED}">:</tspan>'
                     f'<tspan x="{PAD + KEY_COLS * CW:.1f}" fill="{TEXT}">{escape(value)}</tspan>')
    lines += [None, "BLOCKS"]

    top = BAR + 58
    lh = min(50.0, (H - top - 80) / (len(lines) - 1))
    for n, line in enumerate(lines):
        if line is None:
            continue
        y = top + n * lh
        begin = BASE + n * STEP
        if static:
            a("<g>")
        else:
            a(f'<g opacity="0" transform="translate(-16 0)">'
              f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.2f}s" dur=".35s" fill="freeze"/>'
              f'<animateTransform attributeName="transform" type="translate" from="-16 0" to="0 0" begin="{begin:.2f}s" dur=".35s" fill="freeze"/>')
        if line == "BLOCKS":
            for k, c in enumerate(BLOCKS):
                a(f'<rect x="{PAD + k * 52}" y="{y - 30:.1f}" width="46" height="34" rx="3" fill="{c}"/>')
        else:
            a(f'<text x="{PAD}" y="{y:.1f}" font-size="{FS}" xml:space="preserve">{line}</text>')
        a("</g>")

    # closing prompt with a blinking cursor
    done = BASE + len(lines) * STEP
    fy = H - 26
    blink = "" if static else '<animate attributeName="opacity" values="1;0" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/>'
    fade = "" if static else f'<animate attributeName="opacity" from="0" to="1" begin="{done:.2f}s" dur=".3s" fill="freeze"/>'
    a(f'<g opacity="{1 if static else 0}">{fade}')
    a(f'<text x="{PAD}" y="{fy:.1f}" font-size="20"><tspan fill="{TEAL}">topper@workshop</tspan><tspan fill="{MUTED}"> ~ $ </tspan></text>')
    a(f'<rect x="{PAD + 20 * 12}" y="{fy - 17:.1f}" width="11" height="21" fill="{TEAL}">{blink}</rect>')
    a("</g></svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "assets" / "info-card.svg"))
    args = ap.parse_args()

    H = portrait_height()
    svg = build(H, static=os.environ.get("STATIC") == "1")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} ({W}x{H:.0f})")


if __name__ == "__main__":
    main()
