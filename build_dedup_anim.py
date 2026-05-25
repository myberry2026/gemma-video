#!/usr/bin/env python3
"""Generate the dedup explainer animation (20 -> 7 funnel)."""
import glob
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---- Config ----
W, H = 1220, 2712
FPS = 30
DURATION = 24.0  # seconds (slow pacing so viewer can read badges)
OUT_DIR = Path("/tmp/dedup_anim")
OUT_DIR.mkdir(exist_ok=True, parents=True)
APP = "com.amazon.mShop.android.shopping"
SRC_DIR = Path("/tmp/gemma_demo_curate")
OUT_MP4 = "/tmp/dedup_explainer.mp4"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ---- Load 20 frames ordered by phone timestamp ----
paths = sorted(SRC_DIR.glob(f"{APP}_*.png"))
paths = [p for p in paths if not p.name.endswith("_recap.json")][:20]
assert len(paths) == 20, f"need 20 frames, got {len(paths)}"

with open(SRC_DIR / f"{APP}_recap.json") as f:
    selected = set(json.load(f)["selected_indices"])
rejected = [i for i in range(20) if i not in selected]

# ---- Compute aHash similarity 0..1 ----
def ahash(p, sz=16):
    a = np.array(Image.open(p).convert("L").resize((sz, sz)), dtype=np.int16)
    return (a > a.mean()).flatten()

bits = [ahash(p) for p in paths]
def sim(i, j):
    return float((bits[i] == bits[j]).mean())

# For each rejected frame: find nearest selected (highest similarity)
nearest = {}
for i in rejected:
    best = max(selected, key=lambda j: sim(i, j))
    nearest[i] = (best, sim(i, best))

# ---- Layout: 5 cols × 4 rows ----
COLS, ROWS = 5, 4
GAP = 16
SIDE = 40
TITLE_H = 340
GRID_W = W - 2 * SIDE
THUMB_W = (GRID_W - (COLS - 1) * GAP) // COLS
THUMB_H = int(THUMB_W * 2712 / 1220)
GRID_TOTAL_H = ROWS * THUMB_H + (ROWS - 1) * GAP
GRID_TOP = TITLE_H
print(f"Thumb {THUMB_W}x{THUMB_H}  grid {GRID_W}x{GRID_TOTAL_H}")

# Load thumbnails once
thumbs = []
for p in paths:
    img = Image.open(p).convert("RGB").resize((THUMB_W, THUMB_H), Image.LANCZOS)
    thumbs.append(img)

def cell(i):
    c, r = i % COLS, i // COLS
    x = SIDE + c * (THUMB_W + GAP)
    y = GRID_TOP + r * (THUMB_H + GAP)
    return x, y

def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

BG = (15, 18, 30)
PURPLE = (167, 139, 250)
RED = (239, 68, 68)
GOLD = (245, 158, 11)
WHITE = (255, 255, 255)

def draw_text(draw, xy, text, color, size, bold=True, alpha=255):
    if alpha < 255:
        # Render to a temp RGBA layer then composite
        layer = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(layer)
        d2.text(xy, text, fill=color + (alpha,), font=font(size, bold))
        return layer
    draw.text(xy, text, fill=color, font=font(size, bold))
    return None

def lerp(a, b, t):
    return a + (b - a) * t

# ---- Phase boundaries (seconds) ----
P1_END = 2.5    # Title intro
P2_END = 6.5    # Progressive thumb reveal (4s, slow)
P3_END = 8.5    # Linger on full 20
P4_END = 14.0   # Red overlays + badges (5.5s, deliberate)
P5_END = 16.0   # Linger to read badges
P6_END = 18.0   # Fade out duplicates
P7_END = 24.0   # 7 highlighted + summary bullets (6s, long dwell)

def caption_bar(draw, lines, alpha=255):
    """Render a bottom caption strip with up to 2 short lines."""
    bar_y = H - 220
    draw.rectangle([0, bar_y - 30, W, H], fill=(0, 0, 0, int(180 * alpha / 255)))
    draw.line([(0, bar_y - 30), (W, bar_y - 30)], fill=PURPLE + (alpha,), width=4)
    for i, (txt, col) in enumerate(lines):
        draw.text((SIDE, bar_y + i * 70), txt, fill=col + (alpha,), font=font(46))


