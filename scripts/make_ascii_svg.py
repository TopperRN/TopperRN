"""Turn the prepped portrait into a terminal SVG that types itself in, then glitches.

Usage:
    python scripts/make_ascii_svg.py [--src .portrait/source-prepped.png] [--out assets/topper-ascii.svg]

STATIC=1 writes the finished frame with no animation (for previews).
"""
import argparse
import os
import random
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent

RAMP = " .`:-=+*cs#%@"   # sparse -> dense
COLS = 88
SUBJECT_FLOOR = 0.28   # minimum ink inside the cut-out
W = 740
PAD_X = 26
BAR = 56           # title bar height
TOP = BAR + 14     # first row of art
LINE_H = 13.0
FOOT = 64
FONT = "'JetBrains Mono','SFMono-Regular',Menlo,Consolas,monospace"

ROW_START = 0.5    # after the power-on flicker
ROW_STAGGER = 0.045
ROW_DUR = 0.3
GLITCH_EVERY = 9   # seconds between glitch bursts


def to_rows(src):
    img = Image.open(src)
    cw = (W - 2 * PAD_X) / COLS
    rows = round(COLS * img.height / img.width * cw / LINE_H)
    if img.mode in ("LA", "RGBA"):
        # light glyphs on a dark panel: bright skin prints dense, the cut-out background prints nothing,
        # and everything inside the subject gets a floor so darker hair still shows its texture
        gray, alpha = (np.asarray(c, dtype=np.float32) / 255 for c in img.convert("LA").split())
        ink = Image.fromarray((alpha * (SUBJECT_FLOOR + (1 - SUBJECT_FLOOR) * gray ** 0.9) * 255).astype(np.uint8))
        gamma = 1.0
    else:
        # plain photo on white: dark areas print dense
        ink = ImageOps.invert(img.convert("L"))
        gamma = 0.85
    ink = ink.filter(ImageFilter.UnsharpMask(radius=4, percent=110, threshold=2))
    level = np.asarray(ink.resize((COLS, rows), Image.Resampling.BOX), dtype=np.float32) / 255
    idx = np.clip(level ** gamma * len(RAMP), 0, len(RAMP) - 1).astype(int)
    lines = ["".join(RAMP[i] for i in row) for row in idx]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines, cw


