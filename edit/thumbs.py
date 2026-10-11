"""
youtube thumbnails, 1280x720, no face: a drawn booster pack whose shadow is a question mark, plus one number in the
video's own graphic language (chapter tag, callout plate, palette, Inter).

  python3 edit/thumbs.py      -> results/thumbs/<design>.png
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graphics import font, SURF, INK, INK2, MUTED, BLUE, AQUA, YELLOW, MAGENTA, RED

W, H = 1280, 720
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'thumbs'); os.makedirs(OUT, exist_ok=True)
CH = os.path.join(os.path.dirname(OUT), 'charts')

# ----------------------------------------------------------------------------- the surface
def bg(accent=None, pool=(900, 400)):
    """same dark surface as the edit, faint grid, a soft pool of light where the pack sits, accent bar on the left."""
    y, x = np.mgrid[0:H, 0:W].astype(float)
    r = np.sqrt(((x - pool[0]) / 560) ** 2 + ((y - pool[1]) / 420) ** 2)
    glow = np.clip(1 - r, 0, 1) ** 1.6
    base = np.array(SURF, float); arr = base + glow[..., None] * (np.array((52, 54, 60)) - base)
    img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGB').convert('RGBA'); d = ImageDraw.Draw(img)
    for gx in range(0, W, 64): d.line([(gx, 0), (gx, H)], fill=(255, 255, 255, 3))
    for gy in range(0, H, 64): d.line([(0, gy), (W, gy)], fill=(255, 255, 255, 3))
    if accent: d.rectangle((0, 0, 18, H), fill=accent)
    return img

def plate(img, box, alpha=235, radius=14):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(22, 22, 21, alpha))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10))); img.alpha_composite(layer)

def callout(img, xy, big, small, col, fb=200, fs=46, w=None):
    d = ImageDraw.Draw(img); FB, FS = font('black', fb), font('bold', fs)
    bw, bh = d.textbbox((0, 0), big, font=FB)[2:]; sw = d.textbbox((0, 0), small, font=FS)[2]
    x0, y0 = xy; w = w or max(bw, sw) + 90; h = bh + 30 + fs + 34
    plate(img, (x0, y0, x0 + w, y0 + h)); d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + 12, y0 + h), fill=col)
    d.text((x0 + 44, y0 + 10), big, font=FB, fill=col); d.text((x0 + 46, y0 + bh + 34), small, font=FS, fill=INK2)
    return x0 + w, y0 + h

def tag(img, xy, a, b):
    d = ImageDraw.Draw(img); fa, fb_ = font('semi', 30), font('bold', 46)
    w = max(d.textbbox((0, 0), a, font=fa)[2], d.textbbox((0, 0), b, font=fb_)[2]) + 70
    x0, y0 = xy; plate(img, (x0, y0, x0 + w, y0 + 120)); d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + 8, y0 + 120), fill=YELLOW)
    d.text((x0 + 34, y0 + 16), a.upper(), font=fa, fill=YELLOW); d.text((x0 + 34, y0 + 54), b, font=fb_, fill=INK)

# ----------------------------------------------------------------------------- the pack
def pack(w=340, h=500, col=(43, 95, 168), col2=(24, 48, 96), label='2027', mark='?'):
    """a sealed booster: crimped top and bottom, foil sheen, a question mark where the art would be. no logos."""
    pad = 40; img = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = pad, pad, pad + w, pad + h; crimp = 34; tooth = 14
    # body with a vertical gradient
    body = Image.new('RGBA', img.size, (0, 0, 0, 0)); bd = ImageDraw.Draw(body)
    for i in range(h):
        t = i / h; c = tuple(int(col[k] * (1 - t) + col2[k] * t) for k in range(3))
        bd.line([(x0, y0 + i), (x1, y0 + i)], fill=c + (255,))
    # foil sheen: a diagonal light band
    sheen = Image.new('L', img.size, 0); sd = ImageDraw.Draw(sheen)
    sd.polygon([(x0 + 40, y0), (x0 + 150, y0), (x1, y1 - 170), (x1, y1 - 60)], fill=90)
    sd.polygon([(x0, y0 + 300), (x0, y0 + 360), (x1 - 40, y1), (x1 - 150, y1)], fill=40)
    sheen = sheen.filter(ImageFilter.GaussianBlur(14))
    light = Image.new('RGBA', img.size, (255, 255, 255, 0)); light.putalpha(sheen); body.alpha_composite(light)
    # crimps: zigzag teeth cut out of top and bottom, and a pressed band
    mask = Image.new('L', img.size, 0); md = ImageDraw.Draw(mask); md.rectangle((x0, y0, x1, y1), fill=255)
    top = [(x0, y0)]; x = x0
    while x < x1: top += [(x + tooth / 2, y0 + 10), (x + tooth, y0)]; x += tooth
    md.polygon(top + [(x1, y0 - 1), (x0, y0 - 1)], fill=0)
    bot = [(x0, y1)]; x = x0
    while x < x1: bot += [(x + tooth / 2, y1 - 10), (x + tooth, y1)]; x += tooth
    md.polygon(bot + [(x1, y1 + 1), (x0, y1 + 1)], fill=0)
    body.putalpha(ImageChops.multiply(body.getchannel('A'), mask))
    bd = ImageDraw.Draw(body)
    for yy in (y0 + 14, y1 - 14 - crimp):
        bd.rectangle((x0, yy, x1, yy + crimp), fill=(0, 0, 0, 70))
        for xx in range(x0, x1, 12): bd.line([(xx, yy + 4), (xx, yy + crimp - 4)], fill=(255, 255, 255, 28), width=2)
    # the "window": a darker panel where card art would be, with the mark in it
    bd.rounded_rectangle((x0 + 38, y0 + 86, x1 - 38, y1 - 120), radius=18, fill=(10, 14, 28, 150), outline=(255, 255, 255, 60), width=3)
    f = font('black', 260); tw, th = bd.textbbox((0, 0), mark or ' ', font=f)[2:]
    cx, cy = (x0 + x1) / 2, (y0 + 86 + y1 - 120) / 2
    glow = Image.new('RGBA', img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.text((cx - tw / 2, cy - th / 2 - 30), mark, font=f, fill=YELLOW + (255,)); glow = glow.filter(ImageFilter.GaussianBlur(18))
    body.alpha_composite(glow); bd = ImageDraw.Draw(body)
    bd.text((cx - tw / 2, cy - th / 2 - 30), mark, font=f, fill=INK + (255,))
    if not mark:   # empty window: a faint echo of the question, so the art area doesn't read as a blank screen
        fq = font('black', 230); qw, qh = bd.textbbox((0, 0), '?', font=fq)[2:]
        bd.text((cx - qw / 2, cy - qh / 2 - 30), '?', font=fq, fill=(255, 255, 255, 34))
    fl = font('black', 34); lw = bd.textbbox((0, 0), label, font=fl)[2]
    bd.text((cx - lw / 2, y1 - 104), label, font=fl, fill=(255, 255, 255, 230))
    bd.text((cx - bd.textbbox((0, 0), 'BOOSTER', font=font('semi', 22))[2] / 2, y1 - 62), 'BOOSTER', font=font('semi', 22), fill=(255, 255, 255, 170))
    # edge highlight
    bd.rectangle((x0, y0 + 10, x0 + 3, y1 - 10), fill=(255, 255, 255, 70)); bd.rectangle((x1 - 3, y0 + 10, x1, y1 - 10), fill=(0, 0, 0, 90))
    return body

def question_shadow(img, center, col, size=700, dx=255, dy=105):
    """the pack's shadow is a question mark: a big '?' in the design colour, dark and soft, thrown behind and
    below-right of the pack, big enough to show around it. (a true cast shadow is invisible on a dark surface.)"""
    f = font('black', size); layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    tw, th = d.textbbox((0, 0), '?', font=f)[2:]
    x, y = center[0] + dx - tw / 2, center[1] + dy - th / 2 - size * 0.10
    dark = tuple(int(c * 0.42) for c in col)
    d.text((x, y), '?', font=f, fill=dark + (235,))
    layer = layer.transform(layer.size, Image.AFFINE, (1, 0.18, -0.18 * center[1], 0, 1, 0), resample=Image.BICUBIC)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))

def place_pack(img, center, rot=-8, scale=1.0, **kw):
    p = pack(**kw); p = p.resize((int(p.width * scale), int(p.height * scale)), Image.LANCZOS).rotate(rot, resample=Image.BICUBIC, expand=True)
    soft = Image.new('RGBA', p.size, (0, 0, 0, 0)); soft.putalpha(p.getchannel('A').filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.7)))
    cx, cy = center; img.alpha_composite(soft, (int(cx - p.width / 2) + 10, int(cy - p.height / 2) + 26))
    img.alpha_composite(p, (int(cx - p.width / 2), int(cy - p.height / 2)))

def hero(img, col, center=(880, 360), rot=-8, scale=0.92, **kw):
    question_shadow(img, center, col)
    place_pack(img, center, rot=rot, scale=scale, mark='', **kw)

# ----------------------------------------------------------------------------- designs
def d_six_cents():
    img = bg(BLUE); hero(img, BLUE)
    tag(img, (56, 44), 'the 2027 god pack', 'what it adds to every pack')
    callout(img, (56, 200), '6¢', 'on a $5.49 pack', BLUE, fb=300, fs=50)
    return img

def d_ev():
    img = bg(AQUA); hero(img, AQUA)
    tag(img, (56, 44), 'ten years of boxes', 'is opening boosters +EV?')
    x, y = callout(img, (56, 190), '$1.35', 'of cards per $1, on paper', AQUA, fb=150, fs=42)
    callout(img, (56, y + 18), '49¢', 'per $1 once you sell it', RED, fb=150, fs=42, w=x - 56)
    return img

def d_myth():
    img = bg(MAGENTA); hero(img, MAGENTA)
    plate(img, (56, 44, 740, 660)); d = ImageDraw.Draw(img)
    d.text((96, 70), 'MYTH', font=font('black', 56), fill=RED)
    d.text((96, 134), '"god packs make', font=font('bold', 54), fill=INK)
    d.text((96, 194), '  boxes worth it"', font=font('bold', 54), fill=INK)
    d.line([(96, 290), (700, 290)], fill=MUTED, width=2)
    d.text((96, 318), 'MATH', font=font('black', 56), fill=AQUA)
    d.text((96, 382), '+$1.74', font=font('black', 150), fill=INK)
    d.text((100, 556), 'on a $151 box', font=font('bold', 50), fill=INK2)
    return img

def d_ten_million():
    img = bg(YELLOW); hero(img, YELLOW, center=(900, 360))
    tag(img, (56, 44), 'the receipts', 'i opened 10 million packs')
    callout(img, (56, 196), '1 in 70', 'boxes pay for themselves', AQUA, fb=170, fs=44)
    callout(img, (56, 470), '49¢', 'per $1, in cash', RED, fb=120, fs=40)
    return img

def d_question():
    """the pack and the question, nothing else: for the version where the title does the talking."""
    img = bg(BLUE, pool=(640, 380)); hero(img, BLUE, center=(600, 360), rot=-6, scale=1.0)
    d = ImageDraw.Draw(img); f = font('black', 96)
    for text, y, col in (('is opening', 40, INK), ('boosters +EV?', 590, INK)):
        tw = d.textbbox((0, 0), text, font=f)[2]
        glow = Image.new('RGBA', img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.text(((W - tw) / 2, y), text, font=f, fill=(0, 0, 0, 200)); img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16)))
        ImageDraw.Draw(img).text(((W - tw) / 2, y), text, font=f, fill=col)
    return img

DESIGNS = {'six_cents': d_six_cents, 'ev': d_ev, 'myth': d_myth, 'ten_million': d_ten_million, 'question': d_question}

if __name__ == '__main__':
    for name, fn in DESIGNS.items():
        o = os.path.join(OUT, f'{name}.png'); fn().convert('RGB').save(o, optimize=True); print('  ', o)
