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
    ('ratio_127', '$1.27', 'of cards per $1 of box, on paper', BLUE),
    ('cash_46', '46¢', 'per $1 if you actually sell it all', AQUA),
    ('bulk_396', '396 of 420', 'cards in a box are under a dollar', MUTED),
    ('hours', '~5 hrs → ~$48', 'sorting, listing, shipping. under $10/hr', YELLOW),
    ('one_in_100', '~1 in 100', 'boxes pay for themselves in cash', AQUA),
    ('gp_63', '$63', 'average god pack (reality fracture prices)', YELLOW),
    ('gp_50', '$50', 'the median god pack. half are worth less', YELLOW),
    ('gp_23', '23 boxes', '~$3,800 at msrp for a coin flip at one', RED),
    ('shrink', '15 → 12', 'cards per collector booster, same $26.99', MAGENTA),
    ('net_80', '−$0.80', 'net change per collector booster', RED),
    ('foil_85', '1 in 8.5', 'foil-rare rate that breaks even (today: 1 in 13)', BLUE),
    ('verdict', 'singles for the deck.', 'packs for the night.', INK),
    ('wilcoxon', 'p ≈ 0.0002', 'play boosters above 1 at market, 14 of 16 sets', BLUE),
    ('coin_flip', '15 of 31', 'old draft boxes above the line: a coin flip', MUTED),
]
def callouts():
    for key, big, small, col in CALLOUTS:
        img = blank(); d = ImageDraw.Draw(img)
        fb = font('black', 110 if len(big) < 12 else 76); fs = font('med', 34)
        bw, bh = tw(d, big, fb); sw, sh = tw(d, small, fs)
        w = max(bw, sw) + 96; x1 = W - 80; x0 = x1 - w; y0 = 400; y1 = y0 + bh + sh + 120
        plate(img, (x0, y0, x1, y1), alpha=215)
        d.rectangle((x0, y0, x0 + 10, y1), fill=col)
        d.text((x0 + 48, y0 + 30), big, font=fb, fill=col if col != INK else INK)
        d.text((x0 + 48, y0 + 50 + bh + 18), small, font=fs, fill=INK2)
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

# ----------------------------------------------------------------------------- thumbnails
def thumbs():
    for key, big, col, sub in [('a', '6¢', BLUE, 'what a god pack is worth to you'), ('b', '46¢', AQUA, 'per dollar. every box. ten years.')]:
        img = Image.new('RGBA', (1280, 720), SURF + (255,)); d = ImageDraw.Draw(img)
        d.text((70, 60), 'GOD PACKS', font=font('black', 120), fill=INK)
        d.text((70, 200), big, font=font('black', 330), fill=col)
        d.text((74, 600), sub, font=font('bold', 46), fill=INK2)
        d.rectangle((70, 40, 190, 48), fill=YELLOW)
        img.convert('RGB').save(os.path.join(OUT, f'thumb_{key}.png')); print('   thumb_' + key + '.png  (leave the right half for your face)')

if __name__ == '__main__':
    card_title(); card_end(); tags(); callouts(); lower(); badge(); thumbs()
