#!/usr/bin/env python3
"""Build a distinct .icns for the second Claude instance.

Takes the stock app icon, hue-shifts the background to a different color, and
stamps a letter badge in the corner so the two Dock icons are unmistakable.

Requires Pillow (`pip3 install Pillow`) and macOS `iconutil` (built in).
"""
import argparse, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

SIZES = {
    "icon_16x16.png": 16,   "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,   "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128, "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256, "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512, "icon_512x512@2x.png": 1024,
}
FONTS = [
    "/System/Library/Fonts/SFNSRounded.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]


def load_master(base_icns, tmp):
    """Extract the largest PNG from the stock .icns as a 1024px RGBA master."""
    iconset = os.path.join(tmp, "base.iconset")
    subprocess.run(["iconutil", "-c", "iconset", base_icns, "-o", iconset],
                   check=True)
    png = os.path.join(iconset, "icon_512x512@2x.png")
    if not os.path.exists(png):  # fall back to the biggest available
        png = max((os.path.join(iconset, f) for f in os.listdir(iconset)),
                  key=os.path.getsize)
    return Image.open(png).convert("RGBA").resize((1024, 1024), Image.LANCZOS)


def hue_shift(img, shift):
    r, g, b, a = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    h, s, v = hsv.split()
    h = h.point(lambda x: (x + shift) % 256)
    rgb = Image.merge("HSV", (h, s, v)).convert("RGB")
    return Image.merge("RGBA", (*rgb.split(), a))


def add_badge(img, letter, fill=(20, 30, 66, 255)):
    draw = ImageDraw.Draw(img)
    d, m = 430, 40
    x1, y1 = 1024 - m - d, 1024 - m - d
    x2, y2 = x1 + d, y1 + d
    draw.ellipse([x1 - 16, y1 - 16, x2 + 16, y2 + 16], fill=(255, 255, 255, 255))
    draw.ellipse([x1, y1, x2, y2], fill=fill)
    font = None
    for p in FONTS:
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, 300); break
            except Exception:
                pass
    font = font or ImageFont.load_default()
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    tb = draw.textbbox((0, 0), letter, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    draw.text((cx - tw / 2 - tb[0], cy - th / 2 - tb[1]), letter,
              font=font, fill=(255, 255, 255, 255))
    return img


def build_icns(img, out, tmp):
    iconset = os.path.join(tmp, "out.iconset")
    os.makedirs(iconset, exist_ok=True)
    for name, sz in SIZES.items():
        img.resize((sz, sz), Image.LANCZOS).save(os.path.join(iconset, name))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="stock electron.icns")
    ap.add_argument("--out", required=True, help="output app.icns")
    ap.add_argument("--hue", type=int, default=150, help="hue shift 0-255")
    ap.add_argument("--letter", default="W", help="badge letter")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        img = load_master(args.base, tmp)
        img = hue_shift(img, args.hue % 256)
        img = add_badge(img, args.letter[:1].upper())
        build_icns(img, args.out, tmp)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"make-icon: {e}", file=sys.stderr)
        sys.exit(1)
