"""Procedural renderers for demo assets: damage photos and workshop bills.

Everything here is synthetic and fictional. Photos are stylised illustrations;
for a live demo with Gemini, drop real photos into sample-data/photos/<scenario>/
and they will be used instead (see README).
"""

from __future__ import annotations

import io
import math
import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

FONT_DIR = Path(__file__).parent / "fonts"
SS = 2  # supersampling factor for anti-aliased drawing


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    files = {
        "sans": "DejaVuSans.ttf",
        "bold": "DejaVuSans-Bold.ttf",
        "cond": "DejaVuSansCondensed-Bold.ttf",
        "mono": "DejaVuSansMono.ttf",
        "serif": "DejaVuSerif-Bold.ttf",
    }
    try:
        return ImageFont.truetype(str(FONT_DIR / files[name]), size)
    except Exception:
        return ImageFont.load_default(size)


def _s(v):
    """Scale a coordinate tuple/list by the supersampling factor."""
    if isinstance(v, (int, float)):
        return v * SS
    if isinstance(v, tuple) and all(isinstance(x, (int, float)) for x in v):
        return tuple(x * SS for x in v)
    return [_s(x) for x in v]


def _vgradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h))


def _noise(img: Image.Image, amount: int = 10, seed: int = 0) -> Image.Image:
    rnd = random.Random(seed)
    w, h = img.size
    small = Image.new("L", (w // 2, h // 2))
    small.putdata([128 + rnd.randint(-amount, amount) for _ in range((w // 2) * (h // 2))])
    n = small.resize((w, h)).convert("RGB")
    return Image.blend(img, ImageChops.overlay(img, n), 0.55)


def _vignette(img: Image.Image, strength: float = 0.45) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([-w * 0.15, -h * 0.2, w * 1.15, h * 1.2], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) // 6))
    dark = ImageEnhance.Brightness(img).enhance(1 - strength)
    return Image.composite(img, dark, mask)


def _shade(color, f):
    return tuple(max(0, min(255, int(c * f))) for c in color)


def _finish(img: Image.Image, seed: int, *, warmth=(255, 246, 232), blur=0.6, noise=9, vignette=0.4) -> Image.Image:
    img = img.resize((img.width // SS, img.height // SS), Image.Resampling.LANCZOS)
    tint = Image.new("RGB", img.size, warmth)
    img = ImageChops.multiply(img, tint)
    img = _noise(img, noise, seed)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    img = _vignette(img, vignette)
    return img


def _crack(d: ImageDraw.ImageDraw, start, length, angle, rnd: random.Random, width=3, color=(235, 235, 230), depth=0):
    x, y = start
    pts = [(x, y)]
    seg = length / 6
    for _ in range(6):
        angle += rnd.uniform(-0.6, 0.6)
        x += math.cos(angle) * seg
        y += math.sin(angle) * seg
        pts.append((x, y))
    d.line([(px + 2 * SS, py + 2 * SS) for px, py in pts], fill=(35, 35, 35), width=width * SS)
    d.line(pts, fill=color, width=max(1, (width - 1)) * SS)
    if depth < 2:
        for i in (2, 4):
            if rnd.random() < 0.8:
                _crack(d, pts[i], length * 0.45, angle + rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.2), rnd, max(1, width - 1), color, depth + 1)


def _dent(base: Image.Image, center, radius, darkness=0.55):
    """Radial shading that reads as a dent on a painted panel."""
    cx, cy = _s(center)
    rx, ry = _s(radius)
    mask = Image.new("L", base.size, 0)
    md = ImageDraw.Draw(mask)
    for i in range(12, 0, -1):
        f = i / 12
        md.ellipse([cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f], fill=int(255 * (1 - f) * darkness + 20))
    mask = mask.filter(ImageFilter.GaussianBlur(10 * SS))
    dark = ImageEnhance.Brightness(base).enhance(0.35)
    base.paste(Image.composite(dark, base, mask))
    # a bright rim highlight on the upper edge of the dent
    hl = Image.new("L", base.size, 0)
    hd = ImageDraw.Draw(hl)
    hd.arc([cx - rx, cy - ry * 1.05, cx + rx, cy + ry * 0.9], 200, 340, fill=150, width=6 * SS)
    hl = hl.filter(ImageFilter.GaussianBlur(4 * SS))
    bright = ImageEnhance.Brightness(base).enhance(1.6)
    base.paste(Image.composite(bright, base, hl))


def _scrapes(d: ImageDraw.ImageDraw, box, rnd: random.Random, n=40, color=(225, 222, 215), horizontal=False):
    x0, y0, x1, y1 = _s(box)
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(y0, y1)
        ln = rnd.uniform(20, 90) * SS
        ang = rnd.uniform(-0.15, 0.15) if horizontal else rnd.uniform(-0.6, 0.3)
        d.line([x, y, x + math.cos(ang) * ln, y + math.sin(ang) * ln], fill=color, width=rnd.choice([1, 1, 2, 3]) * SS)


def _street_background(size, rnd, daylight=True):
    w, h = size
    img = _vgradient(size, (176, 190, 204) if daylight else (24, 26, 34), (214, 214, 206) if daylight else (40, 40, 44))
    d = ImageDraw.Draw(img)
    # buildings band
    x = 0
    while x < w:
        bw = rnd.randint(140, 320) * SS
        bh = rnd.randint(260, 420) * SS
        tone = rnd.randint(150, 200) if daylight else rnd.randint(30, 50)
        d.rectangle([x, h * 0.42 - bh, x + bw, h * 0.42], fill=(tone, tone - 6, tone - 14))
        for wx in range(x + 20 * SS, x + bw - 20 * SS, 46 * SS):
            for wy in range(int(h * 0.42 - bh + 24 * SS), int(h * 0.42 - 20 * SS), 60 * SS):
                lit = (232, 210, 150) if (not daylight and rnd.random() < 0.4) else (_shade((tone, tone, tone + 10), 0.7))
                d.rectangle([wx, wy, wx + 22 * SS, wy + 30 * SS], fill=lit)
        x += bw + rnd.randint(4, 30) * SS
    # road
    road = _vgradient((w, int(h * 0.58)), (98, 98, 96) if daylight else (30, 30, 32), (70, 70, 68) if daylight else (18, 18, 20))
    img.paste(road, (0, int(h * 0.42)))
    for i in range(6):
        y = int(h * 0.45 + i * 70 * SS)
        d.polygon([(w * 0.47 - i * 6 * SS, y), (w * 0.53 + i * 6 * SS, y), (w * 0.535 + i * 7 * SS, y + 30 * SS), (w * 0.465 - i * 7 * SS, y + 30 * SS)],
                  fill=(205, 205, 195) if daylight else (90, 90, 88))
    return img


def render_rear_photo(*, color, plate, damage_side="left", seed=1, daylight=True, size=(1600, 1200)) -> Image.Image:
    """Rear view of a hatchback with bumper + tail lamp damage on one side."""
    rnd = random.Random(seed)
    W, H = _s(size[0]), _s(size[1])
    img = _street_background((W, H), rnd, daylight)
    d = ImageDraw.Draw(img)

    # ground shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse(_s([250, 890, 1350, 1000]), fill=200)
    sh = sh.filter(ImageFilter.GaussianBlur(25 * SS))
    img.paste(Image.new("RGB", (W, H), (20, 20, 22)), (0, 0), sh)

    dark = _shade(color, 0.62)
    mid = color
    light = _shade(color, 1.18)

    # tyres
    for x0 in (335, 1125):
        d.rounded_rectangle(_s([x0, 860, x0 + 140, 965]), radius=_s(18), fill=(22, 22, 24))
    # upper cabin
    d.polygon(_s([(430, 300), (1170, 300), (1262, 600), (338, 600)]), fill=mid)
    glass = _vgradient((_s(730), _s(230)), (40, 46, 58), (14, 16, 22))
    gmask = Image.new("L", glass.size, 0)
    ImageDraw.Draw(gmask).polygon([(_s(40), 0), (_s(690), 0), (_s(730), _s(230)), (0, _s(230))], fill=255)
    img.paste(glass, (_s(435), _s(338)), gmask)
    d = ImageDraw.Draw(img)
    d.line(_s([520, 360, 650, 520]), fill=(70, 80, 96), width=_s(10))  # reflection
    d.rounded_rectangle(_s([440, 286, 1160, 318]), radius=_s(12), fill=(28, 28, 30))  # spoiler
    d.rectangle(_s([760, 296, 840, 304]), fill=(200, 40, 40))  # brake light
    # lower body
    body = _vgradient((_s(960), _s(250)), light, dark)
    bmask = Image.new("L", body.size, 0)
    ImageDraw.Draw(bmask).rounded_rectangle([0, 0, body.width, body.height], radius=_s(40), fill=255)
    img.paste(body, (_s(320), _s(560)), bmask)
    d = ImageDraw.Draw(img)
    d.line(_s([420, 690, 1180, 690]), fill=_shade(color, 0.5), width=_s(3))  # tailgate crease
    d.ellipse(_s([775, 615, 825, 655]), outline=(210, 210, 214), width=_s(5))  # emblem
    # tail lamps
    for left in (True, False):
        pts = [(332, 590), (478, 590), (505, 702), (338, 712)] if left else [(1268, 590), (1122, 590), (1095, 702), (1262, 712)]
        d.polygon(_s(pts), fill=(150, 18, 22))
        inner = [(p[0] + (12 if left else -12), p[1] + 10) for p in pts[:2]] + [(pts[2][0] + (-10 if left else 10), pts[2][1] - 12), (pts[3][0] + (10 if left else -10), pts[3][1] - 12)]
        d.polygon(_s(inner), fill=(205, 34, 38))
        cx = 405 if left else 1195
        d.ellipse(_s([cx - 26, 625, cx + 26, 667]), fill=(250, 200, 190))
    # number plate (HSRP style)
    d.rounded_rectangle(_s([665, 712, 935, 772]), radius=_s(6), fill=(250, 250, 248), outline=(20, 20, 20), width=_s(3))
    d.rectangle(_s([669, 716, 699, 768]), fill=(30, 70, 160))
    d.text(_s((684, 750)), "IND", font=font("bold", _s(10)), fill=(255, 255, 255), anchor="mm")
    d.text(_s((817, 742)), plate, font=font("cond", _s(27)), fill=(15, 15, 15), anchor="mm")
    # bumper
    bump = _vgradient((_s(1000), _s(118)), _shade(color, 1.05), _shade(color, 0.55))
    bm = Image.new("L", bump.size, 0)
    ImageDraw.Draw(bm).rounded_rectangle([0, 0, bump.width, bump.height], radius=_s(46), fill=255)
    img.paste(bump, (_s(300), _s(790)), bm)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(_s([370, 872, 1230, 928]), radius=_s(20), fill=(26, 26, 28))
    d.rectangle(_s([330, 830, 380, 846]), fill=(170, 30, 30))
    d.rectangle(_s([1220, 830, 1270, 846]), fill=(170, 30, 30))

    # ---- damage -----------------------------------------------------------
    if damage_side in ("left", "right"):
        mirror = damage_side == "right"
        X = (lambda x: 1600 - x) if mirror else (lambda x: x)
        _dent(img, (X(425), 842), (130, 52), 0.7)
        d = ImageDraw.Draw(img)
        # bumper pushed in: dark gap between body and bumper
        d.polygon(_s([(X(300), 786), (X(520), 786), (X(300), 812)]), fill=(18, 18, 18))
        _scrapes(d, [min(X(320), X(540)), 805, max(X(320), X(540)), 875], rnd, 26, (214, 196, 190))
        for _ in range(2):
            _crack(d, _s((X(rnd.uniform(330, 380)), rnd.uniform(805, 830))), _s(200), (0.35 if not mirror else math.pi - 0.35), rnd, 3)
        # tail lamp: missing chunk + cracks
        cx = X(405)
        d.polygon(_s([(cx - 40, 655), (cx + 10, 640), (cx + 35, 690), (cx - 20, 700)]), fill=(28, 10, 10))
        for _ in range(3):
            _crack(d, _s((cx + rnd.uniform(-20, 20), 650 + rnd.uniform(-10, 10))), _s(70), rnd.uniform(0, math.tau), rnd, 2, (255, 220, 220))

    return _finish(img, seed, warmth=(255, 246, 232) if daylight else (210, 210, 255), noise=9 if daylight else 16,
                   blur=0.6 if daylight else 1.4, vignette=0.4 if daylight else 0.6)


def render_side_photo(*, color, seed=3, size=(1600, 1200)) -> Image.Image:
    """Left-side profile of a hatchback in a basement car park, scraped doors and broken mirror."""
    rnd = random.Random(seed)
    W, H = _s(size[0]), _s(size[1])
    img = _vgradient((W, H), (88, 90, 92), (60, 62, 64))
    d = ImageDraw.Draw(img)
    # ceiling, beams, lights
    d.rectangle([0, 0, W, _s(250)], fill=(110, 112, 112))
    for x in range(0, 1600, 400):
        d.rectangle(_s([x + 120, 90, x + 300, 104]), fill=(250, 250, 236))
    floor = _vgradient((W, _s(500)), (92, 94, 96), (52, 54, 56))
    img.paste(floor, (0, _s(700)))
    d = ImageDraw.Draw(img)
    d.polygon(_s([(0, 1080), (1600, 1040), (1600, 1060), (0, 1104)]), fill=(214, 180, 40))  # parking line
    # concrete pillar on the left of frame with hazard stripes
    d.rectangle(_s([40, 120, 230, 1000]), fill=(150, 150, 146))
    d.rectangle(_s([40, 120, 70, 1000]), fill=(120, 120, 118))
    for i in range(6):
        y = 840 + i * 26
        d.polygon(_s([(40, y), (230, y - 40), (230, y - 20), (40, y + 20)]), fill=(225, 190, 30) if i % 2 == 0 else (25, 25, 25))
    # shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse(_s([300, 910, 1500, 1010]), fill=210)
    sh = sh.filter(ImageFilter.GaussianBlur(24 * SS))
    img.paste(Image.new("RGB", (W, H), (15, 15, 17)), (0, 0), sh)
    d = ImageDraw.Draw(img)

    light, dark = _shade(color, 1.2), _shade(color, 0.6)
    body_poly = [(300, 860), (292, 650), (330, 600), (470, 455), (560, 430), (980, 430), (1080, 470), (1215, 590), (1380, 640), (1420, 700),
                 (1425, 860)]
    body = _vgradient((W, H), light, dark)
    bm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bm).polygon(_s(body_poly), fill=255)
    img.paste(body, (0, 0), bm)
    d = ImageDraw.Draw(img)
    # windows
    d.polygon(_s([(372, 600), (490, 475), (720, 465), (720, 600)]), fill=(26, 30, 38))
    d.polygon(_s([(738, 465), (965, 462), (1060, 600), (738, 600)]), fill=(26, 30, 38))
    d.line(_s([800, 480, 870, 590]), fill=(64, 74, 90), width=_s(8))
    # door seams + handles
    for x in (500, 740, 1075):
        d.line(_s([x, 470 if x != 500 else 600, x - 8, 850]), fill=_shade(color, 0.45), width=_s(3))
    d.line(_s([500, 600, 1075, 600]), fill=_shade(color, 0.45), width=_s(3))
    for x in (640, 960):
        d.rounded_rectangle(_s([x, 655, x + 70, 672]), radius=_s(6), fill=_shade(color, 0.55))
    d.line(_s([310, 760, 1415, 760]), fill=_shade(color, 1.35), width=_s(4))  # character line
    # wheels
    for cx in (470, 1185):
        d.ellipse(_s([cx - 125, 735, cx + 125, 985]), fill=(30, 30, 32))
        d.ellipse(_s([cx - 112, 748, cx + 112, 972]), fill=(18, 18, 20))
        d.ellipse(_s([cx - 70, 790, cx + 70, 930]), fill=(170, 172, 176))
        for k in range(5):
            a = k * math.tau / 5
            d.line(_s([cx, 860, cx + math.cos(a) * 64, 860 + math.sin(a) * 64]), fill=(110, 112, 116), width=_s(14))
        d.ellipse(_s([cx - 16, 844, cx + 16, 876]), fill=(60, 60, 64))
    d.ellipse(_s([1395, 662, 1425, 690]), fill=(240, 236, 210))  # headlamp edge
    # ---- damage: long scrape across both left doors, dent, broken mirror ----
    _dent(img, (880, 720), (190, 60), 0.6)
    _dent(img, (620, 735), (140, 48), 0.5)
    d = ImageDraw.Draw(img)
    _scrapes(d, [540, 690, 1040, 770], rnd, 120, (228, 226, 220), horizontal=True)
    _scrapes(d, [560, 700, 1000, 760], rnd, 60, (150, 150, 150), horizontal=True)
    # mirror housing knocked down and hanging
    d.polygon(_s([(1090, 640), (1160, 655), (1150, 715), (1080, 700)]), fill=_shade(color, 0.7))
    d.polygon(_s([(1100, 650), (1150, 662), (1142, 705), (1092, 694)]), fill=(150, 160, 170))
    _crack(d, _s((1110, 660)), _s(60), 1.0, rnd, 2)
    d.line(_s([1078, 618, 1095, 645]), fill=(20, 20, 20), width=_s(5))  # exposed wire
    # Drawn facing right; mirror so we look at the car's LEFT side (front on the viewer's left).
    img = ImageOps.mirror(img)
    return _finish(img, seed, warmth=(236, 244, 255), noise=12, blur=0.8, vignette=0.5)


def crop_zoom(img: Image.Image, box: tuple[float, float, float, float], out_size=(1600, 1200)) -> Image.Image:
    w, h = img.size
    region = img.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    region = region.resize(out_size, Image.Resampling.LANCZOS)
    return region.filter(ImageFilter.UnsharpMask(radius=2, percent=60))


def to_jpeg(img: Image.Image, *, taken_at: datetime | None = None, quality: int = 86, camera: str = "Pixel 8a") -> bytes:
    exif = Image.Exif()
    if taken_at:
        stamp = taken_at.strftime("%Y:%m:%d %H:%M:%S")
        exif[0x0110] = camera  # Model
        exif[0x010F] = "Google"  # Make
        exif[0x0132] = stamp  # DateTime
        exif_ifd = exif.get_ifd(0x8769)
        exif_ifd[0x9003] = stamp  # DateTimeOriginal
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality, exif=exif.tobytes() if taken_at else b"")
    return buf.getvalue()


def reuse_variant(jpeg: bytes, *, crop=0.06, brightness=1.08, darken=False, keep_exif=True, seed=7) -> bytes:
    """What a fraudster does: re-save an old photo with a crop and a filter."""
    img = Image.open(io.BytesIO(jpeg))
    exif = img.getexif()
    w, h = img.size
    img = img.crop((int(w * crop), int(h * crop * 0.6), int(w * (1 - crop * 0.4)), int(h * (1 - crop * 0.3))))
    img = img.resize((1440, int(1440 * img.height / img.width)), Image.Resampling.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.55 if darken else brightness)
    img = ImageEnhance.Contrast(img).enhance(0.9 if darken else 1.05)
    if darken:
        img = img.filter(ImageFilter.GaussianBlur(1.6))
        img = Image.blend(img, Image.new("RGB", img.size, (20, 22, 40)), 0.25)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80, exif=exif.tobytes() if keep_exif else b"")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Bills
# ---------------------------------------------------------------------------

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _words_99(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])


def _words_999(n):
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " hundred")
    if r:
        parts.append(_words_99(r))
    return " ".join(parts)


def rupees_in_words(amount: int) -> str:
    """Indian numbering: 85,196 -> 'Eighty-five thousand one hundred ninety-six'."""
    n = int(round(amount))
    if n == 0:
        return "Zero"
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    parts = []
    if crore:
        parts.append(_words_999(crore) + " crore")
    if lakh:
        parts.append(_words_99(lakh) + " lakh")
    if thousand:
        parts.append(_words_99(thousand) + " thousand")
    if n:
        parts.append(_words_999(n))
    s = " ".join(parts)
    return s[0].upper() + s[1:]


def _inr(x: float) -> str:
    neg = x < 0
    x = abs(x)
    whole = int(x)
    frac = round((x - whole) * 100)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-" if neg else "") + f"{s}.{frac:02d}"


def render_bill(spec: dict, seed: int = 11) -> Image.Image:
    """spec keys: vendor, address, phone, gstin, title, number, date, customer, vehicle,
    model, items[(desc, hsn, qty, rate)], tax_rate, tamper_total (optional), stamp_color."""
    rnd = random.Random(seed)
    W, H = 1240, 1754
    page = Image.new("RGB", (W, H), (252, 251, 247))
    d = ImageDraw.Draw(page)
    ink = (28, 30, 36)
    accent = spec.get("accent", (24, 76, 140))

    d.rectangle([0, 0, W, 16], fill=accent)
    d.text((70, 70), spec["vendor"], font=font("bold", 44), fill=accent)
    y = 128
    for line in spec["address"].split("\n"):
        d.text((70, y), line, font=font("sans", 22), fill=ink)
        y += 30
    d.text((70, y + 4), f"Ph: {spec['phone']}    GSTIN: {spec['gstin']}", font=font("sans", 22), fill=ink)
    d.text((W - 70, 78), spec["title"], font=font("bold", 40), fill=ink, anchor="ra")
    d.text((W - 70, 136), f"No: {spec['number']}", font=font("sans", 24), fill=ink, anchor="ra")
    d.text((W - 70, 170), f"Date: {spec['date']}", font=font("sans", 24), fill=ink, anchor="ra")
    d.line([70, 290, W - 70, 290], fill=ink, width=2)

    d.text((70, 312), "Bill to", font=font("bold", 22), fill=(110, 110, 110))
    d.text((70, 342), spec["customer"], font=font("bold", 28), fill=ink)
    d.text((70, 380), f"Vehicle: {spec['vehicle']}   ·   {spec['model']}", font=font("sans", 24), fill=ink)
    if spec.get("job_note"):
        d.text((70, 414), spec["job_note"], font=font("sans", 22), fill=(80, 80, 80))

    # table
    top = 470
    cols = [70, 140, 690, 830, 920, 1170]
    d.rectangle([70, top, W - 70, top + 52], fill=(234, 238, 244))
    for x, label in zip([84, 154, 704, 844, 0], ["#", "Description", "HSN/SAC", "Qty", ""]):
        if label:
            d.text((x, top + 14), label, font=font("bold", 22), fill=ink)
    d.text((cols[5] - 10, top + 14), "Amount (Rs)", font=font("bold", 22), fill=ink, anchor="ra")
    y = top + 70
    subtotal = 0.0
    for i, (desc, hsn, qty, rate) in enumerate(spec["items"], 1):
        amount = qty * rate
        subtotal += amount
        d.text((84, y), str(i), font=font("sans", 23), fill=ink)
        d.text((154, y), desc, font=font("sans", 23), fill=ink)
        d.text((704, y), hsn, font=font("sans", 21), fill=(90, 90, 90))
        d.text((860, y), f"{qty:g}", font=font("sans", 23), fill=ink)
        d.text((cols[5] - 10, y), _inr(amount), font=font("mono", 24), fill=ink, anchor="ra")
        y += 46
        d.line([70, y - 8, W - 70, y - 8], fill=(222, 222, 222), width=1)
    y += 20
    tax_rate = spec.get("tax_rate", 0.18)
    cgst = round(subtotal * tax_rate / 2, 2)
    sgst = cgst
    total = subtotal + cgst + sgst
    rounded = round(total)
    rows = [
        ("Subtotal", subtotal),
        (f"CGST @ {tax_rate * 50:g}%", cgst),
        (f"SGST @ {tax_rate * 50:g}%", sgst),
        ("Round off", rounded - total),
    ]
    for label, val in rows:
        d.text((820, y), label, font=font("sans", 24), fill=ink)
        d.text((cols[5] - 10, y), _inr(val), font=font("mono", 24), fill=ink, anchor="ra")
        y += 40
    d.line([800, y + 4, W - 70, y + 4], fill=ink, width=2)
    y += 20
    d.text((820, y), "Grand total", font=font("bold", 28), fill=ink)
    printed_total = rounded
    if spec.get("tamper_total"):
        printed_total = spec["tamper_total"]
        # white-out patch, then a figure typed in a different font, slightly off-baseline
        d.rectangle([cols[5] - 178, y - 6, cols[5] - 2, y + 40], fill=(255, 255, 255))
        d.text((cols[5] - 6, y + 5), _inr(printed_total), font=font("serif", 29), fill=(20, 20, 60), anchor="ra")
    else:
        d.text((cols[5] - 10, y), _inr(printed_total), font=font("mono", 28), fill=ink, anchor="ra")
    y += 70
    words_amount = rounded  # words always reflect the real arithmetic
    d.text((70, y), f"Amount in words: Rupees {rupees_in_words(words_amount)} only", font=font("sans", 22), fill=ink)
    y += 70
    if spec.get("terms"):
        for t in spec["terms"]:
            d.text((70, y), "• " + t, font=font("sans", 20), fill=(90, 90, 90))
            y += 30

    # stamp + signature
    sc = spec.get("stamp_color", (40, 70, 160))
    stamp = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.ellipse([10, 10, 290, 290], outline=sc + (170,), width=6)
    sd.ellipse([40, 40, 260, 260], outline=sc + (150,), width=3)
    short = spec["vendor"].split()[0:2]
    sd.text((150, 130), " ".join(short).upper(), font=font("bold", 26), fill=sc + (170,), anchor="mm")
    sd.text((150, 175), spec.get("stamp_city", "HYDERABAD"), font=font("sans", 20), fill=sc + (160,), anchor="mm")
    stamp = stamp.rotate(rnd.uniform(-18, 18), resample=Image.Resampling.BICUBIC)
    page.paste(stamp, (W - 420, H - 470), stamp)
    d.line([W - 420, H - 220, W - 120, H - 225], fill=(30, 30, 80), width=2)
    d.text((W - 270, H - 205), "Authorised signatory", font=font("sans", 20), fill=ink, anchor="ma")
    d.text((70, H - 90), spec.get("footer", "Fictional business · ClaimPilot sample data"), font=font("sans", 17), fill=(150, 150, 150))

    # photograph-of-paper look
    canvas = Image.new("RGB", (W + 160, H + 160), (118, 104, 88))
    shadow = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(shadow).rectangle([90, 95, W + 90, H + 95], fill=140)
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(Image.new("RGB", canvas.size, (40, 32, 26)), (0, 0), shadow)
    canvas.paste(page, (80, 80))
    canvas = canvas.rotate(rnd.uniform(-0.9, 0.9), resample=Image.Resampling.BICUBIC, fillcolor=(118, 104, 88))
    light = _vgradient(canvas.size, (255, 255, 250), (232, 228, 218))
    canvas = ImageChops.multiply(canvas, light)
    canvas = _noise(canvas, 6, seed)
    return canvas.resize((1100, int(1100 * canvas.height / canvas.width)), Image.Resampling.LANCZOS)


def bill_totals(spec: dict) -> dict:
    subtotal = sum(q * r for _, _, q, r in spec["items"])
    tax = round(subtotal * spec.get("tax_rate", 0.18) / 2, 2) * 2
    true_total = round(subtotal + tax)
    return {"subtotal": subtotal, "tax": tax, "true_total": true_total,
            "printed_total": spec.get("tamper_total") or true_total}
