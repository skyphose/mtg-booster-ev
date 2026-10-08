"""
open 8,000 packs of every product from the last ten years and see where you stand.

for each of the 99 products: crack 8,000 packs (one literal run, so there's a story: best pull, total haul) and
bootstrap 2,000 more 8,000-pack runs from a pool of simulated packs for the odds. pack price = that product's
recent box sale price / packs per box (today's sealed prices; old boxes are priced as collectibles).

  cost_8k / market_8k / cash_8k      what 8,000 packs cost, are worth at market, and sell for after the haircut
  breakeven_price_market / _cash     the pack price at which 8,000 packs break even on paper / in cash
  p_ahead_market / p_ahead_cash      chance a whole 8,000-pack run comes out ahead
  packs_to_95_market                 packs needed to be 95% sure you're ahead on paper (if it ever happens)
  best_pull                          the single best card in the literal 8,000-pack run

run ev_model.py first.  -> results/packs8000.csv, results/charts/13_8000_packs.png
"""
import csv, os, random, statistics as st, zlib
import numpy as np
import ev_model as M

N = 8000; POOL = 20000; BOOT = 2000
summary = {r['product']: r for r in csv.DictReader(open(os.path.join(M.OUT, 'set_summary.csv')))}

def pack_sampler(code, rng):
    x = M.BY_CODE[code]; configs = [(b['weight'], b['sheets']) for b in x['boosters']]; cw = [c[0] for c in configs]
    samp = {}
    for n, sh in x['sheets'].items():
        keys = list(sh['cards']); samp[n] = (keys, list(sh['cards'].values()), [M.card_price(k)[0] for k in keys], sh.get('fixed', False))
    def one():
        cfg = rng.choices(configs, weights=cw)[0][1]; mv = cv = 0.0; best = (0.0, '')
        for s, k in cfg.items():
            keys, w, vals, fixed = samp[s]
            idx = range(len(keys)) if fixed else rng.choices(range(len(keys)), weights=w, k=k)
            for i in idx:
                v = vals[i]; mv += v; cv += M.realizable(v)
                if v > best[0]: best = (v, keys[i])
        return mv, cv, best
    return one

rows = []
for (s, name, year, code, kind, packs, msrp) in M.PRODUCTS:
    if code not in M.BY_CODE: continue
    r = summary[code]; price = float(r['box_price_sales_median']) / packs if r['box_price_sales_median'] else None
    rng = random.Random(zlib.crc32(code.encode())); one = pack_sampler(code, rng)
    # the literal run: 8,000 packs, opened one at a time
    mv = cv = 0.0; best = (0.0, '')
    for _ in range(N):
        a, b, c = one(); mv += a; cv += b
        if c[0] > best[0]: best = c
    # a pool of packs to bootstrap whole runs from
    pool = np.array([one()[:2] for _ in range(POOL)])
    nprng = np.random.default_rng(zlib.crc32(code.encode()))
    idx = nprng.integers(0, POOL, size=(BOOT, N))
    runs_m = pool[idx, 0].sum(axis=1); runs_c = pool[idx, 1].sum(axis=1)
    mu_m, sd_m = pool[:, 0].mean(), pool[:, 0].std()
    row = dict(set=s, name=name, year=year, product=code, kind=kind, packs_per_box=packs,
               pack_price=round(price, 2) if price else '', ev_pack=round(mu_m, 2), cash_pack=round(pool[:, 1].mean(), 2),
               cost_8k=round(price * N, 0) if price else '', market_8k=round(mv, 0), cash_8k=round(cv, 0),
               net_market_8k=round(mv - price * N, 0) if price else '', net_cash_8k=round(cv - price * N, 0) if price else '',
               breakeven_price_market=round(mu_m, 2), breakeven_price_cash=round(pool[:, 1].mean(), 2),
               p_ahead_market=round(float((runs_m > price * N).mean()), 3) if price else '',
               p_ahead_cash=round(float((runs_c > price * N).mean()), 3) if price else '',
               packs_to_95_market='', best_pull=f"{M.card_price(best[1])[3]} (${best[0]:,.2f})")
    if price and mu_m > price:   # normal approx on the per-pack edge: n where the 5th percentile of the total clears the cost
        edge = mu_m - price; row['packs_to_95_market'] = int(np.ceil((1.645 * sd_m / edge) ** 2))
    rows.append(row)
    print(f"{code:15} pack ${row['pack_price']!s:>6}  ev ${row['ev_pack']:6.2f}  cash ${row['cash_pack']:5.2f}  8k: cost {row['cost_8k']!s:>8} market {row['market_8k']:>8.0f} cash {row['cash_8k']:>7.0f}  P(ahead) {row['p_ahead_market']}/{row['p_ahead_cash']}  best {row['best_pull']}")

