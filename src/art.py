# Launcher artwork. No game art is shipped or downloaded: the launcher draws its own background and
# title. A user may put their own images in art\ (hero.png, logo.png, icon.png, cover.png, wide.png),
# for example through an "art" .zip mod.
import os, random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import core


def path(kind):
    """The user's own art\\<kind>.png (or .jpg), or None when there isn't one."""
    for ext in ('.png', '.jpg', '.jpeg'):
        p = os.path.join(core.ART, kind + ext)
        if os.path.isfile(p):
            return p
    return None

# ---------------------------------------------------------------- drawn fallback

def background(w, h):
    """Dark smoke in the launcher's colours, used when there's no hero art."""
    rnd = random.Random(7)
    img = Image.new('RGB', (w, h), (12, 13, 17))
    glow = Image.new('RGB', (w, h), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    for _ in range(26):
        x, y = rnd.uniform(0.35, 1.05) * w, rnd.uniform(-0.1, 0.9) * h
        r = rnd.uniform(0.06, 0.22) * w
        c = rnd.choice([(226, 69, 43), (255, 106, 61), (140, 40, 30), (70, 75, 90), (40, 44, 56)])
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(v * rnd.uniform(0.25, 0.6)) for v in c))
    glow = glow.filter(ImageFilter.GaussianBlur(w / 14))
    return Image.blend(img, glow, 0.9)


def title_image(width=400):
    """The game's name in plain type (no logo artwork), with the launcher's name under it."""
    try:
        big = ImageFont.truetype('bahnschrift.ttf', 64)
        big.set_variation_by_name('Bold')
        small = ImageFont.truetype('bahnschrift.ttf', 30)
        small.set_variation_by_name('SemiBold')
    except (OSError, ValueError, AttributeError):
        big = small = ImageFont.load_default()
    img = Image.new('RGBA', (760, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((4, 0), 'inFAMOUS Second Son', font=big, fill=(236, 238, 243, 255))
    d.text((8, 78), 'Conduit Launcher', font=small, fill=(141, 148, 165, 255))
    img = img.crop(img.getbbox())
    s = width / img.width
    return img.resize((width, int(img.height * s)), Image.LANCZOS)
