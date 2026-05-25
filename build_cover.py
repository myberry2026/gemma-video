#!/usr/bin/env python3
"""Build a 1920x1080 Devpost cover image for AetherLens.
Output: /tmp/cover.png
"""
import glob
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = (15, 18, 30)
PURPLE = (167, 139, 250)
GOLD = (245, 158, 11)
WHITE = (255, 255, 255)
RED = (239, 68, 68)
CYAN = (6, 182, 212)
GRID_LINE = (60, 70, 100)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else
                              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                              size)

SRC = Path("/tmp/gemma_demo_curate")
APP = "com.amazon.mShop.android.shopping"
RECAP = json.load(open(SRC / f"{APP}_recap.json"))
SELECTED = RECAP["selected_indices"]
SUMMARY = RECAP["summary"]

# Load 20 Amazon frames (sorted)
paths = sorted(glob.glob(str(SRC / f"{APP}_*.png")))[:20]

# ===== Background gradient =====
img = Image.new("RGB", (W, H), BG)
# soft radial-ish vignette: lighten center slightly
gd = ImageDraw.Draw(img)
for r in range(800, 0, -40):
    a = int(8 * (1 - r / 800))
    if a > 0:
        gd.ellipse([(W // 2 - r, H // 2 - r), (W // 2 + r, H // 2 + r)],
                   fill=(25, 28, 50))

draw = ImageDraw.Draw(img, "RGBA")

# ===== Top: title + tagline =====
draw.text((W // 2, 60), "AetherLens", fill=GOLD, font=font(96), anchor="mm")
draw.text((W // 2, 130), "A daily recap of your digital life — distilled by Gemma-4-E2B, fully on your phone.",
          fill=WHITE, font=font(34), anchor="mm")

# ===== Middle: 3-column flow =====
# left column: raw 20 frame grid (4 cols x 5 rows)
LEFT_X = 80
LEFT_W = 560
LEFT_Y = 200
THUMB_W_L = 80
THUMB_H_L = int(THUMB_W_L * 2712 / 1220)
gap = 8
cols_l = 4
rows_l = 3
gw = cols_l * THUMB_W_L + (cols_l - 1) * gap
gh = rows_l * THUMB_H_L + (rows_l - 1) * gap
gx = LEFT_X + (LEFT_W - gw) // 2
gy = LEFT_Y + 50
visible = cols_l * rows_l   # only render what fits
for i, p in enumerate(paths[:visible]):
    c, r = i % cols_l, i // cols_l
    x = gx + c * (THUMB_W_L + gap)
    y = gy + r * (THUMB_H_L + gap)
    t = Image.open(p).convert("RGB").resize((THUMB_W_L, THUMB_H_L), Image.LANCZOS)
    m = Image.new("L", (THUMB_W_L, THUMB_H_L), 0)
    ImageDraw.Draw(m).rounded_rectangle([(0, 0), (THUMB_W_L, THUMB_H_L)], radius=10, fill=255)
    img.paste(t, (x, y), m)

# left column header
draw.text((LEFT_X + LEFT_W // 2, LEFT_Y + 18),
          "20 raw screenshots", fill=WHITE, font=font(28), anchor="mm")
draw.text((LEFT_X + LEFT_W // 2, gy + gh + 30),
          "captured all day, every 15 s", fill=PURPLE, font=font(22), anchor="mm")

# ===== Middle column: dedup pipeline (text + icons) =====
MID_X = LEFT_X + LEFT_W + 40
MID_W = 360
MID_CX = MID_X + MID_W // 2
MID_Y = LEFT_Y + 50
# vertical 3-step indicator
stages = [
    (CYAN,   "Pass 1",  "pHash"),
    (PURPLE, "Pass 2",  "Gemma visual sim"),
    (GOLD,   "Pass 3",  "Gemma 20 → 7"),
]
step_h = 180
for i, (color, label, sub) in enumerate(stages):
    y = MID_Y + 40 + i * step_h
    # rounded box
    draw.rounded_rectangle([(MID_CX - 150, y), (MID_CX + 150, y + 110)],
                           radius=20, fill=color)
    draw.text((MID_CX, y + 36),  label, fill=WHITE, font=font(34), anchor="mm")
    draw.text((MID_CX, y + 76),  sub,   fill=(25,28,50), font=font(22), anchor="mm")
    if i < len(stages) - 1:
        # arrow down
        ay = y + 130
        draw.line([(MID_CX, ay), (MID_CX, ay + 50)], fill=WHITE, width=4)
        draw.polygon([(MID_CX, ay + 60),
                      (MID_CX - 12, ay + 44),
                      (MID_CX + 12, ay + 44)], fill=WHITE)

draw.text((MID_CX, MID_Y + 18),
          "3 passes of dedup", fill=WHITE, font=font(28), anchor="mm")

# ===== Right column: 7 curated highlights =====
RIGHT_X = MID_X + MID_W + 40
RIGHT_W = W - RIGHT_X - 80
RIGHT_Y = LEFT_Y
# header
draw.text((RIGHT_X + RIGHT_W // 2, RIGHT_Y + 18),
          "7 narrative highlights", fill=GOLD, font=font(28), anchor="mm")
# 7 thumbs in 4x2 (with last cell empty), tighter
sel_paths = [paths[i] for i in SELECTED if i < len(paths)]
THUMB_W_R = 130
THUMB_H_R = int(THUMB_W_R * 2712 / 1220)
cols_r = 4
sel_gap = 12
sgw = cols_r * THUMB_W_R + (cols_r - 1) * sel_gap
sgx = RIGHT_X + (RIGHT_W - sgw) // 2
sgy = RIGHT_Y + 50
for i, p in enumerate(sel_paths[:7]):
    c, r = i % cols_r, i // cols_r
    x = sgx + c * (THUMB_W_R + sel_gap)
    y = sgy + r * (THUMB_H_R + sel_gap)
    t = Image.open(p).convert("RGB").resize((THUMB_W_R, THUMB_H_R), Image.LANCZOS)
    m = Image.new("L", (THUMB_W_R, THUMB_H_R), 0)
    ImageDraw.Draw(m).rounded_rectangle([(0, 0), (THUMB_W_R, THUMB_H_R)], radius=12, fill=255)
    img.paste(t, (x, y), m)
    # gold border
    bw = 5
    draw.rounded_rectangle([(x - bw, y - bw), (x + THUMB_W_R + bw, y + THUMB_H_R + bw)],
                           radius=14, outline=GOLD, width=bw)
    # rank badge
    badge = f"{i + 1}/7"
    bw_t = font(20).getlength(badge) + 12
    draw.rounded_rectangle([(x + 6, y + 6), (x + 6 + bw_t, y + 6 + 30)],
                           radius=10, fill=GOLD)
    draw.text((x + 6 + bw_t / 2, y + 6 + 15), badge,
              fill=(15, 18, 30), font=font(20), anchor="mm")

# summary excerpt under the grid
sum_y = sgy + 2 * THUMB_H_R + sel_gap + 20
summary_short = '"' + SUMMARY.split('.')[0].strip() + '."'
# wrap if needed: very rough split
def wrap(text, max_chars=58):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars:
            lines.append(cur.strip()); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur: lines.append(cur)
    return lines
for i, line in enumerate(wrap(summary_short, 56)):
    draw.text((RIGHT_X + RIGHT_W // 2, sum_y + i * 30),
              line, fill=PURPLE, font=font(20), anchor="mm")

# ===== Bottom: tag bar (compact, centered) =====
bar_y = H - 110
draw.line([(80, bar_y - 16), (W - 80, bar_y - 16)], fill=GRID_LINE, width=2)
chips = [
    ("Gemma-4-E2B · 2.4 GB", GOLD),
    ("on your phone", PURPLE),
    ("no cloud · no laptop", CYAN),
]
chip_font = font(22)
total = 0
chip_widths = []
for label, _ in chips:
    w = int(chip_font.getlength(label)) + 30
    chip_widths.append(w)
    total += w
gap_x = 28
total += gap_x * (len(chips) - 1)
cx = (W - total) // 2
y_bar = bar_y + 24
for (label, color), w in zip(chips, chip_widths):
    draw.rounded_rectangle([(cx, y_bar - 22), (cx + w, y_bar + 22)],
                           radius=18, outline=color, width=3)
    draw.text((cx + w // 2, y_bar), label, fill=color, font=chip_font, anchor="mm")
    cx += w + gap_x

# Footer URL (single line, centered, fits)
draw.text((W // 2, H - 28),
          "github.com/myberry2026/gemma-video    ·    youtube.com/shorts/W_pw4Lqcz14",
          fill=WHITE, font=font(20), anchor="mm")

img.save("/tmp/cover.png", "PNG", optimize=True)
print("Wrote /tmp/cover.png")
