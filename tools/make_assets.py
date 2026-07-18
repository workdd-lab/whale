# -*- coding: utf-8 -*-
"""Generate cover/OG/favicon assets from the poster-style cover art.

Unlike the original blank 3D book mockup, this cover already has the title
and author baked into the artwork, so the OG card just centers it on a
blurred/darkened extended backdrop -- no text overlay needed.
"""
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
import os

SRC = r"C:\Users\musta\Desktop\asdf.jpeg"
OUT = r"C:\Users\musta\tt\whale-book\assets"
os.makedirs(OUT, exist_ok=True)

src = Image.open(SRC).convert("RGB")
W, H = src.size

# ---------- 1. cover.jpg : clean copy of the source art, web-optimized ----------
cover = src.copy()
cover.save(os.path.join(OUT, "cover.jpg"), quality=90, optimize=True)

# ---------- 2. og-image.jpg : 1200x630 social-share card ----------
OGW, OGH = 1200, 630

bg_scale = max(OGW / W, OGH / H) * 1.15
bg = src.resize((int(W * bg_scale), int(H * bg_scale)), Image.LANCZOS)
bg = bg.crop((
    (bg.width - OGW) // 2, (bg.height - OGH) // 2,
    (bg.width - OGW) // 2 + OGW, (bg.height - OGH) // 2 + OGH,
))
bg = bg.filter(ImageFilter.GaussianBlur(22))
bg = ImageEnhance.Brightness(bg).enhance(0.5)
bg = ImageEnhance.Color(bg).enhance(0.9)

og = bg.copy().convert("RGBA")

# sharp cover art centered, scaled to card height with margin (title/author
# already baked into the artwork, so no text layer is added here)
margin = 34
target_h = OGH - margin * 2
target_w = int(target_h * (W / H))
fg = src.resize((target_w, target_h), Image.LANCZOS)

fx = (OGW - target_w) // 2
fy = (OGH - target_h) // 2

shadow = Image.new("RGBA", (target_w + 60, target_h + 60), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle([30, 34, 30 + target_w, 34 + target_h], radius=14, fill=(0, 0, 0, 175))
shadow = shadow.filter(ImageFilter.GaussianBlur(24))
og.alpha_composite(shadow, (fx - 30, fy - 26))

mask = Image.new("L", (target_w, target_h), 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle([0, 0, target_w, target_h], radius=10, fill=255)
og.paste(fg, (fx, fy), mask)

og = og.convert("RGB")
og.save(os.path.join(OUT, "og-image.jpg"), quality=92, optimize=True)
print("og-image:", og.size)

# ---------- 3. favicon crop: tight SQUARE on the whale's head ----------
# whale head/eye sits in roughly the same relative position as before;
# scale the old fractional crop box to this image's own dimensions
fx0, fy0, fx1, fy1 = 150 / 1024, 290 / 1536, 570 / 1024, 710 / 1536
box = (int(fx0 * W), int(fy0 * H), int(fx1 * W), int(fy1 * H))
sq = src.crop(box)
side = min(sq.size)
sq = sq.crop((0, 0, side, side))  # keep it square

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
