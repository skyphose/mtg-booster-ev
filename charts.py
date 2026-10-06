"""b-roll charts for the video. 1920x1080, dark. store figures are rounded UP to the nearest $10 and anonymous on purpose."""
import csv, os, math, statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'results'); CH = os.path.join(OUT, 'charts'); os.makedirs(CH, exist_ok=True)
# palette (dark mode steps)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = '#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'
SURF, INK, INK2, MUTED, GRID, BASE = '#1a1a19', '#ffffff', '#c3c2b7', '#898781', '#2c2c2a', '#383835'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'text.color': INK, 'font.family': 'DejaVu Sans', 'font.size': 16, 'axes.titlesize': 24, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 1, 'axes.axisbelow': True, 'legend.frameon': False})
usd = FuncFormatter(lambda v, _: f'${v:,.0f}')
def fig(w=19.2, h=10.8): return plt.subplots(figsize=(w, h), dpi=100)
def save(f, name, sub=None):
    if sub: f.text(0.01, 0.015, sub, color=MUTED, fontsize=13)
    f.tight_layout(rect=(0, 0.03, 1, 1)); f.savefig(os.path.join(CH, name), facecolor=SURF); plt.close(f)

rows = list(csv.DictReader(open(os.path.join(OUT, 'set_summary.csv'))))
def fl(x): return float(x) if x not in ('', None) else None

# ---------------------------------------------------------------- 1. Play booster boxes: EV vs what boxes actually sell for
play = [r for r in rows if r['kind'] == 'play' and r['box_price_sales_median']]
play.sort(key=lambda r: (int(r['year']), r['set']))
f, ax = fig()
labels = [f"{r['name']} ('{r['year'][2:]})" for r in play]
y = range(len(play))
ax.barh(y, [fl(r['ev_box']) for r in play], color=BLUE, height=0.62, label='EV of the cards at market prices')
ax.barh(y, [fl(r['real_box']) for r in play], color=AQUA, height=0.62, label='What you could actually cash out (bulk = $0, $1-5 cards at 50%, $5+ at 70%)')
ax.scatter([fl(r['box_price_sales_median']) for r in play], list(y), color=YELLOW, s=160, zorder=5, marker='D', label='Box price: median of recent completed sales')
ax.set_yticks(list(y)); ax.set_yticklabels(labels); ax.invert_yaxis(); ax.xaxis.set_major_formatter(usd)
ax.set_title('Play Booster boxes 2024-26: cards "worth" more than the box - until you sell them')
ax.legend(loc='lower right', fontsize=14)
save(f, '01_play_boxes_ev_vs_price.png', 'Model: official pack odds x TCGplayer market prices (Scryfall bulk, 2026-10-05). 4,000 simulated boxes per set. Box price = median of the 5 most recent completed TCGplayer sales.')

# ---------------------------------------------------------------- 2. Collector boxes
coll = [r for r in rows if r['kind'] == 'collector' and r['box_price_sales_median'] and int(r['year']) >= 2023]
coll.sort(key=lambda r: (int(r['year']), r['set']))
f, ax = fig()
labels = [f"{r['name']} ('{r['year'][2:]})" for r in coll]; y = range(len(coll))
ax.barh(y, [fl(r['ev_box']) for r in coll], color=BLUE, height=0.62, label='EV of the cards at market prices')
ax.barh(y, [fl(r['real_box']) for r in coll], color=AQUA, height=0.62, label='Cash-out value')
ax.scatter([fl(r['box_price_sales_median']) for r in coll], list(y), color=YELLOW, s=160, zorder=5, marker='D', label='Box price (recent sales)')
ax.set_yticks(list(y)); ax.set_yticklabels(labels); ax.invert_yaxis(); ax.xaxis.set_major_formatter(usd)
ax.set_title('Collector Booster boxes: the box costs more than the cards inside, almost every time')
ax.legend(loc='lower right', fontsize=14)
save(f, '02_collector_boxes_ev_vs_price.png', 'Same method. Collector boxes carry a sealed premium: buyers pay for the lottery ticket, not the expected contents.')

# ---------------------------------------------------------------- 3. Ten years: EV / box price ratio by product
pts = [r for r in rows if r['ev_to_price']]
f, ax = fig()
kinds = [('draft', 'Draft booster box', BLUE), ('set', 'Set booster box', ORANGE), ('play', 'Play booster box', AQUA), ('collector', 'Collector box', MAGENTA)]
import random; random.seed(3)
for k, lab, col in kinds:
    xs = [int(r['year']) + random.uniform(-0.18, 0.18) for r in pts if r['kind'] == k]
    ys = [fl(r['ev_to_price']) for r in pts if r['kind'] == k]
    ax.scatter(xs, ys, color=col, s=110, label=lab, zorder=4)
