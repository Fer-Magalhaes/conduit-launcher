# Draws a DualShock 4 seen from above with PIL (supersampled), and where each part is.
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
SYMBOL = {'triangle': (64, 224, 176), 'circle': (255, 102, 112), 'cross': (127, 168, 255), 'square': (255, 140, 216)}
ACCENT = (255, 106, 61)


def _font(name, size):
    for n in (name, 'segoeuib.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(os.path.join(FONTS, n), size)
        except OSError:
            pass
    return ImageFont.load_default()


def _cubic(p0, p1, p2, p3, n=28):
    out = []
    for i in range(1, n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _outline():
    """Body outline in a 0..1 box (right half built from curves, left half mirrored)."""
    segs = [((0.5, 0.035), (0.62, 0.035), (0.75, 0.04), (0.83, 0.05)),
            ((0.83, 0.05), (0.945, 0.062), (0.995, 0.15), (1.0, 0.32)),
            ((1.0, 0.32), (1.008, 0.55), (0.985, 0.84), (0.935, 0.965)),
            ((0.935, 0.965), (0.90, 1.03), (0.81, 1.02), (0.775, 0.955)),
            ((0.775, 0.955), (0.74, 0.87), (0.70, 0.73), (0.645, 0.685)),
            ((0.645, 0.685), (0.59, 0.662), (0.55, 0.665), (0.5, 0.665))]
    right = [(0.5, 0.035)]
    for s in segs:
        right += _cubic(*s)
    left = [(1 - x, y) for x, y in reversed(right[1:-1])]
    return right + left


def _vgrad(size, top, bottom):
    w, h = size
    g = Image.new('RGB', (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h))


def _radial(r, inner, outer, hl=(0.35, 0.3)):
    size = 2 * r
    img = Image.new('RGB', (size, size), outer)
    d = ImageDraw.Draw(img)
    cx, cy = size * hl[0], size * hl[1]
    steps = 24
    for i in range(steps, 0, -1):
        t = i / steps
        col = tuple(int(inner[k] + (outer[k] - inner[k]) * t) for k in range(3))
        rr = size * 0.95 * t
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    return img.filter(ImageFilter.GaussianBlur(size / 18))


def _paste_circle(base, img, cx, cy):
    r = img.width // 2
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, img.width - 1, img.height - 1), fill=255)
    base.paste(img, (int(cx - r), int(cy - r)), m)


