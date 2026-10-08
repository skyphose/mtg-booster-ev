"""
what if god packs had always existed? the 2027 rule (1 in 1,000 packs is all rares and mythics) bolted onto every
main booster from 2016 to 2026: draft, set and play boosters, priced at today's prices.

the god pack, the same for every set so they compare: 14 cards drawn from that set's own rare slot (whatever the
rare slot held: plain rares, showcase, borderless), 2 of them foil. the real 2027 version swaps four of those for
booster fun, so on modern sets this is a bit conservative (reality fracture: see `fra_official_rule` below).

per set:
  gp_mean / gp_median / gp_p90   what a god pack would be worth today
  lift_pack / lift_box           what 1-in-1,000 adds to pack and box ev
  ratio_before / ratio_after     box ev / box price, without and with god packs
  p_cash_before / p_cash_after   chance one box pays for itself in cash, without and with god packs
  p_gp_in_box                    chance a box has at least one god pack

run ev_model.py first.  python3 godpack_history.py  -> results/godpack_history.csv, results/charts/11_godpacks_through_history.png
"""
import csv, os, random, statistics as st, math, zlib
import ev_model as M

random.seed(17)
RATE = 1 / 1000
GP_CARDS, GP_FOILS = 14, 2
N_BOXES, N_GP = 2000, 4000
SKIP = ('special_guest', 'the_list', 'source_material', 'transformers', 'foil_transformers', 'prototype_praetor', 'borderless_reprint')
summary = {r['product']: r for r in csv.DictReader(open(os.path.join(M.OUT, 'set_summary.csv')))}

def rare_slot(code):
    """the set's rare slot as a weighted list of printings: every rare/mythic-only sheet a pack pulls from (not the
    list / special guests / fixed pairs), weighted by how often packs pull it."""
    x = M.BY_CODE[code]; tw = sum(b['weight'] for b in x['boosters']); w = {}
    for b in x['boosters']:
        for s, n in b['sheets'].items():
            sh = x['sheets'][s]
            if sh.get('fixed') or s.startswith(SKIP) or s.startswith('pair_'): continue
            cards = sh['cards']; sw = sum(cards.values())
            rm = sum(v for k, v in cards.items() if M.card_price(k)[2] in ('r', 'm'))
            if rm / sw < 0.9 or any(k.endswith((':foil', ':etched')) for k in cards): continue
            for k, v in cards.items(): w[k] = w.get(k, 0) + b['weight'] / tw * n * v / sw
    keys = list(w); return keys, [w[k] for k in keys]

def foil_price(key):
    p, found, r, name = M.card_price(key + ':foil')
    return p

def god_pack(keys, ws, rng):
    picks = rng.choices(keys, weights=ws, k=GP_CARDS)
    return [foil_price(k) for k in picks[:GP_FOILS]] + [M.card_price(k)[0] for k in picks[GP_FOILS:]]

import sys
CHART_ONLY = '--chart-only' in sys.argv   # redraw chart 11 from results/godpack_history.csv without re-simulating
rows = []
for (s, name, year, code, kind, packs, msrp) in ([] if CHART_ONLY else M.PRODUCTS):
    if kind == 'collector' or code not in M.BY_CODE: continue
    r = summary[code]; price = float(r['box_price_sales_median']) if r['box_price_sales_median'] else None
    keys, ws = rare_slot(code); tot = sum(ws)
    mean_nf = sum(w * M.card_price(k)[0] for k, w in zip(keys, ws)) / tot
    mean_f = sum(w * foil_price(k) for k, w in zip(keys, ws)) / tot
    gp_mean = (GP_CARDS - GP_FOILS) * mean_nf + GP_FOILS * mean_f
    rng = random.Random(zlib.crc32(code.encode()))
    gps = [god_pack(keys, ws, rng) for _ in range(N_GP)]
    gp_vals = sorted(sum(g) for g in gps); gp_cash = [sum(M.realizable(v) for v in g) for g in gps]
    pack_ev = float(r['ev_pack']); lift_pack = RATE * (gp_mean - pack_ev)
    top_key = max(keys, key=lambda k: foil_price(k)); top = (M.card_price(top_key)[3], round(foil_price(top_key), 2))
    row = dict(set=s, name=name, year=year, product=code, kind=kind, packs=packs,
               rare_slot_avg=round(mean_nf, 2), gp_mean=round(gp_mean, 2), gp_median=round(st.median(gp_vals), 2),
               gp_p10=round(gp_vals[int(.1 * N_GP)], 2), gp_p90=round(gp_vals[int(.9 * N_GP)], 2), gp_p99=round(gp_vals[int(.99 * N_GP)], 2),
               pack_ev=pack_ev, gp_vs_pack_x=round(gp_mean / pack_ev, 1), lift_pack=round(lift_pack, 4), lift_box=round(lift_pack * packs, 2),
               p_gp_in_box=round(1 - (1 - RATE) ** packs, 4), top_foil_card=f'{top[0]} (${top[1]:,.0f} foil)',
               box_price=price or '', ratio_before='', ratio_after='', ratio_after_1in100='', p_cash_before='', p_cash_after='')
    if price:
        ev_box = float(r['ev_box'])
        row['ratio_before'] = round(ev_box / price, 3); row['ratio_after'] = round((ev_box + lift_pack * packs) / price, 3)
        row['ratio_after_1in100'] = round((ev_box + 10 * lift_pack * packs) / price, 3)  # ten times as common
        # cash: simulate boxes, then let each pack independently be a god pack at 1 in 1,000
        sim = M.simulate_boxes(code, packs, n_boxes=N_BOXES)
        pack_cash = float(r['real_box']) / packs
        before = sum(1 for _, rv, _ in sim if rv > price) / len(sim)
        hits = 0; trials = 0
        for _, rv, _ in sim:
            for _ in range(4):  # 4 god-pack draws per simulated box
                k = sum(1 for _ in range(packs) if rng.random() < RATE)
                v = rv + sum(rng.choice(gp_cash) - pack_cash for _ in range(k))
                hits += v > price; trials += 1
        row['p_cash_before'] = round(before, 4); row['p_cash_after'] = round(hits / trials, 4)
    rows.append(row); print(f"{code:12} gp ${gp_mean:7.2f} (median {row['gp_median']:7.2f})  lift/box ${row['lift_box']:5.2f}  ratio {row['ratio_before']} -> {row['ratio_after']}  cash {row['p_cash_before']} -> {row['p_cash_after']}")