def render(t):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img, "RGBA")

    # ===== P1: Title intro (0 -> 2.5s) =====
    if t < P1_END:
        a = min(255, int(255 * t / 0.8))
        draw.text((SIDE, 110), "20 raw screenshots", fill=WHITE + (a,), font=font(86))
        draw.text((SIDE, 220), "captured every 15 seconds", fill=PURPLE + (a,), font=font(50))
        caption_bar(draw, [
            ("Every active app gets ~20 frames per day.", WHITE),
            ("Most of them look almost identical.", PURPLE),
        ], alpha=a)

    # ===== P2: Progressive thumb reveal (2.5 -> 6.5s) =====
    elif t < P2_END:
        draw.text((SIDE, 110), "20 raw screenshots", fill=WHITE, font=font(86))
        draw.text((SIDE, 220), "captured every 15 seconds", fill=PURPLE, font=font(50))
        prog = (t - P1_END) / (P2_END - P1_END)
        n_show = int(20 * prog) + 1
        for i in range(min(n_show, 20)):
            x, y = cell(i)
            img.paste(thumbs[i], (x, y))
            draw.rectangle([x-2, y-2, x+THUMB_W+2, y+THUMB_H+2], outline=(60,70,100), width=2)
        caption_bar(draw, [
            ("One Amazon session captured →", WHITE),
            (f"{n_show} of 20 frames shown so far", PURPLE),
        ])

    # ===== P3: Linger on full 20 (6.5 -> 8.5s) =====
    elif t < P3_END:
        draw.text((SIDE, 110), "20 raw screenshots", fill=WHITE, font=font(86))
        draw.text((SIDE, 220), "captured every 15 seconds", fill=PURPLE, font=font(50))
        for i in range(20):
            x, y = cell(i)
            img.paste(thumbs[i], (x, y))
            draw.rectangle([x-2, y-2, x+THUMB_W+2, y+THUMB_H+2], outline=(60,70,100), width=2)
        caption_bar(draw, [
            ("All 20 frames captured.", WHITE),
            ("Notice the repeated layouts — that's the problem.", PURPLE),
        ])

    # ===== P4: Red overlays + similarity badges (8.5 -> 14s) =====
    elif t < P4_END:
        # All thumbs visible
        for i in range(20):
            x, y = cell(i)
            img.paste(thumbs[i], (x, y))

        # Title crossfade
        tt = min(1, (t - P3_END) / 0.7)
        draw.text((SIDE, 110), "20 raw screenshots",
                  fill=WHITE + (int(255 * (1 - tt)),), font=font(86))
        draw.text((SIDE, 110), "Multi-level dedup",
                  fill=RED + (int(255 * tt),), font=font(86))
        draw.text((SIDE, 220), "pHash → Gemma-4 similarity",
                  fill=PURPLE + (int(255 * tt),), font=font(50))

        # Reveal red overlays one by one over 4s
        reveal_t = (t - P3_END - 0.7) / (P4_END - P3_END - 0.7)
        rejected_sorted = sorted(rejected)
        for k, idx in enumerate(rejected_sorted):
            threshold = k / max(1, len(rejected_sorted))
            if reveal_t > threshold:
                x, y = cell(idx)
                draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=RED + (90,))
                draw.rectangle([x-4, y-4, x + THUMB_W + 4, y + THUMB_H + 4],
                               outline=RED, width=6)
                nj, ns = nearest[idx]
                badge = f"{int(ns*100)}% ≈ #{nj}"
                tx_w = font(30).getlength(badge) + 16
                draw.rectangle([x + 6, y + THUMB_H - 52, x + 6 + tx_w, y + THUMB_H - 6],
                               fill=(0, 0, 0, 220))
                draw.text((x + 14, y + THUMB_H - 48), badge, fill=RED, font=font(30))

        n_flagged = min(13, int(13 * max(0, reveal_t) + 1)) if reveal_t > 0 else 0
        caption_bar(draw, [
            (f"Each frame is hashed and compared.", WHITE),
            (f"{n_flagged} flagged as duplicates of an earlier frame.", RED),
        ])

    # ===== P5: Linger to read badges (14 -> 16s) =====
    elif t < P5_END:
        for i in range(20):
            x, y = cell(i)
            img.paste(thumbs[i], (x, y))
        draw.text((SIDE, 110), "Multi-level dedup", fill=RED, font=font(86))
        draw.text((SIDE, 220), "pHash → Gemma-4 similarity", fill=PURPLE, font=font(50))
        for idx in rejected:
            x, y = cell(idx)
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=RED + (90,))
            draw.rectangle([x-4, y-4, x + THUMB_W + 4, y + THUMB_H + 4],
                           outline=RED, width=6)
            nj, ns = nearest[idx]
            badge = f"{int(ns*100)}% ≈ #{nj}"
            tx_w = font(30).getlength(badge) + 16
            draw.rectangle([x + 6, y + THUMB_H - 52, x + 6 + tx_w, y + THUMB_H - 6],
                           fill=(0, 0, 0, 220))
            draw.text((x + 14, y + THUMB_H - 48), badge, fill=RED, font=font(30))
        caption_bar(draw, [
            ("13 of 20 frames are near-duplicates.", RED),
            ("Each shows similarity vs its nearest kept frame.", PURPLE),
        ])

    # ===== P6: Fade out duplicates (16 -> 18s) =====
    elif t < P6_END:
        prog = (t - P5_END) / (P6_END - P5_END)
        draw.text((SIDE, 110), "Multi-level dedup", fill=RED, font=font(86))
        draw.text((SIDE, 220), "13 duplicates removed", fill=PURPLE, font=font(50))
        for i in range(20):
            x, y = cell(i)
            if i in selected:
                img.paste(thumbs[i], (x, y))
                draw.rectangle([x-2, y-2, x+THUMB_W+2, y+THUMB_H+2], outline=(60,70,100), width=2)
            else:
                bg = Image.new("RGB", (THUMB_W, THUMB_H), BG)
                blended = Image.blend(thumbs[i], bg, prog * 0.95)
                img.paste(blended, (x, y))
        caption_bar(draw, [
            ("Removed.", RED),
            ("Now Gemma picks the most diverse 7.", PURPLE),
        ])

    # ===== P7: 7 highlighted + summary (18 -> 24s) =====
    else:
        prog = min(1, (t - P6_END) / 1.2)
        draw.text((SIDE, 110), "7 narrative highlights", fill=GOLD, font=font(86))
        draw.text((SIDE, 220), "curated by Gemma-4-E2B", fill=PURPLE, font=font(50))

        for i in selected:
            x, y = cell(i)
            bump = 1 + 0.06 * max(0, 1 - prog / 0.4)
            if bump > 1.01:
                tw = int(THUMB_W * bump); th = int(THUMB_H * bump)
                resized = thumbs[i].resize((tw, th), Image.LANCZOS)
                ox = x - (tw - THUMB_W) // 2; oy = y - (th - THUMB_H) // 2
                img.paste(resized, (ox, oy))
            else:
                img.paste(thumbs[i], (x, y))
            border = 8
            draw.rectangle([x - border, y - border, x + THUMB_W + border, y + THUMB_H + border],
                           outline=GOLD, width=border)

        # Summary panel at the bottom (replaces caption_bar this phase)
        panel_y = H - 480
        panel_alpha = int(255 * min(1, (t - P6_END - 0.5) / 1.0)) if t > P6_END + 0.5 else 0
        draw.rectangle([0, panel_y - 30, W, H], fill=(0, 0, 0, int(210 * panel_alpha / 255)))
        draw.line([(0, panel_y - 30), (W, panel_y - 30)], fill=GOLD + (panel_alpha,), width=4)
        bullets = [
            ("✓ 13 duplicates removed (pHash + visual similarity)", WHITE),
            ("✓ 7 most diverse frames selected by Gemma-4-E2B", GOLD),
            ("✓ Curation finished in 20.4s on workstation", PURPLE),
            ("✓ Same model runs on the phone — no cloud required", PURPLE),
        ]
        for i, (txt, col) in enumerate(bullets):
            # Stagger reveal of each bullet
            reveal = max(0, min(1, (t - P6_END - 0.8 - i * 0.4) / 0.3))
            a = int(panel_alpha * reveal)
            draw.text((SIDE, panel_y + i * 90), txt, fill=col + (a,), font=font(42))

    return img

# ---- Render frames ----
total = int(DURATION * FPS)
print(f"Rendering {total} frames at {FPS} fps...")
for i in range(total):
    t = i / FPS
    im = render(t)
    im.save(OUT_DIR / f"f_{i:04d}.png", optimize=False, compress_level=1)
    if i % 30 == 0:
        print(f"  frame {i}/{total} (t={t:.1f}s)")

print("Stitching with ffmpeg...")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error",
    "-framerate", str(FPS),
    "-i", str(OUT_DIR / "f_%04d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-profile:v", "high", "-preset", "medium",
    "-r", "60",
    OUT_MP4,
], check=True)

print(f"Done: {OUT_MP4}")