ax.axhline(1.0, color=INK2, lw=2, ls='--'); ax.text(2015.6, 1.03, 'break-even (cards at market = box price)', color=INK2, fontsize=14)
ax.set_ylim(0, 1.9); ax.set_xlim(2015.5, 2026.6); ax.set_xticks(range(2016, 2027))
ax.set_ylabel('EV of cards at market  ÷  box price (recent sales)')
ax.set_title('Ten years of boxes: Play Boosters are the only product reliably above water - on paper')
ax.legend(loc='upper left', fontsize=14, ncol=4)
save(f, '03_ten_years_ev_ratio.png', '99 products, 2016-2026. Older boxes are priced today as aged sealed, so their ratio reflects the collector premium on the box, not the cards.')

# ---------------------------------------------------------------- 4. Probability of beating the price (market vs cash-out)
f, ax = fig()
sel = [r for r in rows if r['kind'] in ('play',) and r['p_box_beats_price']]
sel.sort(key=lambda r: (int(r['year']), r['set']))
labels = [f"{r['name']} ('{r['year'][2:]})" for r in sel]; y = range(len(sel))
ax.barh(y, [100 * fl(r['p_box_beats_price']) for r in sel], color=BLUE, height=0.38, align='edge', label='P(box beats its price) - cards valued at market')
ax.barh([v - 0.38 for v in y], [100 * fl(r['p_box_beats_price_realizable']) for r in sel], color=AQUA, height=0.38, align='edge', label='P(box beats its price) - cash-out value')
ax.set_yticks(list(y)); ax.set_yticklabels(labels); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
ax.set_title('Odds a single Play Booster box pays for itself')
ax.legend(loc='lower right', fontsize=14)
save(f, '04_p_box_beats_price.png', '4,000 simulated boxes per set. "Cash-out" = bulk at $0, $1-5 cards at 50% of market, $5+ at 70%.')

# ---------------------------------------------------------------- 5. God pack: what it adds, and the odds
gp = {r[0]: r[1] for r in csv.reader(open(os.path.join(OUT, 'godpack.csv')))}
f, (a1, a2) = plt.subplots(1, 2, figsize=(19.2, 10.8), dpi=100, gridspec_kw={'width_ratios': [1, 1.4]})
vals = [('Normal\nBooster Pack', fl(gp['Reality Fracture Play Booster EV (market, today)']), BLUE),
        ('Booster\ngod pack', fl(gp['Booster Pack GOD PACK value (10 R/M + 2 BF + 2 foil BF, no celeb card)']), YELLOW),
        ('Collector\ngod pack', fl(gp['Collector GOD PACK value (foil land + 3 foil R/M + 3 BF + 5 foil BF, no celeb)']), MAGENTA),
        ('Normal\nCollector Booster', fl(gp['Reality Fracture Collector Booster EV (market, today)']), VIOLET)]
a1.bar(range(4), [v[1] for v in vals], color=[v[2] for v in vals], width=0.6)
for i, v in enumerate(vals): a1.text(i, v[1] + 2, f'${v[1]:.0f}', ha='center', fontsize=20, fontweight='bold')
a1.set_xticks(range(4)); a1.set_xticklabels([v[0] for v in vals], fontsize=15); a1.yaxis.set_major_formatter(usd)
a1.set_title('What a god pack is worth')
packs = list(range(0, 2001, 10))
a2.plot(packs, [100 * (1 - (1 - 1 / 1000) ** p) for p in packs], color=YELLOW, lw=3, label='Booster packs (1 in 1,000)')
a2.plot(packs, [100 * (1 - (1 - 1 / 300) ** p) for p in packs], color=MAGENTA, lw=3, label='Collector boosters (1 in 300)')
a2.axhline(50, color=INK2, ls='--', lw=1.5)
for p, lab, yy in [(30, '1 box', 95), (180, '1 case', 88), (693, '23 boxes\n($3,800 MSRP)', 58)]:
    a2.axvline(p, color=GRID, lw=1); a2.text(p + 8, yy, lab, color=INK2, fontsize=13)
a2.set_xlabel('Packs opened'); a2.set_ylabel('Chance of at least one god pack'); a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
a2.set_title('How many packs for a coin-flip at one?'); a2.legend(loc='lower right', fontsize=14); a2.set_ylim(0, 100)
save(f, '05_godpack_value_and_odds.png', f"God pack values use Reality Fracture sheet averages (3 days post-release, so generous). Celebration card valued at $0. Per-pack EV lift: ${fl(gp['EV lift per Booster Pack from god packs ($)']):.2f} Booster / ${fl(gp['EV lift per Collector Booster from god packs ($)']):.2f} Collector.")

