"""
on-screen graphics for the edit. everything is 1920x1080 png; overlays have transparency.

    python3 edit/graphics.py        # writes edit/gfx/*.png

kinds:
  card_*      full-frame cards (title, end)
  tag_*       chapter tags, top-left, with a translucent plate
  callout_*   big number + one line, right third of the frame (keeps clear of a centered face)
  lower_*     lower third
  badge_*     small persistent corner badge
  thumb_*     1280x720 thumbnail drafts
  backdrop    what goes behind you once the black background is keyed out
  pip_fade    alpha ramp that fades your cut-out's torso when you shrink into a corner
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'gfx'); os.makedirs(OUT, exist_ok=True)
FONTS = os.path.join(HERE, 'fonts')
def font(weight, size):
    name = {'black': 'Inter-Black.otf', 'bold': 'Inter-Bold.otf', 'semi': 'Inter-SemiBold.otf', 'med': 'Inter-Medium.otf', 'reg': 'Inter-Regular.otf'}[weight]
    for d in (FONTS, '/usr/share/fonts/opentype/inter'):
        p = os.path.join(d, name)
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)

W, H = 1920, 1080
SURF = (26, 26, 25); INK = (255, 255, 255); INK2 = (195, 194, 183); MUTED = (137, 135, 129)
BLUE = (57, 135, 229); AQUA = (25, 158, 112); YELLOW = (201, 133, 0); MAGENTA = (213, 81, 129); RED = (230, 103, 103)

def save(img, name): img.save(os.path.join(OUT, name)); print('  ', name)
def blank(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))
def plate(img, box, alpha=200, radius=18):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=SURF + (alpha,))
    shadow = layer.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow); img.alpha_composite(layer)
def tw(d, text, f): b = d.textbbox((0, 0), text, font=f); return b[2] - b[0], b[3] - b[1]

# ----------------------------------------------------------------------------- behind the keyed-out talking head
def backdrop(cx=960):
    import numpy as np
    y, x = np.mgrid[0:H, 0:W].astype(float)
    r = np.sqrt(((x - cx) / 900) ** 2 + ((y - 600) / 620) ** 2)          # soft pool of light behind the head
    glow = np.clip(1 - r, 0, 1) ** 1.6
    vig = np.clip(r - 0.9, 0, 1) * 0.6                                      # darker corners
    base = np.array(SURF, float); lift = np.array((44, 46, 50), float) - base
    img = base + glow[..., None] * lift - vig[..., None] * base * 0.45
    grid = ((x % 96 < 1.2) | (y % 96 < 1.2)) * (0.35 + 0.65 * glow)         # faint chart-paper grid, fades out toward the edges
    img = img + grid[..., None] * np.array((7, 7, 7)) * (1 - np.clip(r, 0, 1))[..., None]
    img = np.clip(img + np.random.default_rng(0).normal(0, 0.6, img.shape), 0, 255).astype('uint8')   # dither against banding
    save(Image.fromarray(img, 'RGB'), 'backdrop.png')

def pip_fade(w=330, h=300, start=0.62):
    img = Image.new('L', (w, h), 255); d = ImageDraw.Draw(img)
    for row in range(int(h * start), h):
        d.line([(0, row), (w, row)], fill=int(255 * (1 - (row - h * start) / (h * (1 - start))) ** 1.5))
    save(img, 'pip_fade.png')

# ----------------------------------------------------------------------------- full-frame cards
def card_title():
    img = Image.new('RGBA', (W, H), SURF + (255,)); d = ImageDraw.Draw(img)
    d.text((140, 330), 'is opening boosters', font=font('black', 120), fill=INK)
    d.text((140, 470), '+EV?', font=font('black', 220), fill=BLUE)
    d.text((140, 760), 'ten years of boxes, and what god packs change', font=font('med', 48), fill=INK2)
    d.rectangle((140, 300, 260, 308), fill=YELLOW)
    save(img, 'card_title.png')

def card_end():
    img = Image.new('RGBA', (W, H), SURF + (255,)); d = ImageDraw.Draw(img)
    d.text((140, 300), 'i have the receipts.', font=font('black', 110), fill=INK)
    d.text((140, 470), 'model, data, charts, and verify.py:', font=font('med', 48), fill=INK2)
    d.text((140, 545), 'github.com/skyphose/mtg-booster-ev', font=font('bold', 72), fill=BLUE)
    d.text((140, 700), 'find a play booster box that returns $1 in cash? open an issue.', font=font('reg', 38), fill=MUTED)
    save(img, 'card_end.png')

# ----------------------------------------------------------------------------- chapter tags (top-left)
CHAPTERS = [
    ('p1', 'part 1', 'the number everyone gets wrong'),
    ('p2', 'part 2', 'where the money actually goes'),
    ('p3', 'part 3', 'ten years'),
    ('p4', 'part 4', "so what's a god pack worth"),
    ('p5', 'part 5', 'the part you skipped'),
    ('p6', 'part 6', 'from behind the counter'),
    # nerd-cut extras
    ('b1', 'part 1', 'how the model works'),
    ('b2', 'part 2', 'on paper, you win'),
    ('b3', 'part 3', 'the haircut, and the hours'),
    ('b4', 'part 4', 'ten years, with the caveats'),
    ('b5', 'part 5', 'pricing a god pack'),
    ('b6', 'part 6', 'the foil change is the real ev story'),
    ('b7', 'part 7', 'collector shrink, with the math'),
    ('b8', 'part 8', 'behind the counter'),
    ('h1', 'what if', 'god packs had always existed'),
]
def tags():
    for key, a, b in CHAPTERS:
        img = blank(); d = ImageDraw.Draw(img)
        fa, fb = font('semi', 28), font('bold', 44)
        w = max(tw(d, a, fa)[0], tw(d, b, fb)[0]) + 72
        plate(img, (60, 56, 60 + w, 56 + 130))
        d.rectangle((60, 56, 68, 186), fill=YELLOW)
        d.text((96, 74), a.upper(), font=fa, fill=YELLOW)
        d.text((96, 112), b, font=fb, fill=INK)
        save(img, f'tag_{key}.png')

# ----------------------------------------------------------------------------- callouts (right third)
CALLOUTS = [
    ('six_cents', 'six cents', 'what a god pack adds to a $5.49 pack', BLUE),
    ('ratio_127', '$1.35', 'of cards per $1 of box, on paper', BLUE),
    ('cash_46', '49¢', 'per $1 if you actually sell it all', AQUA),
    ('bulk_396', '395 of 420', 'cards in a box are under a dollar', MUTED),
    ('hours', '~5 hrs → ~$50', 'sorting, listing, shipping. about $10/hr', YELLOW),
    ('one_in_100', '~1 in 70', 'boxes pay for themselves in cash (median set)', AQUA),
    ('gp_63', '$65', 'average god pack (reality fracture prices)', YELLOW),
    ('gp_50', '$51', 'the median god pack. half are worth less', YELLOW),
    ('gp_23', '23 boxes', '~$3,800 at msrp for a coin flip at one', RED),
    ('shrink', '15 → 12', 'cards per collector booster, same $26.99', MAGENTA),
    ('net_80', '−$0.85', 'net change per collector booster', RED),
    ('foil_85', '1 in 8', 'foil-rare rate that breaks even (today: 1 in 12)', BLUE),
    ('verdict', 'singles for the deck.', 'packs for the night.', INK),
    ('wilcoxon', 'p ≈ 0.00005', 'play boosters above 1 at market, 15 of 16 sets', BLUE),
    ('gp_history', '~$2', 'the most a god pack would ever have added to a box', YELLOW),
    ('gp_flip', '0 of 62', 'boxes since 2016 that god packs would flip to a win', RED),
    ('cut_box', '−$12.83', 'what the cut takes out of a reality fracture collector box', MAGENTA),
    ('cut_cash', '3¢', 'what those three cards sell for, per pack', AQUA),
    ('coin_flip', '17 of 31', 'old draft boxes above the line: still a coin flip', MUTED),
]
def callouts():
    for key, big, small, col in CALLOUTS:
        img = blank(); d = ImageDraw.Draw(img)
        fb = font('black', 110 if len(big) < 12 else 76); fs = font('med', 34)
        bw, bh = tw(d, big, fb)
        lines, cur = [], ''   # wrap the small line so the plate stays clear of the face (max ~460px of text)
        for word in small.split():
            if cur and tw(d, cur + ' ' + word, fs)[0] > max(460, bw): lines.append(cur); cur = word
            else: cur = (cur + ' ' + word).strip()
        lines.append(cur); sw = max(tw(d, l, fs)[0] for l in lines); sh = 44 * len(lines) - 10
        w = max(bw, sw) + 96; x1 = W - 80; x0 = x1 - w; y0 = 400; y1 = y0 + bh + sh + 120
        plate(img, (x0, y0, x1, y1), alpha=215)
        d.rectangle((x0, y0, x0 + 10, y1), fill=col)
        d.text((x0 + 48, y0 + 30), big, font=fb, fill=col if col != INK else INK)
        for li, l in enumerate(lines): d.text((x0 + 48, y0 + 50 + bh + 18 + 44 * li), l, font=fs, fill=INK2)
        save(img, f'callout_{key}.png')

# ----------------------------------------------------------------------------- lower third, badge, source tag
def lower():
    img = blank(); d = ImageDraw.Draw(img)
    plate(img, (60, 860, 900, 1000), alpha=215)
    d.rectangle((60, 860, 70, 1000), fill=BLUE)
    d.text((100, 876), 'miguel', font=font('black', 56), fill=INK)
    d.text((100, 946), 'works at a game store · built the model', font=font('med', 30), fill=INK2)
    save(img, 'lower_name.png')

def badge():
    img = blank(); d = ImageDraw.Draw(img); f = font('semi', 26); t = 'github.com/skyphose/mtg-booster-ev'
    w, h = tw(d, t, f); plate(img, (W - w - 110, H - 136, W - 50, H - 86), alpha=190, radius=12)
    d.text((W - w - 80, H - 129), t, font=f, fill=INK2); save(img, 'badge_repo.png')
    img = blank(); d = ImageDraw.Draw(img); f = font('reg', 22); t = 'prices: tcgplayer market via scryfall, 5 oct 2026 · box prices: median of recent completed sales'
    w, h = tw(d, t, f); d.text((W - w - 60, H - 40), t, font=f, fill=MUTED); save(img, 'badge_source.png')


# ----------------------------------------------------------------------------- full-screen story cards (used as b-roll, so your face sits in the corner)
def card_myth():
    img = Image.new('RGBA', (W, H), SURF + (255,)); d = ImageDraw.Draw(img)
    d.text((140, 170), 'MYTH', font=font('black', 64), fill=RED)
    d.text((140, 250), '"god packs make boxes worth it"', font=font('bold', 76), fill=INK)
    d.rectangle((140, 470, 1780, 474), fill=GRID if 'GRID' in globals() else (44, 44, 42))
    d.text((140, 540), 'MATH', font=font('black', 64), fill=AQUA)
    d.text((140, 620), '+$1.74 of value on a $151 box', font=font('black', 96), fill=INK)
    d.text((140, 760), 'one god pack in 1,000 packs, averaged out', font=font('med', 40), fill=INK2)
    save(img, 'card_myth.png')

def card_receipts():
    img = Image.new('RGBA', (W, H), SURF + (255,)); d = ImageDraw.Draw(img)
    d.text((140, 150), 'RECEIPTS: I FOUND A BUG IN MY OWN MODEL', font=font('black', 56), fill=YELLOW)
    d.text((140, 260), 'double-faced cards were priced as bulk', font=font('bold', 60), fill=INK)
    rows = [('median play box, on paper', '1.27×', '1.35×'), ('median play box, in cash', '46¢', '49¢'), ('median collector box', '0.58×', '0.62×')]
    y = 420
    for lab, a, b in rows:
        d.text((140, y), lab, font=font('med', 44), fill=INK2)
        d.text((1150, y - 6), a, font=font('bold', 56), fill=MUTED); d.text((1400, y - 6), '→', font=font('bold', 56), fill=MUTED); d.text((1520, y - 6), b, font=font('black', 56), fill=BLUE)
        y += 110
    d.text((140, 800), 'conclusions: unchanged.', font=font('black', 72), fill=AQUA)
    save(img, 'card_receipts.png')

def card_recap():
    img = Image.new('RGBA', (W, H), SURF + (255,)); d = ImageDraw.Draw(img)
    d.text((140, 120), 'the whole video in three numbers', font=font('bold', 52), fill=INK2)
    cols = [('49¢', 'what a play box returns\nper $1, in cash', AQUA), ('6¢', 'what a god pack adds\nto each pack', YELLOW), ('−$12.83', 'what the 2027 cut takes\nfrom a collector box', MAGENTA)]
    for i, (big, small, c) in enumerate(cols):
        x = 140 + i * 560
        d.text((x, 340), big, font=font('black', 118), fill=c)
        d.multiline_text((x, 560), small.replace('\\n', '\n'), font=font('med', 40), fill=INK, spacing=12)
    d.text((140, 840), 'buy singles for the deck.', font=font('black', 64), fill=INK); d.text((140, 920), 'buy packs for the night.', font=font('black', 64), fill=INK2)
    save(img, 'card_recap.png')

# ----------------------------------------------------------------------------- thumbnails
def thumbs():
    for key, big, col, sub in [('a', '6¢', BLUE, 'what a god pack is worth to you'), ('b', '49¢', AQUA, 'per dollar, in cash. median play box.')]:
        img = Image.new('RGBA', (1280, 720), SURF + (255,)); d = ImageDraw.Draw(img)
        d.text((70, 60), 'GOD PACKS', font=font('black', 120), fill=INK)
        d.text((70, 200), big, font=font('black', 330), fill=col)
        d.text((74, 600), sub, font=font('bold', 46), fill=INK2)
        d.rectangle((70, 40, 190, 48), fill=YELLOW)
        img.convert('RGB').save(os.path.join(OUT, f'thumb_{key}.png')); print('   thumb_' + key + '.png  (leave the right half for your face)')

if __name__ == '__main__':
    card_title(); card_end(); card_myth(); card_receipts(); card_recap(); tags(); callouts(); lower(); badge(); thumbs(); backdrop(); pip_fade()