def title_bar(a, label, right):
    a(f'<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="#21262d"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        a(f'<circle cx="{28 + i * 24}" cy="{BAR / 2}" r="7" fill="{c}" opacity=".85"/>')
    a(f'<text x="{W / 2}" y="{BAR / 2 + 7}" fill="#8b949e" font-size="20" text-anchor="middle">{label}</text>')
    a(f'<text x="{W - 24}" y="{BAR / 2 + 7}" fill="#484f58" font-size="18" text-anchor="end">{right}</text>')


def build(lines, cw, static):
    n = len(lines)
    art_h = n * LINE_H
    H = round(TOP + art_h + FOOT)
    fs = cw / 0.6
    reveal_end = ROW_START + (n - 1) * ROW_STAGGER + ROW_DUR
    rng = random.Random(29)

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
      f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    a("<title>ASCII portrait of Topper</title>")
    a("<defs>")
    a(f'<linearGradient id="ink" gradientUnits="userSpaceOnUse" x1="0" y1="{TOP}" x2="0" y2="{TOP + art_h}">'
      '<stop offset="0" stop-color="#c8fff2"/><stop offset=".45" stop-color="#4ec9b0"/>'
      '<stop offset="1" stop-color="#2d7a6b"/></linearGradient>')
    a('<filter id="glow" x="-5%" y="-5%" width="110%" height="110%">'
      '<feGaussianBlur stdDeviation="2.4" result="b"/>'
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    a('<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
      '<rect width="4" height="1.6" fill="#000" opacity=".28"/></pattern>')
    a('<linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="#4ec9b0" stop-opacity="0"/>'
      '<stop offset=".5" stop-color="#4ec9b0" stop-opacity=".13"/>'
      '<stop offset="1" stop-color="#4ec9b0" stop-opacity="0"/></linearGradient>')
    a('<radialGradient id="vignette" cx=".5" cy=".5" r=".75">'
      '<stop offset=".6" stop-color="#000" stop-opacity="0"/>'
      '<stop offset="1" stop-color="#000" stop-opacity=".45"/></radialGradient>')
    a(f'<clipPath id="panel"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10"/></clipPath>')

    rows = []  # (i, x, y, text)
    for i, line in enumerate(lines):
        body = line.rstrip()
        text = body.lstrip()
        if text:
            rows.append((i, PAD_X + (len(body) - len(text)) * cw, TOP + i * LINE_H, text))

    if not static:
        for i, x, y, text in rows:
            begin = ROW_START + i * ROW_STAGGER
            a(f'<clipPath id="r{i}"><rect x="{x - 1:.1f}" y="{y:.1f}" width="0" height="{LINE_H + 1}">'
              f'<animate attributeName="width" from="0" to="{len(text) * cw + 2:.1f}" begin="{begin:.3f}s" '
              f'dur="{ROW_DUR}s" fill="freeze"/></rect></clipPath>')
        bands = []
        for k in range(6):
            bh = rng.randint(8, 30)
            by = TOP + rng.uniform(0, art_h - bh)
            bands.append((by, bh))
            a(f'<clipPath id="gb{k}"><rect x="0" y="{by:.1f}" width="{W}" height="{bh}"/></clipPath>')
    a("</defs>")

    a(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>')
    a('<g clip-path="url(#panel)">')
    if not static:
        # CRT power-on flicker
        a('<g><animate attributeName="opacity" values="0;1;.3;1;.6;1" keyTimes="0;.2;.35;.5;.7;1" dur=".5s" fill="freeze"/>')
    else:
        a("<g>")
    title_bar(a, "topper@workshop: ~/portrait", f"{COLS}×{n}")

    # the portrait itself
    a('<g fill="url(#ink)" filter="url(#glow)">')
    if not static:
        a(f'<animateTransform attributeName="transform" type="translate" values="0 0;-4 0;3 0;-1 0;0 0;0 0" '
          f'keyTimes="0;.012;.024;.036;.05;1" dur="{GLITCH_EVERY}s" begin="{reveal_end + 0.4:.2f}s" repeatCount="indefinite"/>')
    a(f'<g id="rows" font-size="{fs:.2f}" xml:space="preserve">')
    for i, x, y, text in rows:
        clip = "" if static else f' clip-path="url(#r{i})"'
        a(f'<text x="{x:.1f}" y="{y + LINE_H * 0.8:.1f}" textLength="{len(text) * cw:.1f}" '
          f'lengthAdjust="spacingAndGlyphs"{clip}>{escape(text)}</text>')
    a("</g></g>")

    if not static:
        # typing cursor that rides each row's wipe edge
        a('<g fill="#8ff5df">')
        for i, x, y, text in rows:
            begin = ROW_START + i * ROW_STAGGER
            a(f'<rect x="{x:.1f}" y="{y + 1:.1f}" width="{cw:.1f}" height="{LINE_H - 1}" opacity="0">'
              f'<set attributeName="opacity" to="1" begin="{begin:.3f}s"/>'
              f'<animate attributeName="x" from="{x:.1f}" to="{x + len(text) * cw:.1f}" begin="{begin:.3f}s" dur="{ROW_DUR}s" fill="freeze"/>'
              f'<set attributeName="opacity" to="0" begin="{begin + ROW_DUR:.3f}s"/></rect>')
        a("</g>")

        # chromatic glitch bursts: offset magenta and cyan slices of the portrait
        glitch_begin = reveal_end + 0.4
        kt = 'keyTimes="0;.012;.024;.036;.05;1"'
        for k, (by, bh) in enumerate(bands):
            for color, sign in (("#ff4fd8", 1), ("#7ff7ff", -1)):
                amp = rng.randint(8, 22) * sign
                begin = glitch_begin + rng.uniform(0, 0.08)
                a(f'<g clip-path="url(#gb{k})" opacity="0">'
                  f'<animate attributeName="opacity" values="0;.9;.15;.75;0;0" {kt} dur="{GLITCH_EVERY}s" begin="{begin:.2f}s" repeatCount="indefinite"/>'
                  f'<use href="#rows" xlink:href="#rows" fill="{color}">'
                  f'<animateTransform attributeName="transform" type="translate" values="0 0;{amp} 0;{-amp // 2} 0;{amp // 3} 0;0 0;0 0" '
                  f'{kt} dur="{GLITCH_EVERY}s" begin="{begin:.2f}s" repeatCount="indefinite"/></use></g>')

    # CRT texture on top
    a(f'<rect x="0" y="{BAR}" width="{W}" height="{H - BAR}" fill="url(#scan)"/>')
    a(f'<rect x="0" y="{BAR}" width="{W}" height="{H - BAR}" fill="url(#vignette)"/>')
    if not static:
        a(f'<rect x="0" y="-160" width="{W}" height="160" fill="url(#sweep)">'
          f'<animate attributeName="y" from="-160" to="{H}" dur="5s" begin="{reveal_end:.2f}s" repeatCount="indefinite"/></rect>')

    # prompt with a blinking cursor once the portrait has printed
    fy = H - 26
    prompt = "topper@workshop ~ $ "
    fade = "" if static else (f'<animate attributeName="opacity" from="0" to="1" begin="{reveal_end:.2f}s" dur=".3s" fill="freeze"/>')
    a(f'<g opacity="{1 if static else 0}">{fade}')
    a(f'<text x="{PAD_X}" y="{fy}" font-size="20"><tspan fill="#4ec9b0">topper@workshop</tspan>'
      f'<tspan fill="#6e7681"> ~ $ </tspan></text>')
    blink = "" if static else ('<animate attributeName="opacity" values="1;0" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/>')
    a(f'<rect x="{PAD_X + len(prompt) * 12:.1f}" y="{fy - 17}" width="11" height="21" fill="#4ec9b0">{blink}</rect>')
    a("</g>")

    a("</g></g></svg>")
    return "\n".join(out), H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / ".portrait" / "source-prepped.png"))
    ap.add_argument("--out", default=str(ROOT / "assets" / "topper-ascii.svg"))
    args = ap.parse_args()

    lines, cw = to_rows(args.src)
    svg, H = build(lines, cw, static=os.environ.get("STATIC") == "1")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(svg, encoding="utf-8")
    print(f"wrote {args.out} ({COLS}x{len(lines)} chars, {W}x{H}, {len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
