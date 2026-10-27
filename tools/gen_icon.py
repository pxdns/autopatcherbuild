"""Draws the Autopatcher icon (an original mark: a stitched code patch on a rounded tile) with Pillow.

Writes assets/icon.png (512), assets/icon-192.png, assets/favicon-32.png and site/favicon.png.
Run: python3 -I tools/gen_icon.py
"""
from PIL import Image, ImageDraw
import os

S = 1024
TOP, BOT = (38, 70, 120), (18, 28, 56)
PATCH, PATCH_EDGE = (246, 196, 83), (196, 142, 38)
STITCH = (255, 255, 255)
ACCENT = (86, 214, 170)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
# vertical gradient tile with rounded corners
grad = Image.new("RGBA", (S, S))
gd = ImageDraw.Draw(grad)
for y in range(S):
    t = y / (S - 1)
    gd.line([(0, y), (S, y)], fill=tuple(round(TOP[i] + (BOT[i] - TOP[i]) * t) for i in range(3)) + (255,))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=210, fill=255)
img.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(img)
# the patch: tilted square with edge
patch = Image.new("RGBA", (S, S), (0, 0, 0, 0))
pd = ImageDraw.Draw(patch)
x0, y0, x1, y1 = 300, 300, 780, 780
pd.rounded_rectangle([x0 + 14, y0 + 20, x1 + 14, y1 + 20], radius=60, fill=(0, 0, 0, 90))
pd.rounded_rectangle([x0, y0, x1, y1], radius=60, fill=PATCH_EDGE)
pd.rounded_rectangle([x0 + 18, y0 + 18, x1 - 18, y1 - 18], radius=48, fill=PATCH)
# stitches around the inside edge
off = 52
n = 9
for i in range(n):
    f = i / (n - 1)
    a = x0 + off + f * (x1 - x0 - 2 * off)
    b = y0 + off + f * (y1 - y0 - 2 * off)
    L = 22
    pd.line([(a - L, y0 + off), (a + L, y0 + off)], fill=STITCH, width=11)
    pd.line([(a - L, y1 - off), (a + L, y1 - off)], fill=STITCH, width=11)
    pd.line([(x0 + off, b - L), (x0 + off, b + L)], fill=STITCH, width=11)
    pd.line([(x1 - off, b - L), (x1 - off, b + L)], fill=STITCH, width=11)
# a bracket mark "{ }" feel in the middle: two chevrons and a slash, drawn as lines
cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
w = 14 * 2
pd.line([(cx - 70, cy - 90), (cx - 150, cy), (cx - 70, cy + 90)], fill=(40, 52, 88), width=w, joint="curve")
pd.line([(cx + 70, cy - 90), (cx + 150, cy), (cx + 70, cy + 90)], fill=(40, 52, 88), width=w, joint="curve")
pd.line([(cx + 28, cy - 100), (cx - 28, cy + 100)], fill=ACCENT, width=w)
patch = patch.rotate(-8, resample=Image.BICUBIC, center=(S // 2, S // 2))
img.alpha_composite(patch)

os.makedirs("assets", exist_ok=True)
os.makedirs("site", exist_ok=True)
img.resize((512, 512), Image.LANCZOS).save("assets/icon.png", optimize=True)
img.resize((192, 192), Image.LANCZOS).save("assets/icon-192.png", optimize=True)
img.resize((32, 32), Image.LANCZOS).save("assets/favicon-32.png", optimize=True)
img.resize((64, 64), Image.LANCZOS).save("site/favicon.png", optimize=True)
print("wrote icons")
