"""
is any of this statistically significant, or did i just run a lot of dice?

four separate things could be wrong, so i test them separately:

  A. monte carlo noise   - per product, t-test of simulated box values vs the box price. with thousands of boxes this is never the problem.
  B. five sales          - the box price is the median of only 5 completed sales. bootstrap them and see how much the answer moves.
  C. card prices         - tcgplayer market prices are estimates. shake every card price by lognormal noise (20%) 300 times.
  D. across sets         - each set is one data point. wilcoxon signed-rank + sign test on log(ratio), by box type.
  E. god pack spread     - the god pack value is an average. simulate 20,000 god packs and look at the distribution.

    python3 significance.py     # ~4 min, writes results/significance_*.csv
"""
import csv, os, math, random, statistics as st, collections
import numpy as np
from scipy import stats
from ev_model import BY_CODE, card_price, prices, PRODUCTS, box_price, realizable, OUT, sales

random.seed(21); np.random.seed(21)

# ----------------------------------------------------------------------------- helpers
def box_samplers(code):
    x = BY_CODE[code]
    configs = [(b['weight'], b['sheets']) for b in x['boosters']]
    cw = np.array([c[0] for c in configs], float); cw /= cw.sum()
    samplers = {}
    for name, sh in x['sheets'].items():
        keys = list(sh['cards'].keys()); w = np.array(list(sh['cards'].values()), float); w /= w.sum()
        samplers[name] = (np.array([card_price(k)[0] for k in keys]), w, sh.get('fixed', False))
    return configs, cw, samplers

def sim_boxes(code, packs, n, price_mult=None):
    """vectorised-ish Monte Carlo; price_mult: optional dict sheet->array multiplier for card-price noise"""
    configs, cw, samplers = box_samplers(code)
    mv = np.zeros(n); rv = np.zeros(n)
    real_v = np.vectorize(realizable)
    for i in range(n):
        idx = np.random.choice(len(configs), size=packs, p=cw)
        for ci in np.unique(idx):
            reps = int((idx == ci).sum())
            for s, k in configs[ci][1].items():
                vals, w, fixed = samplers[s]
                if price_mult is not None: vals = vals * price_mult[s]
                if fixed: draw = np.tile(vals, reps)
                else: draw = np.random.choice(vals, size=k * reps, p=w)
                mv[i] += draw.sum(); rv[i] += real_v(draw).sum()
    return mv, rv

rows = list(csv.DictReader(open(os.path.join(OUT, 'set_summary.csv'))))
def fl(v): return float(v) if v not in ('', None) else None

# ----------------------------------------------------------------------------- A + B: per product
per = []
focus = [p for p in PRODUCTS if p[4] in ('play', 'collector') and p[2] >= 2024]
print(f'A/B: simulating {len(focus)} products x 2,000 boxes ...')
for (s, name, year, code, kind, packs, msrp) in focus:
    bp = box_price(s, kind)
    if not bp: continue
    sale_prices = [x[1] for x in sales[(s, bp[5])]]
    mv, rv = sim_boxes(code, packs, 2000)
    price = bp[0]
    t_m, p_m = stats.ttest_1samp(mv, price); t_r, p_r = stats.ttest_1samp(rv, price)
    # bootstrap the 5 sales -> median price; combine with the simulated boxes
    boot_ratio_m, boot_ratio_r, boot_pbeat_m, boot_pbeat_r = [], [], [], []
    for _ in range(2000):
        bp_b = st.median(random.choices(sale_prices, k=len(sale_prices)))
        boot_ratio_m.append(mv.mean() / bp_b); boot_ratio_r.append(rv.mean() / bp_b)
        boot_pbeat_m.append((mv > bp_b).mean()); boot_pbeat_r.append((rv > bp_b).mean())
    q = lambda a: (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))
    per.append(dict(product=code, kind=kind, box_price=round(price, 2), n_sales=len(sale_prices), sales_min=min(sale_prices), sales_max=max(sale_prices),
                    ev_market=round(mv.mean(), 2), ev_cashout=round(rv.mean(), 2),
                    t_market=round(t_m, 1), p_market=f'{p_m:.1e}', t_cashout=round(t_r, 1), p_cashout=f'{p_r:.1e}',
                    ratio_market=round(mv.mean() / price, 3), ratio_market_ci95=f'{q(boot_ratio_m)[0]:.2f}-{q(boot_ratio_m)[1]:.2f}',
                    ratio_cashout=round(rv.mean() / price, 3), ratio_cashout_ci95=f'{q(boot_ratio_r)[0]:.2f}-{q(boot_ratio_r)[1]:.2f}',
                    p_beat_market=round((mv > price).mean(), 3), p_beat_market_ci95=f'{q(boot_pbeat_m)[0]:.2f}-{q(boot_pbeat_m)[1]:.2f}',
                    p_beat_cashout=round((rv > price).mean(), 3), p_beat_cashout_ci95=f'{q(boot_pbeat_r)[0]:.3f}-{q(boot_pbeat_r)[1]:.3f}'))
    print(f"  {code:15} market {mv.mean():6.0f} vs price {price:6.0f}  t={t_m:7.1f}  | cash {rv.mean():6.0f}  t={t_r:7.1f} | boot ratio_m {per[-1]['ratio_market_ci95']}  ratio_c {per[-1]['ratio_cashout_ci95']}")