def render(width, light=ACCENT):
    """Returns (RGBA image, {part: (x, y, radius)}) for a pad image `width` pixels wide."""
    S = 3
    W = width * S
    bw = W * 0.86
    bh = bw * 0.62
    mx = (W - bw) / 2
    my = bh * 0.13
    H = int(my + bh * 1.06 + 8 * S)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(u, v):
        return mx + u * bw, my + v * bh

    parts = {}

    def part(name, u, v, r):
        x, y = P(u, v)
        parts[name] = (x / S, y / S, r / S)

    # triggers and shoulders behind the body
    small = _font('bahnschrift.ttf', int(bw * 0.032))
    for side, (u1, u2) in (('l', (0.13, 0.31)), ('r', (0.69, 0.87))):
        x1, y1 = P(u1, -0.11)
        x2, y2 = P(u2, 0.03)
        d.rounded_rectangle((x1, y1, x2, y2), radius=bw * 0.03, fill=(24, 26, 32), outline=(58, 63, 76), width=S)
        d.text(((x1 + x2) / 2, y1 + (y2 - y1) * 0.36), side.upper() + '2', font=small, fill=(140, 148, 165),
               anchor='mm')
        part(side + '2', (u1 + u2) / 2, -0.07, bw * 0.06)
        x1, y1 = P(u1 - 0.015, -0.025)
        x2, y2 = P(u2 + 0.015, 0.075)
        d.rounded_rectangle((x1, y1, x2, y2), radius=bw * 0.035, fill=(40, 44, 54), outline=(70, 76, 92), width=S)
        d.text(((x1 + x2) / 2, y1 + (y2 - y1) * 0.3), side.upper() + '1', font=small, fill=(140, 148, 165),
               anchor='mm')
        part(side + '1', (u1 + u2) / 2, 0.0, bw * 0.05)

    # body with a soft shadow
    poly = [P(u, v) for u, v in _outline()]
    shadow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(shadow).polygon([(x, y + 6 * S) for x, y in poly], fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(9 * S))
    img.paste((0, 0, 0, 255), (0, 0), shadow)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    img.paste(_vgrad((W, H), (58, 63, 76), (24, 27, 33)), (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.line(poly + [poly[0]], fill=(84, 91, 108), width=2 * S, joint='curve')
    # top sheen
    sheen = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sheen).polygon([P(u, v + 0.012) for u, v in _outline() if v < 0.2], fill=40)
    img.paste((255, 255, 255, 255), (0, 0), sheen.filter(ImageFilter.GaussianBlur(6 * S)))

    # light bar glow above the touch pad
    glow = Image.new('L', (W, H), 0)
    gx1, gy1 = P(0.37, 0.036)
    gx2, gy2 = P(0.63, 0.052)
    ImageDraw.Draw(glow).rounded_rectangle((gx1, gy1, gx2, gy2), radius=3 * S, fill=255)
    img.paste(light + (255,), (0, 0), glow.filter(ImageFilter.GaussianBlur(5 * S)))
    d.rounded_rectangle((gx1, gy1, gx2, gy2), radius=3 * S, fill=tuple(min(255, c + 40) for c in light))

    # touch pad
    tx1, ty1 = P(0.335, 0.075)
    tx2, ty2 = P(0.665, 0.40)
    tmask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(tmask).rounded_rectangle((tx1, ty1, tx2, ty2), radius=bw * 0.025, fill=255)
    img.paste(_vgrad((W, H), (50, 55, 67), (34, 37, 46)), (0, 0), tmask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((tx1, ty1, tx2, ty2), radius=bw * 0.025, outline=(80, 87, 104), width=S)
    part('touchpad', 0.5, 0.24, bw * 0.16)

    # share / options
    for name, u in (('share', 0.285), ('options', 0.715)):
        x, y = P(u, 0.17)
        d.rounded_rectangle((x - bw * 0.011, y - bw * 0.03, x + bw * 0.011, y + bw * 0.03), radius=bw * 0.011,
                            fill=(66, 72, 86), outline=(96, 104, 122), width=S)
        d.text(P(u, 0.10), name.upper(), font=_font('bahnschrift.ttf', int(bw * 0.022)),
               fill=(120, 128, 146), anchor='mm')
        part(name, u, 0.17, bw * 0.035)

    # d-pad
    cx, cy = P(0.205, 0.33)
    rr = bw * 0.078
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(22, 24, 30), outline=(46, 50, 60), width=S)
    a, k = bw * 0.026, bw * 0.062
    for name, (dx, dy) in (('pad_up', (0, -1)), ('pad_down', (0, 1)), ('pad_left', (-1, 0)),
                           ('pad_right', (1, 0))):
        # a key: square-ish block pointing outward with a bevelled inner tip
        px, py = -dy, dx
        tip = (cx + dx * a * 0.55, cy + dy * a * 0.55)
        pts = [(tip[0] + px * a * 0.0, tip[1] + py * a * 0.0),
               (cx + dx * a * 1.0 + px * a, cy + dy * a * 1.0 + py * a),
               (cx + dx * k + px * a, cy + dy * k + py * a),
               (cx + dx * k - px * a, cy + dy * k - py * a),
               (cx + dx * a * 1.0 - px * a, cy + dy * a * 1.0 - py * a)]
        d.polygon(pts, fill=(64, 70, 84), outline=(98, 106, 124))
        ax, ay = cx + dx * k * 0.78, cy + dy * k * 0.78
        s = a * 0.38
        d.polygon([(ax + dx * s, ay + dy * s), (ax - dx * s * 0.6 + px * s, ay - dy * s * 0.6 + py * s),
                   (ax - dx * s * 0.6 - px * s, ay - dy * s * 0.6 - py * s)], fill=(150, 158, 176))
        parts[name] = ((cx + dx * k * 0.7) / S, (cy + dy * k * 0.7) / S, a * 1.1 / S)

    # face buttons
    cx, cy = P(0.795, 0.33)
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(22, 24, 30), outline=(46, 50, 60), width=S)
    off, br = bw * 0.047, int(bw * 0.027)
    for name, (dx, dy) in (('triangle', (0, -1)), ('circle', (1, 0)), ('cross', (0, 1)), ('square', (-1, 0))):
        x, y = cx + dx * off, cy + dy * off
        _paste_circle(img, _radial(br, (92, 98, 114), (34, 37, 45)), x, y)
        d = ImageDraw.Draw(img)
        d.ellipse((x - br, y - br, x + br, y + br), outline=(20, 22, 27), width=S)
        col, s, w = SYMBOL[name], br * 0.5, max(2, int(br * 0.14))
        if name == 'triangle':
            d.polygon([(x, y - s), (x + s * 0.95, y + s * 0.65), (x - s * 0.95, y + s * 0.65)], outline=col, width=w)
        elif name == 'circle':
            d.ellipse((x - s * 0.85, y - s * 0.85, x + s * 0.85, y + s * 0.85), outline=col, width=w)
        elif name == 'cross':
            d.line((x - s * 0.8, y - s * 0.8, x + s * 0.8, y + s * 0.8), fill=col, width=w)
            d.line((x - s * 0.8, y + s * 0.8, x + s * 0.8, y - s * 0.8), fill=col, width=w)
        else:
            d.rectangle((x - s * 0.75, y - s * 0.75, x + s * 0.75, y + s * 0.75), outline=col, width=w)
        parts[name] = (x / S, y / S, br * 1.15 / S)

    # speaker and PS button
    for i in range(-3, 4):
        for j in range(3):
            x, y = P(0.5 + i * 0.012, 0.455 + j * 0.017)
            d.ellipse((x - S, y - S, x + S, y + S), fill=(16, 18, 22))
    x, y = P(0.5, 0.585)
    pr = bw * 0.022
    _paste_circle(img, _radial(int(pr), (70, 76, 90), (30, 33, 40)), x, y)
    d = ImageDraw.Draw(img)
    d.text((x, y), 'PS', font=_font('bahnschrift.ttf', int(pr * 0.9)), fill=(150, 158, 176), anchor='mm')

    # sticks
    for side, u in (('l', 0.355), ('r', 0.645)):
        x, y = P(u, 0.585)
        wr = bw * 0.068
        d.ellipse((x - wr, y - wr, x + wr, y + wr), fill=(14, 15, 19), outline=(52, 56, 66), width=S)
        cr = int(bw * 0.05)
        _paste_circle(img, _radial(cr, (98, 104, 120), (30, 33, 40), (0.4, 0.32)), x, y)
        d = ImageDraw.Draw(img)
        d.ellipse((x - cr * 0.62, y - cr * 0.62, x + cr * 0.62, y + cr * 0.62), outline=(40, 43, 52), width=S)
        d.ellipse((x - cr, y - cr, x + cr, y + cr), outline=(18, 20, 24), width=S)
        parts[side + 'stick'] = (x / S, y / S, wr / S)
        parts[side + '3'] = (x / S, y / S, cr * 0.7 / S)

    img = img.resize((width, H // S), Image.LANCZOS)
    return img, parts


def touchpad_art(width, light=ACCENT):
    """Close-up of the touch pad with the two finger spots and swipe arrows, for the touch page."""
    S = 3
    W, H = width * S, int(width * 0.52) * S
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = (W * 0.04, H * 0.14, W * 0.96, H * 0.96)
    shadow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((pad[0], pad[1] + 8 * S, pad[2], pad[3] + 8 * S), radius=W * 0.05,
                                             fill=160)
    img.paste((0, 0, 0, 255), (0, 0), shadow.filter(ImageFilter.GaussianBlur(10 * S)))
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle(pad, radius=W * 0.05, fill=255)
    img.paste(_vgrad((W, H), (54, 59, 72), (30, 33, 41)), (0, 0), m)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(pad, radius=W * 0.05, outline=(88, 95, 112), width=2 * S)
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).rounded_rectangle((W * 0.2, H * 0.05, W * 0.8, H * 0.09), radius=3 * S, fill=255)
    img.paste(light + (255,), (0, 0), glow.filter(ImageFilter.GaussianBlur(6 * S)))
    d.rounded_rectangle((W * 0.2, H * 0.05, W * 0.8, H * 0.09), radius=3 * S,
                        fill=tuple(min(255, c + 40) for c in light))
    f = _font('bahnschrift.ttf', int(H * 0.09))
    spots = {}
    for i, u in enumerate((0.27, 0.73)):
        x, y = W * u, H * 0.55
        r = H * 0.12
        g = Image.new('L', (W, H), 0)
        ImageDraw.Draw(g).ellipse((x - r * 1.5, y - r * 1.5, x + r * 1.5, y + r * 1.5), fill=110)
        img.paste(light + (255,), (0, 0), g.filter(ImageFilter.GaussianBlur(r * 0.6)))
        d = ImageDraw.Draw(img)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(240, 242, 246), outline=light, width=2 * S)
        d.text((x, y), str(i + 1), font=f, fill=(30, 33, 41), anchor='mm')
        spots['finger%d' % (i + 1)] = (x / S, y / S)
    # swipe arrows in the middle
    cx, cy, L = W * 0.5, H * 0.55, H * 0.2
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        x2, y2 = cx + dx * L, cy + dy * L
        d.line((cx + dx * L * 0.3, cy + dy * L * 0.3, x2, y2), fill=(150, 158, 176), width=2 * S)
        s = L * 0.18
        px, py = -dy, dx
        d.polygon([(x2 + dx * s, y2 + dy * s), (x2 + px * s * 0.7, y2 + py * s * 0.7),
                   (x2 - px * s * 0.7, y2 - py * s * 0.7)], fill=(150, 158, 176))
    return img.resize((W // S, H // S), Image.LANCZOS), spots
