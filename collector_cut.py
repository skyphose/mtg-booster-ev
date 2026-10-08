"""
the 2027 collector booster cut, priced on every collector booster since they started in 2019.

wizards: two foil commons and one foil uncommon come out of collector boosters, nothing replaces them, and the price
doesn't change. so for each set: what were those three cards worth (at market, and in cash after the same haircut
as everywhere else), how much is that per box, and what share of the pack's cards vs the pack's value is it.

the removed cards are priced as the set's own foil common / foil uncommon sheet averages (the plain foil slots, not
the showcase ones). run ev_model.py first.  -> results/collector_cut.csv, results/charts/12_collector_cut.png
"""
import csv, os, statistics as st
import ev_model as M

summary = {r['product']: r for r in csv.DictReader(open(os.path.join(M.OUT, 'set_summary.csv')))}
FC = ('foil_common', 'foil_common_or_basic', 'foil_sfc_common'); FU = ('foil_uncommon', 'foil_sfc_uncommon')

def sheet_avg(code, names, cash=False):
    x = M.BY_CODE[code]
    for n in names:
        if n in x['sheets']:
            sh = x['sheets'][n]['cards']; tw = sum(sh.values())
            f = (lambda p: M.realizable(p)) if cash else (lambda p: p)
            return sum(w * f(M.card_price(k)[0]) for k, w in sh.items()) / tw, n
    return None, None

rows = []
for (s, name, year, code, kind, packs, msrp) in M.PRODUCTS:
    if kind != 'collector': continue
    c, cn = sheet_avg(code, FC); u, un = sheet_avg(code, FU)
    cc, _ = sheet_avg(code, FC, cash=True); uc, _ = sheet_avg(code, FU, cash=True)
    if c is None or u is None: print('skip', code); continue
    r = summary[code]; ev_pack = float(r['ev_pack']); real_pack = float(r['real_box']) / packs
    cut = 2 * c + u; cut_cash = 2 * cc + uc
    # the single best card on those two sheets, and its odds of being one of the three cut cards
    best = max(((M.card_price(k)[0], M.card_price(k)[3]) for n in (cn, un) for k in M.BY_CODE[code]['sheets'][n]['cards']))
    price = float(r['box_price_sales_median']) if r['box_price_sales_median'] else None
    rows.append(dict(set=s, name=name, year=year, product=code, foil_common_avg=round(c, 3), foil_uncommon_avg=round(u, 3),
                     cut_per_pack=round(cut, 2), cut_per_box=round(cut * packs, 2), cut_per_case=round(cut * packs * 6, 2),
                     cut_cash_per_pack=round(cut_cash, 3), cut_cash_per_box=round(cut_cash * packs, 2),
                     share_of_cards=round(3 / 15, 3), share_of_pack_ev=round(cut / ev_pack, 4), share_of_pack_cash=round(cut_cash / real_pack, 4) if real_pack else '',
                     ratio_before=r['ev_to_price'], ratio_after=round((float(r['ev_box']) - cut * packs) / price, 3) if price else '',
                     best_cut_card=f'{best[1]} (${best[0]:.2f} foil)'))
    print(f"{code:15} cut ${cut:5.2f}/pack ${cut * packs:6.2f}/box  cash ${cut_cash:4.2f}/pack  {100 * cut / ev_pack:4.1f}% of ev for 20% of the cards   best: {best[1]} ${best[0]:.2f}")

with open(os.path.join(M.OUT, 'collector_cut.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
med = lambda k: st.median(r[k] for r in rows)
print(f"median cut ${med('cut_per_pack'):.2f}/pack, ${med('cut_per_box'):.2f}/box, {100 * med('share_of_pack_ev'):.1f}% of pack ev; cash ${med('cut_cash_per_pack'):.2f}/pack")

# ----------------------------------------------------------------------------- chart 12
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
SURF, INK, INK2, MUTED, GRID = '#1a1a19', '#ffffff', '#c3c2b7', '#898781', '#2c2c2a'
MAGENTA, AQUA = '#d55181', '#199e70'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.edgecolor': GRID, 'font.size': 16, 'axes.titlesize': 24, 'axes.titleweight': 'bold'})
order = sorted(rows, key=lambda r: (r['year'], r['product']))
f, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
ys = range(len(order))
ax.barh(ys, [r['cut_per_box'] for r in order], color=MAGENTA, label='at market')
ax.barh(ys, [r['cut_cash_per_box'] for r in order], color=AQUA, label='what you could actually sell them for')
ax.set_yticks(list(ys)); ax.set_yticklabels([f"{r['name']} ('{str(r['year'])[2:]})" for r in order], fontsize=12); ax.invert_yaxis()
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'${v:.0f}')); ax.grid(True, color=GRID, axis='x')
for i, r in enumerate(order): ax.text(r['cut_per_box'] + 0.3, i, f"${r['cut_per_box']:.0f}", va='center', fontsize=11, color=INK2)
ax.set_title('The 2027 Collector cut (2 foil commons + 1 foil uncommon), applied to every Collector box since 2019')
ax.set_xlabel('value removed per 12-pack box'); ax.legend(loc='lower right', fontsize=14, frameon=False)
f.text(0.01, 0.01, 'Set\'s own foil common / foil uncommon sheet averages, today\'s prices (Scryfall bulk, 2026-10-05). Cash: under \\$1 = \\$0, \\$1-5 at 50%, \\$5+ at 70%.', color=MUTED, fontsize=13)
f.tight_layout(rect=(0, 0.03, 1, 1)); f.savefig(os.path.join(M.OUT, 'charts', '12_collector_cut.png')); print('chart 12 written')