with open(os.path.join(OUT, 'significance_per_product.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(per[0].keys())); w.writeheader(); w.writerows(per)

# ----------------------------------------------------------------------------- D: across sets
print('\nD: across-set tests (each set = one observation)')
cross = []
for kind, label in [('play', 'Play Booster boxes 2024-26'), ('collector', 'Collector boxes (all years)'), ('draft', 'Draft boxes (all years)'), ('set', 'Set Booster boxes')]:
    rs = [r for r in rows if r['kind'] == kind and r['ev_to_price']]
    # H1 follows the claim made in the video: Play Boosters above break-even at market; everything else below.
    for col, name, alt in [('ev_to_price', 'market EV / price', 'greater' if kind == 'play' else 'less'), ('real_to_price', 'cash-out / price', 'less')]:
        x = np.log([fl(r[col]) for r in rs])
        n = len(x); above = int((x > 0).sum())
        w = stats.wilcoxon(x, alternative=alt) if n >= 6 else None
        signp = stats.binomtest(above if alt == 'greater' else n - above, n, 0.5, alternative='greater').pvalue
        t = stats.ttest_1samp(x, 0, alternative=alt)
        cross.append(dict(group=label, measure=name, n=n, sets_above_1=above, median_ratio=round(float(np.exp(np.median(x))), 3),
                          geo_mean_ratio=round(float(np.exp(x.mean())), 3), ci95_geo_mean=f'{math.exp(x.mean()-1.96*x.std(ddof=1)/math.sqrt(n)):.2f}-{math.exp(x.mean()+1.96*x.std(ddof=1)/math.sqrt(n)):.2f}',
                          H1=f'ratio {alt} than 1', wilcoxon_p=f'{w.pvalue:.2e}' if w else '', sign_test_p=f'{signp:.2e}', t_test_p=f'{t.pvalue:.2e}'))
        print(f"  {label:28} {name:18} n={n:2d} above1={above:2d} median={cross[-1]['median_ratio']:.2f} geo-mean CI {cross[-1]['ci95_geo_mean']}  Wilcoxon p={cross[-1]['wilcoxon_p']} sign p={signp:.1e}")
with open(os.path.join(OUT, 'significance_across_sets.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(cross[0].keys())); w.writeheader(); w.writerows(cross)

# ----------------------------------------------------------------------------- C: card-price noise (analytic EV, fast)
print('\nC: card-price measurement error, lognormal sigma=20% per printing, 300 draws')
def analytic(code, mult_by_key):
    x = BY_CODE[code]; tw = sum(b['weight'] for b in x['boosters']); ev = 0.0; rv = 0.0
    for b in x['boosters']:
        w = b['weight'] / tw
        for s, n in b['sheets'].items():
            sh = x['sheets'][s]; t = sum(sh['cards'].values())
            e = sum(wt * card_price(k)[0] * mult_by_key(k) for k, wt in sh['cards'].items()) / t
            r = sum(wt * realizable(card_price(k)[0] * mult_by_key(k)) for k, wt in sh['cards'].items()) / t
            ev += w * n * e; rv += w * n * r
    return ev, rv
play_rows = [(p, box_price(p[0], 'play')) for p in PRODUCTS if p[4] == 'play' and box_price(p[0], 'play')]
med_m, med_r, frac_m_above, frac_r_below = [], [], [], []
for d in range(300):
    noise = collections.defaultdict(lambda: float(np.random.lognormal(0, 0.2)))
    m = lambda k: noise[k]
    rm, rr = [], []
    for (s, name, year, code, kind, packs, msrp), bp in play_rows:
        ev, rv = analytic(code, m); rm.append(ev * packs / bp[0]); rr.append(rv * packs / bp[0])
    med_m.append(st.median(rm)); med_r.append(st.median(rr)); frac_m_above.append(np.mean(np.array(rm) > 1)); frac_r_below.append(np.mean(np.array(rr) < 1))
noise_summary = dict(median_market_ratio_ci95=f'{np.percentile(med_m,2.5):.2f}-{np.percentile(med_m,97.5):.2f}', median_cashout_ratio_ci95=f'{np.percentile(med_r,2.5):.2f}-{np.percentile(med_r,97.5):.2f}',
                     draws_with_median_market_above_1=float(np.mean(np.array(med_m) > 1)), draws_with_median_cashout_below_1=float(np.mean(np.array(med_r) < 1)),
                     mean_share_of_play_sets_above_1_market=float(np.mean(frac_m_above)), mean_share_of_play_sets_below_1_cashout=float(np.mean(frac_r_below)))
print(' ', noise_summary)

# ----------------------------------------------------------------------------- E: god pack spread
print('\nE: god pack value distribution (20,000 simulated god packs, Reality Fracture sheets)')
def sheet_sampler(code, name):
    sh = BY_CODE[code]['sheets'][name]; keys = list(sh['cards'].keys()); w = np.array(list(sh['cards'].values()), float); w /= w.sum()
    return np.array([card_price(k)[0] for k in keys]), w
rm_v, rm_w = sheet_sampler('fra-play', 'rare_mythic'); bf_v, bf_w = sheet_sampler('fra-collector', 'non_foil_boosterfun'); bff_v, bff_w = sheet_sampler('fra-collector', 'foil_boosterfun')
gp = np.random.choice(rm_v, (20000, 10), p=rm_w).sum(1) + np.random.choice(bf_v, (20000, 2), p=bf_w).sum(1) + np.random.choice(bff_v, (20000, 2), p=bff_w).sum(1)
gp_summary = dict(mean=round(float(gp.mean()), 2), median=round(float(np.median(gp)), 2), p10=round(float(np.percentile(gp, 10)), 2), p90=round(float(np.percentile(gp, 90)), 2),
                  p99=round(float(np.percentile(gp, 99)), 2), share_under_50=round(float((gp < 50).mean()), 3), share_over_100=round(float((gp > 100).mean()), 3),
                  lift_per_pack_ci90=f'{(np.percentile(gp,10)-6.9)/1000:.3f}-{(np.percentile(gp,90)-6.9)/1000:.3f}')
print(' ', gp_summary)

with open(os.path.join(OUT, 'significance_summary.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['test', 'metric', 'value'])
    for k, v in noise_summary.items(): w.writerow(['C card-price noise', k, v])
    for k, v in gp_summary.items(): w.writerow(['E god pack spread', k, v])
print('\nwritten: results/significance_per_product.csv, significance_across_sets.csv, significance_summary.csv')
