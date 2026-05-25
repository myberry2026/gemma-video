#!/usr/bin/env python3
"""Build opening + closing slide PNGs for the demo video.
Outputs:
  /tmp/slide_opening.png  (1220x2712)
  /tmp/slide_closing.png  (1220x2712)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1220, 2712
BG = (15, 18, 30)
PURPLE = (167, 139, 250)
GOLD = (245, 158, 11)
WHITE = (255, 255, 255)
RED = (239, 68, 68)
TEAL = (45, 212, 191)
CYAN = (6, 182, 212)
GRID_LINE = (60, 70, 100)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)

SRC = Path("/tmp/gemma_demo_curate")

# Order matters: visually-distinctive apps first
APPS = [
    ("com.amazon.mShop.android.shopping", "Amazon"),
    ("com.zhiliaoapp.musically",           "TikTok"),
    ("com.google.android.youtube",         "YouTube"),
    ("com.android.chrome",                 "Chrome"),
    ("com.google.android.calendar",        "Calendar"),
    ("com.google.android.apps.maps",       "Maps"),
    ("com.google.android.apps.messaging",  "Messages"),
    ("com.google.android.apps.photos",     "Photos"),
    ("com.android.settings",               "Settings"),
]

def load_first_thumb(pkg, size):
    paths = sorted(SRC.glob(f"{pkg}_*.png"))
    if not paths:
        return None
    img = Image.open(paths[0]).convert("RGB")
    img = img.resize((size, int(size * 2712 / 1220)), Image.LANCZOS)
    # Add rounded-rect mask
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), img.size], radius=24, fill=255)
    out = Image.new("RGBA", img.size, (0,0,0,0))
    out.paste(img, (0, 0), mask)
    return out

def draw_stage_icon(draw, cx, cy, kind, color, size=120):
    """Flat-style icon: filled rounded square + glyph drawn inside."""
    r = size // 2
    box = [(cx - r, cy - r), (cx + r, cy + r)]
    draw.rounded_rectangle(box, radius=30, fill=color)
    # Glyph
    f = font(int(size * 0.62))
    if kind == "capture":
        # camera-ish: hollow square + small dot
        d = size // 3
        draw.rectangle([cx - d, cy - d, cx + d, cy + d],
                       outline=WHITE, width=10)
        draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=WHITE)
    elif kind == "dedup":
        # funnel: trapezoid + line
        pts = [(cx - r + 22, cy - r + 30), (cx + r - 22, cy - r + 30),
               (cx + 24, cy), (cx + 24, cy + r - 30),
               (cx - 24, cy + r - 30), (cx - 24, cy)]
        draw.polygon(pts, outline=WHITE, width=10)
    elif kind == "recap":
        # book / diary: spine + lines
        draw.rectangle([cx - r + 28, cy - r + 26, cx + r - 28, cy + r - 26],
                       outline=WHITE, width=10)
        # interior lines
        for i in range(3):
            y = cy - 28 + i * 28
            draw.line([(cx - r + 50, y), (cx + r - 50, y)], fill=WHITE, width=6)
    elif kind == "phone":
        # outlined phone with screen
        draw.rounded_rectangle([cx - r + 26, cy - r + 18, cx + r - 26, cy + r - 18],
                               radius=22, outline=WHITE, width=10)
        # screen inset
        draw.rounded_rectangle([cx - r + 42, cy - r + 50, cx + r - 42, cy + r - 80],
                               radius=12, outline=WHITE, width=6)
        # home dot
        draw.ellipse([cx - 12, cy + r - 64, cx + 12, cy + r - 40],
                     fill=WHITE)

# =============================================================================
# OPENING SLIDE
# =============================================================================
def build_opening():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img, "RGBA")

    # === Title block (compact) ===
    draw.text((W // 2, 130), "AetherLens",
              fill=GOLD, font=font(120), anchor="mm")
    draw.text((W // 2, 230), "A daily recap of your digital life",
              fill=WHITE, font=font(50), anchor="mm")
    draw.text((W // 2, 296), "powered by Gemma-4-E2B  ·  on your phone",
              fill=PURPLE, font=font(40), anchor="mm")

    # === 3-step flow (MOVED UP, big, prominent) ===
    flow_top = 400
    icon_y = flow_top + 130
    stages = [
        ("capture", "Capture",  "every 15s",            CYAN),
        ("dedup",   "Dedup",    "pHash + Gemma-4",      PURPLE),
        ("recap",   "Recap",    "Gemma picks the best", GOLD),
    ]
    n = len(stages)
    for i, (kind, title, sub, color) in enumerate(stages):
        cx = int(W * (i + 0.5) / n)
        draw_stage_icon(draw, cx, icon_y, kind, color, size=160)
        draw.text((cx, icon_y + 130), title, fill=WHITE,  font=font(46), anchor="mm")
        draw.text((cx, icon_y + 184), sub,   fill=PURPLE, font=font(30), anchor="mm")
        if i < n - 1:
            ax_start = cx + 95
            ax_end = int(W * (i + 1.5) / n) - 95
            ay = icon_y
            draw.line([(ax_start, ay), (ax_end, ay)], fill=WHITE, width=6)
            draw.polygon([(ax_end, ay), (ax_end - 22, ay - 14),
                          (ax_end - 22, ay + 14)], fill=WHITE)
    flow_bottom = icon_y + 240  # ~770

    # === Divider + small "Captured from these apps:" label ===
    draw.line([(80, flow_bottom + 30), (W - 80, flow_bottom + 30)],
              fill=GRID_LINE, width=2)
    draw.text((W // 2, flow_bottom + 92),
              "captured from these apps",
              fill=PURPLE, font=font(34), anchor="mm")

    # === App-thumbnail proof grid (3x3, smaller, less prominent) ===
    grid_top = flow_bottom + 140
    thumb_w = 220
    thumb_h = int(thumb_w * 2712 / 1220)  # ~489
    gap_x = 26
    gap_y = 56
    cols = 3
    total_w = cols * thumb_w + (cols - 1) * gap_x
    left = (W - total_w) // 2
    for i, (pkg, label) in enumerate(APPS):
        col = i % cols
        row = i // cols
        x = left + col * (thumb_w + gap_x)
        y = grid_top + row * (thumb_h + gap_y)
        thumb = load_first_thumb(pkg, thumb_w)
        if thumb is not None:
            img.paste(thumb, (x, y), thumb)
        cap_w = font(22).getlength(label) + 22
        cx = x + thumb_w // 2
        cy = y + thumb_h + 22
        draw.rounded_rectangle(
            [(cx - cap_w / 2, cy - 16), (cx + cap_w / 2, cy + 16)],
            radius=14, fill=(35, 40, 60))
        draw.text((cx, cy), label, fill=WHITE, font=font(22), anchor="mm")

    # === Footer tagline ===
    draw.text((W // 2, H - 60),
              "no cloud  ·  no laptop  ·  just the phone in your pocket",
              fill=PURPLE, font=font(30), anchor="mm")

    img.save("/tmp/slide_opening.png", "PNG")
    print("Wrote /tmp/slide_opening.png")

# =============================================================================
# CLOSING SLIDE
# =============================================================================
def build_closing():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img, "RGBA")

    # === Big phone illustration ===
    px, py = W // 2, H // 2 - 200
    phone_w, phone_h = 600, 1200
    # phone body
    draw.rounded_rectangle(
        [(px - phone_w // 2, py - phone_h // 2),
         (px + phone_w // 2, py + phone_h // 2)],
        radius=80, outline=PURPLE, width=10)
    # screen
    sx1, sy1 = px - phone_w // 2 + 40, py - phone_h // 2 + 90
    sx2, sy2 = px + phone_w // 2 - 40, py + phone_h // 2 - 130
    draw.rounded_rectangle([(sx1, sy1), (sx2, sy2)], radius=40, fill=(25, 28, 50))
    # Gemma card inside
    card_w, card_h = phone_w - 180, 360
    cx1 = px - card_w // 2
    cy1 = py - card_h // 2
    cx2 = px + card_w // 2
    cy2 = py + card_h // 2
    draw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=28, fill=BG, outline=GOLD, width=6)
    draw.text((px, cy1 + 70), "Gemma-4-E2B",  fill=GOLD,   font=font(56), anchor="mm")
    draw.text((px, cy1 + 150), "2.4 GB",       fill=WHITE,  font=font(72), anchor="mm")
    draw.text((px, cy1 + 230), "running here", fill=PURPLE, font=font(34), anchor="mm")
    draw.text((px, cy1 + 300), "▼",            fill=GOLD,   font=font(44), anchor="mm")
    # home dot
    draw.ellipse([(px - 16, py + phone_h // 2 - 80),
                  (px + 16, py + phone_h // 2 - 48)], fill=PURPLE)

    # === Headline above phone ===
    draw.text((W // 2, 220), "Every screenshot.", fill=WHITE, font=font(76), anchor="mm")
    draw.text((W // 2, 310), "Every inference.", fill=WHITE, font=font(76), anchor="mm")
    draw.text((W // 2, 410), "On the phone in your pocket.", fill=GOLD, font=font(58), anchor="mm")

    # === Footer ===
    draw.text((W // 2, H - 180), "AetherLens",            fill=GOLD,  font=font(72), anchor="mm")
    draw.text((W // 2, H - 100), "Powered by Gemma 4",    fill=PURPLE,font=font(40), anchor="mm")

    img.save("/tmp/slide_closing.png", "PNG")
    print("Wrote /tmp/slide_closing.png")


if __name__ == "__main__":
    build_opening()
    build_closing()
