# -*- coding: utf-8 -*-
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
import os

SRC = r"C:\Users\musta\Downloads\WhatsApp Image 2026-07-11 at 12.37.46 AM.jpeg"
OUT = r"C:\Users\musta\tt\whale-book\assets"
os.makedirs(OUT, exist_ok=True)

src = Image.open(SRC).convert("RGB")
W, H = src.size  # 1024 x 1536

# ---------- 1. cover.jpg : clean copy of the source art, web-optimized ----------
cover = src.copy()
cover.save(os.path.join(OUT, "cover.jpg"), quality=90, optimize=True)

# ---------- 2. og-image.jpg : 1200x630 social-share card ----------
OGW, OGH = 1200, 630

# blurred, darkened backdrop filling the whole card (extend the art sideways)
bg_scale = max(OGW / W, OGH / H) * 1.15
bg = src.resize((int(W * bg_scale), int(H * bg_scale)), Image.LANCZOS)
bg = bg.crop((
    (bg.width - OGW) // 2, (bg.height - OGH) // 2,
    (bg.width - OGW) // 2 + OGW, (bg.height - OGH) // 2 + OGH,
))
bg = bg.filter(ImageFilter.GaussianBlur(22))
bg = ImageEnhance.Brightness(bg).enhance(0.55)
bg = ImageEnhance.Color(bg).enhance(0.9)

og = bg.copy()

# sharp cover art on the LEFT, scaled to card height with margin, leaving the
# right side clear for the title block (natural for an RTL reading flow --
# image first, then the text you read right-to-left)
margin = 40
target_h = OGH - margin * 2
target_w = int(target_h * (W / H))
fg = src.resize((target_w, target_h), Image.LANCZOS)

fx = 56
fy = (OGH - target_h) // 2

# soft drop shadow
shadow = Image.new("RGBA", (target_w + 60, target_h + 60), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle([30, 34, 30 + target_w, 34 + target_h], radius=14, fill=(0, 0, 0, 175))
shadow = shadow.filter(ImageFilter.GaussianBlur(24))
og = og.convert("RGBA")
og.alpha_composite(shadow, (fx - 30, fy - 26))

# rounded-corner mask for the sharp foreground image
mask = Image.new("L", (target_w, target_h), 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle([0, 0, target_w, target_h], radius=10, fill=255)
og.paste(fg, (fx, fy), mask)

og = og.convert("RGB")

# ---------- title lockup, right side of the card (RTL) ----------
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import ImageFont

FONT_BOLD = r"C:\Windows\Fonts\majallab.ttf"
FONT_REG = r"C:\Windows\Fonts\majalla.ttf"


def shaped(text):
    return get_display(arabic_reshaper.reshape(text))


draw = ImageDraw.Draw(og)

text_right = OGW - 60          # right-align edge (Arabic reads from here leftward)
text_left_bound = fx + target_w + 50  # don't run into the cover art
max_w = text_right - text_left_bound

kicker_font = ImageFont.truetype(FONT_REG, 24)
title_font = ImageFont.truetype(FONT_BOLD, 54)
author_font = ImageFont.truetype(FONT_REG, 24)

kicker = shaped("رواية")
kb = draw.textbbox((0, 0), kicker, font=kicker_font)
kicker_y = 185
draw.text((text_right - (kb[2] - kb[0]), kicker_y), kicker, font=kicker_font, fill=(148, 205, 230))

# wrap the title across as many lines as needed to fit the available width
title_raw = "ماذا لو كانت الحيتان تطير؟"
words = title_raw.split(" ")
lines, cur = [], ""
for w in words:
    trial = (cur + " " + w).strip()
    tb = draw.textbbox((0, 0), shaped(trial), font=title_font)
    if tb[2] - tb[0] <= max_w or not cur:
        cur = trial
    else:
        lines.append(cur)
        cur = w
if cur:
    lines.append(cur)

ly = kicker_y + 46
for line in lines:
    s = shaped(line)
    tb = draw.textbbox((0, 0), s, font=title_font)
    lh = tb[3] - tb[1]
    draw.text((text_right - (tb[2] - tb[0]), ly), s, font=title_font, fill=(245, 251, 255))
    ly += lh + 22

# small gold divider + author credit
divider_y = ly + 14
draw.line([(text_right, divider_y), (text_right - 90, divider_y)], fill=(198, 165, 96), width=2)
author = shaped("أسامة لافي")
ab = draw.textbbox((0, 0), author, font=author_font)
draw.text((text_right - (ab[2] - ab[0]), divider_y + 20), author, font=author_font, fill=(200, 220, 235))

og.save(os.path.join(OUT, "og-image.jpg"), quality=92, optimize=True)
print("og-image:", og.size, "lines:", lines)

# ---------- 3. favicon crop: tight SQUARE on the whale's head (most
# recognizable, high-contrast blob -- reads at 16px, unlike the full
# elongated body) ----------
sq = src.crop((150, 290, 570, 710))  # 420x420 square around the head/eye

icon_512 = sq.resize((512, 512), Image.LANCZOS)
icon_512.save(os.path.join(OUT, "icon-512.png"))
icon_192 = sq.resize((192, 192), Image.LANCZOS)
icon_192.save(os.path.join(OUT, "icon-192.png"))
apple_touch = sq.resize((180, 180), Image.LANCZOS)
apple_touch.save(os.path.join(OUT, "apple-touch-icon.png"))

favicon_sizes = [16, 32, 48, 64]
favicon_imgs = [sq.resize((s, s), Image.LANCZOS) for s in favicon_sizes]
favicon_imgs[0].save(
    os.path.join(OUT, "favicon.ico"),
    format="ICO",
    sizes=[(s, s) for s in favicon_sizes],
    append_images=favicon_imgs[1:],
)

print("done. files:", os.listdir(OUT))