# ---------------------------------------------------------------- 6. Foil change break-even
fr = list(csv.DictReader(open(os.path.join(OUT, 'foil_scenarios.csv'))))
f, ax = fig()
xs = [100 * fl(r['p_foil_rm_new']) for r in fr]; ys = [fl(r['delta_per_box']) for r in fr]
ax.plot(xs, ys, color=BLUE, lw=3, marker='o', ms=10)
ax.axhline(0, color=INK2, ls='--', lw=1.5)
be = fl(gp['break-even new foil R/M rate so pack EV is unchanged (%)']); today = fl(gp['today: P(foil rare or mythic in a pack) (%)'])
ax.axvline(today, color=ORANGE, lw=2); ax.text(today + 0.3, max(ys) * 0.9, f'today: foil rare/mythic in {today:.1f}% of packs\n(1 in {100/today:.0f})', color=ORANGE, fontsize=14)
ax.axvline(be, color=AQUA, lw=2); ax.text(be + 0.3, max(ys) * 0.55, f'break-even: {be:.1f}% (1 in {100/be:.1f})\nif Wizards sets the new rate here, pack EV is unchanged', color=AQUA, fontsize=14)
ax.set_xlabel('New chance of a foil rare/mythic in a Booster Pack (%)'); ax.set_ylabel('Change in box EV vs today (30 packs)'); ax.yaxis.set_major_formatter(usd)
ax.set_title('The foil change: what foil-rare rate pays back the $0.33/pack of lost foil commons?')
save(f, '06_foil_change_breakeven.png', 'Wizards has not published the new foil rare/mythic rate. Today foil commons+uncommons are 83% of the foil slot. Modelled on Reality Fracture.')

# ---------------------------------------------------------------- 7. Collector shrink
f, ax = fig(19.2, 10.8)
cats = ['Cards per Collector Booster', 'MSRP per card', 'EV removed per pack', 'God pack EV added per pack']
before = [15, 26.99 / 15, 0, 0]; after = [12, 26.99 / 12, -fl(gp['EV removed per Collector Booster (2 foil C + 1 foil U) ($)']), fl(gp['EV lift per Collector Booster from god packs ($)'])]
import numpy as np
x = np.arange(2);
ax.bar(x - 0.2, [before[0], after[0]], width=0.38, color=[VIOLET, VIOLET])
ax.set_xticks(x - 0.2); ax.set_xticklabels(['2026: 15 cards', '2027: 12 cards'])
for i, v in enumerate([before[0], after[0]]): ax.text(x[i] - 0.2, v + 0.2, f'{v} cards  ·  ${26.99/v:.2f} per card at MSRP', ha='center', fontsize=18, fontweight='bold')
ax.set_ylim(0, 18); ax.set_ylabel('Cards in a Collector Booster')
ax.set_title('Collector Boosters: 3 fewer cards, same $26.99 - price per card up 25%')
ax.text(0.98, 0.9, f"EV removed (2 foil commons + 1 foil uncommon): -${-after[2]:.2f}/pack\nGod pack EV added (1 in 300): +${after[3]:.2f}/pack\nNet: ${after[3]+after[2]:+.2f}/pack", transform=ax.transAxes, ha='right', va='top', fontsize=18, color=INK2, bbox=dict(facecolor='#232322', edgecolor=BASE))
save(f, '07_collector_shrink.png', 'Card values from Reality Fracture Collector Booster sheets at current market prices.')

# ---------------------------------------------------------------- 8. Store economics (anonymized, rounded UP to nearest $10)
def up10(v): return math.ceil(v / 10) * 10
store = [
  ('Play Booster display (30)', 100, 164.70, 151, 70),
  ('Collector Booster display (12)', 210, 323.88, 457, None),
  ('Commander deck', 40, 49.99, None, None),
  ('Bundle', 40, 57.99, None, None),
  ('Prerelease pack', 30, 35.0, None, None),
]
f, ax = fig()
y = np.arange(len(store)); h = 0.26
ax.barh(y + h, [s[1] for s in store], height=h, color=ORANGE, label='What a store pays its distributor (rounded up to $10)')
ax.barh(y, [s[2] for s in store], height=h, color=BLUE, label='MSRP (prerelease: typical $30-35 shelf)')
ax.barh(y - h, [s[3] or 0 for s in store], height=h, color=YELLOW, label='What the box actually sells for online (recent sales)')
for i, s in enumerate(store):
    ax.text(s[1] + 3, i + h, f'~${s[1]}', va='center', fontsize=14); ax.text(s[2] + 3, i, f'${s[2]:.2f}', va='center', fontsize=14)
    if s[3]: ax.text(s[3] + 3, i - h, f'${s[3]}', va='center', fontsize=14)