if CHART_ONLY:
    def num(v):
        try: return float(v) if '.' in v else int(v)
        except ValueError: return v
    rows = [{k: num(v) for k, v in r.items()} for r in csv.DictReader(open(os.path.join(M.OUT, 'godpack_history.csv')))]
# reality fracture under the real 2027 rule, for scale (godpack_model.py)
gp_csv = {a: b for a, b in csv.reader(open(os.path.join(M.OUT, 'godpack.csv')))}
fra_official_rule = float(gp_csv['Booster Pack GOD PACK value (10 R/M + 2 BF + 2 foil BF, no celeb card)'])
fra_simple = next(r['gp_mean'] for r in rows if r['product'] == 'fra-play')
print(f'reality fracture: simple rule ${fra_simple:.2f}, official 2027 rule ${fra_official_rule:.2f}')

pr = [r for r in rows if r['ratio_before'] != '']
flip = lambda key: [r['product'] for r in pr if (r['ratio_before'] < 1) != (r[key] < 1)]
print('boxes that cross 1.0 on paper: at 1 in 1,000', flip('ratio_after'), ' at 1 in 100', flip('ratio_after_1in100'))
print('max lift per box', max((r['lift_box'], r['product']) for r in rows), ' median', st.median(r['lift_box'] for r in rows))
print('max cash-odds change (pct points)', max((round(100 * (r['p_cash_after'] - r['p_cash_before']), 2), r['product']) for r in pr))

if not CHART_ONLY:
    with open(os.path.join(M.OUT, 'godpack_history.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# ----------------------------------------------------------------------------- chart 11
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
SURF, INK, INK2, MUTED, GRID = '#1a1a19', '#ffffff', '#c3c2b7', '#898781', '#2c2c2a'
BLUE, AQUA, YELLOW = '#3987e5', '#199e70', '#c98500'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.edgecolor': GRID, 'font.size': 16, 'axes.titlesize': 24, 'axes.titleweight': 'bold'})
order = sorted(rows, key=lambda r: (r['year'], r['product']))
f, (a1, a2) = plt.subplots(2, 1, figsize=(19.2, 10.8), dpi=100, gridspec_kw={'height_ratios': [1.4, 1]}, sharex=True)
xs = range(len(order)); cols = [{'draft': MUTED, 'set': AQUA, 'play': BLUE}[r['kind']] for r in order]
a1.vlines(xs, [r['gp_p10'] for r in order], [r['gp_p90'] for r in order], color=cols, lw=3, alpha=0.6)
a1.scatter(xs, [r['gp_mean'] for r in order], c=cols, s=70, zorder=3)
a1.set_yscale('log'); a1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'${v:,.0f}')); a1.grid(True, color=GRID, axis='y')
a1.set_title('If every set since 2016 had god packs: what one would be worth today')
a1.set_ylabel('god pack value (dot = average, bar = 10th-90th pct)')
seen = set(); picks = []
for r_ in sorted(order, key=lambda r: -r['gp_mean']):
    if r_['name'] not in seen: seen.add(r_['name']); picks.append(r_)
    if len(picks) == 3: break
for j, r_ in enumerate(picks):  # label the top three sets once each, staggered so they don't collide
    i = order.index(r_); a1.annotate(f"{r_['name']}: \\${r_['gp_mean']:.0f}", (i, r_['gp_mean']), xytext=(-150 + 40 * j, 34 + 22 * j), textcoords='offset points',
                                     fontsize=13, color=INK, arrowprops=dict(arrowstyle='-', color=INK2, lw=1))
a2.bar(xs, [r['lift_box'] for r in order], color=cols)
a2.set_ylabel('added to box ev ($)'); a2.set_yticks([0, 0.5, 1, 1.5, 2]); a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'${v:.2f}')); a2.grid(True, color=GRID, axis='y')
a2.set_title('...and what that adds to a whole box', fontsize=20)
yr_first = {}
for i, r_ in enumerate(order): yr_first.setdefault(r_['year'], i)
a2.set_xticks(list(yr_first.values())); a2.set_xticklabels(list(yr_first.keys()))
for lab, c in (('draft booster', MUTED), ('set booster', AQUA), ('play booster', BLUE)): a1.scatter([], [], c=c, s=70, label=lab)
a1.legend(loc='upper left', fontsize=14, frameon=False)
f.text(0.01, 0.01, 'God pack = 14 cards from the set\'s own rare slot, 2 foil, at 1 in 1,000 packs. Today\'s prices (Scryfall bulk, 2026-10-05). Draft/set/play boosters only.', color=MUTED, fontsize=13)
f.tight_layout(rect=(0, 0.03, 1, 1)); f.savefig(os.path.join(M.OUT, 'charts', '11_godpacks_through_history.png')); print('chart 11 written')
