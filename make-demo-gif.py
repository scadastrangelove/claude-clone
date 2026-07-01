#!/usr/bin/env python3
"""Render docs/demo.gif — a mock macOS Dock where a second, badged Claude icon
pops in next to the original. Purely illustrative; no screen recording needed.

Usage: python3 make-demo-gif.py [/path/to/electron.icns]
"""
import os, sys, math, tempfile, subprocess
from PIL import Image, ImageDraw, ImageFont

BASE = sys.argv[1] if len(sys.argv) > 1 else "/Applications/Claude.app/Contents/Resources/electron.icns"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "demo.gif")

W, H = 760, 300
ICON = 132
FONTS = ["/System/Library/Fonts/SFNSRounded.ttf", "/System/Library/Fonts/SFNS.ttf",
         "/System/Library/Fonts/HelveticaNeue.ttc"]


def font(sz):
    for p in FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def master(base):
    with tempfile.TemporaryDirectory() as t:
        iset = os.path.join(t, "b.iconset")
        subprocess.run(["iconutil", "-c", "iconset", base, "-o", iset], check=True)
        png = os.path.join(iset, "icon_512x512@2x.png")
        if not os.path.exists(png):
            png = max((os.path.join(iset, f) for f in os.listdir(iset)), key=os.path.getsize)
        return Image.open(png).convert("RGBA").resize((512, 512), Image.LANCZOS)


def variant(img, shift=150, letter="C"):
    r, g, b, a = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    h, s, v = hsv.split()
    h = h.point(lambda x: (x + shift) % 256)
    out = Image.merge("RGBA", (*Image.merge("HSV", (h, s, v)).convert("RGB").split(), a))
    d = ImageDraw.Draw(out)
    dd, m = 215, 20
    x1, y1 = 512 - m - dd, 512 - m - dd
    x2, y2 = x1 + dd, y1 + dd
    d.ellipse([x1 - 8, y1 - 8, x2 + 8, y2 + 8], fill=(255, 255, 255, 255))
    d.ellipse([x1, y1, x2, y2], fill=(20, 30, 66, 255))
    f = font(150)
    tb = d.textbbox((0, 0), letter, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text(((x1 + x2) / 2 - tw / 2 - tb[0], (y1 + y2) / 2 - th / 2 - tb[1]),
           letter, font=f, fill=(255, 255, 255, 255))
    return out


def bg():
    g = Image.new("RGB", (W, H))
    top, bot = (30, 30, 42), (44, 44, 60)
    px = g.load()
    for y in range(H):
        t = y / H
        px_row = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = px_row
    return g.convert("RGBA")


def dock_panel(base_img):
    pw, ph = 470, 176
    px, py = (W - pw) // 2, H - ph - 26
    panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=34, fill=(255, 255, 255, 30))
    pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=34,
                         outline=(255, 255, 255, 55), width=1)
    base_img.alpha_composite(panel, (px, py))
    return px, py, pw, ph


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def main():
    m = master(BASE)
    ic1 = m.resize((ICON, ICON), Image.LANCZOS)
    ic2 = variant(m).resize((ICON, ICON), Image.LANCZOS)
    cap = font(30)

    frames, N = [], 42
    # dock slot centers
    _bx = bg(); px, py, pw, ph = dock_panel(_bx)
    cy = py + ph // 2
    slot1 = (W // 2 - 90, cy)
    slot2 = (W // 2 + 90, cy)

    for i in range(N):
        fr = bg()
        dock_panel(fr)
        # caption fades in early
        alpha = min(255, int(255 * min(1.0, i / 8)))
        cap_img = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cap_img)
        text = "One Mac.  Two accounts."
        tb = cd.textbbox((0, 0), text, font=cap)
        cd.text(((W - (tb[2] - tb[0])) / 2, 4), text, font=cap, fill=(235, 235, 245, alpha))
        fr.alpha_composite(cap_img, (0, 30))

        # icon 1 always present
        fr.alpha_composite(ic1, (slot1[0] - ICON // 2, slot1[1] - ICON // 2))

        # icon 2: pop-in (frames 10-24) then one dock bounce (25-34)
        if i >= 10:
            if i <= 24:
                t = (i - 10) / 14
                sc = max(0.05, ease_out_back(t))
            else:
                sc = 1.0
            bounce = 0
            if 25 <= i <= 36:
                bounce = int(-46 * abs(math.sin((i - 25) / 11 * math.pi)) * (1 - (i - 25) / 11))
            s = max(8, int(ICON * sc))
            ic2s = ic2.resize((s, s), Image.LANCZOS)
            fr.alpha_composite(ic2s, (slot2[0] - s // 2, slot2[1] - s // 2 + bounce))

        frames.append(fr.convert("P", palette=Image.ADAPTIVE))

    # hold last frame
    frames += [frames[-1]] * 14
    frames[0].save(OUT, save_all=True, append_images=frames[1:], loop=0,
                   duration=60, disposal=2, optimize=True)
    # a static poster frame too
    frames[-1].convert("RGB").save(os.path.join(OUT_DIR, "demo.png"))
    print("wrote", OUT, "(", os.path.getsize(OUT) // 1024, "KB )")


if __name__ == "__main__":
    main()