ax.set_yticks(y); ax.set_yticklabels([s[0] for s in store]); ax.invert_yaxis(); ax.xaxis.set_major_formatter(usd)
ax.set_title('One store\'s launch order: distributor cost vs MSRP vs online price')
ax.legend(loc='lower right', fontsize=14)
save(f, '08_store_economics.png', 'Distributor costs rounded up to the nearest $10; launch promo (free displays with case buys) cuts the effective Play display cost to roughly \\$' + str(70) + '. Online prices: median of recent completed TCGplayer sales.')

# ---------------------------------------------------------------- 9. Box value distribution (fra play box)
sim = [fl(r['box_value']) for r in csv.DictReader(open(os.path.join(OUT, 'box_sim.csv'))) if r['product'] == 'fra-play']
simr = [fl(r['realizable']) for r in csv.DictReader(open(os.path.join(OUT, 'box_sim.csv'))) if r['product'] == 'fra-play']
f, ax = fig()
ax.hist(sim, bins=40, color=BLUE, alpha=0.9, label='Cards at market prices')
ax.hist(simr, bins=40, color=AQUA, alpha=0.9, label='Cash-out value')
ax.axvline(151, color=YELLOW, lw=3); ax.text(153, ax.get_ylim()[1] * 0.9, 'box price $151\n(recent sales)', color=YELLOW, fontsize=15)
ax.axvline(164.70, color=INK2, lw=2, ls='--'); ax.text(166, ax.get_ylim()[1] * 0.75, 'MSRP $164.70', color=INK2, fontsize=14)
ax.set_xlabel('Value of one Reality Fracture Play Booster box (30 packs)'); ax.set_ylabel('Simulated boxes'); ax.xaxis.set_major_formatter(usd)
ax.set_title('One box, 400 simulations: on paper 96% beat the price - in cash, under 1% do')
ax.legend(loc='upper right', fontsize=14)
save(f, '09_box_distribution_fra.png', 'Monte Carlo of 30-pack boxes using Reality Fracture sheet odds and 2026-10-05 prices.')
print('charts written:', sorted(os.listdir(CH)))

# ---------------------------------------------------------------- 10. Where the "EV" sits: cards vs dollars by price tier (Reality Fracture box)
plt.rcParams['text.usetex'] = False
tiers = [('under \\$1', 396.0, 96.6), ('\\$1-5', 18.2, 37.2), ('\\$5-20', 4.8, 45.3), ('\\$20+', 0.9, 28.0)]
f, (a1, a2) = plt.subplots(1, 2, figsize=(19.2, 10.8), dpi=100)
cols = [MUTED, BLUE, AQUA, YELLOW]
def stacked(ax, idx, title, fmt, yfmt):
    bottom = 0; mids = []
    for (name, c, v), col in zip(tiers, cols):
        val = (c, v)[idx]
        ax.bar(0, val, bottom=bottom, color=col, width=0.5, edgecolor=SURF, linewidth=2)
        mids.append((bottom + val / 2, f'{name}: {fmt(val)}', col)); bottom += val
    # spread labels so none overlap (min gap 6% of total)
    gap = bottom * 0.06; ys = [m[0] for m in mids]
    for i in range(1, len(ys)):
        if ys[i] - ys[i-1] < gap: ys[i] = ys[i-1] + gap
    for (m, lab, col), yy in zip(mids, ys):
        ax.plot([0.26, 0.36], [m, yy], color=col, lw=1.5); ax.text(0.38, yy, lab, va='center', fontsize=17, color=INK)
    ax.set_xlim(-0.4, 1.3); ax.set_xticks([]); ax.set_title(title); ax.grid(False)
    ax.yaxis.set_major_formatter(FuncFormatter(yfmt))
stacked(a1, 0, 'Cards in the box (420)', lambda v: f'{v:.0f} cards', lambda v, _: f'{v:.0f}')
stacked(a2, 1, 'Dollars of "EV" in the box (\\$207 at market)', lambda v: f'\\${v:.0f}', lambda v, _: f'\\${v:.0f}')
save(f, '10_where_the_ev_sits.png', 'Reality Fracture Play Booster box, expected counts and values by price tier. 94% of the cards and 47% of the "EV" are in cards nobody will buy individually.')
print('chart 10 written')