with open(os.path.join(M.OUT, 'packs8000.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

priced = [r for r in rows if r['pack_price'] != '']
def tot(rs, k): return sum(r[k] for r in rs)
for label, rs in (('everything', priced), ('main boosters', [r for r in priced if r['kind'] != 'collector']), ('collector', [r for r in priced if r['kind'] == 'collector']),
                  ('play boosters', [r for r in priced if r['kind'] == 'play'])):
    c, m, k = tot(rs, 'cost_8k'), tot(rs, 'market_8k'), tot(rs, 'cash_8k')
    print(f"{label:14} {len(rs):3} products x 8,000 packs: cost ${c:,.0f}  market ${m:,.0f} ({m / c:.2f}x)  cash ${k:,.0f} ({k / c:.2f}x)  net cash ${k - c:,.0f}")
print('ahead in cash after 8,000 packs:', [r['product'] for r in priced if r['p_ahead_cash'] > 0.5] or 'none')
print('ahead on paper (>50%):', sum(r['p_ahead_market'] > 0.5 for r in priced), 'of', len(priced))

# ----------------------------------------------------------------------------- chart 13
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
SURF, INK, INK2, MUTED, GRID = '#1a1a19', '#ffffff', '#c3c2b7', '#898781', '#2c2c2a'
BLUE, AQUA, YELLOW, RED = '#3987e5', '#199e70', '#c98500', '#e66767'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.edgecolor': GRID, 'font.size': 15, 'axes.titlesize': 22, 'axes.titleweight': 'bold'})
main = sorted([r for r in priced if r['kind'] != 'collector'], key=lambda r: (r['year'], r['product']))
f, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
xs = np.arange(len(main))
ax.bar(xs, [r['pack_price'] for r in main], color=MUTED, alpha=0.55, label='what a pack costs (today\'s sealed price)')
ax.scatter(xs, [r['breakeven_price_market'] for r in main], color=BLUE, s=60, zorder=3, label='break-even price on paper (avg cards per pack)')
ax.scatter(xs, [r['breakeven_price_cash'] for r in main], color=AQUA, s=60, zorder=3, label='break-even price in cash')
ax.set_yscale('log'); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'${v:,.0f}' if v >= 1 else f'{v * 100:.0f}¢'))
yr = {}
for i, r in enumerate(main): yr.setdefault(r['year'], []).append(i)
ax.set_xticks([sum(v) / len(v) for v in yr.values()]); ax.set_xticklabels(list(yr.keys())); ax.grid(True, color=GRID, axis='y')  # label the middle of each year
ax.set_yticks([1, 2, 5, 10, 20]); ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ''))
ax.set_title('8,000 packs of every draft, set and play booster since 2016: the price you\'d have to pay to break even')
ax.legend(loc='upper right', fontsize=14, frameon=False)
f.text(0.01, 0.01, 'Grey bar above the green dot = losing money in cash. 8,000 packs per product, today\'s prices (Scryfall bulk, 2026-10-05; box price = median of recent completed sales).', color=MUTED, fontsize=12)
f.tight_layout(rect=(0, 0.03, 1, 1)); f.savefig(os.path.join(M.OUT, 'charts', '13_8000_packs.png')); print('chart 13 written')
