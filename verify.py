"""
Check my work: re-derives the headline numbers from results/ and compares them to what the video claims.

    python3 verify.py

Exits non-zero if any claim is outside tolerance. Tolerances are loose on purpose: Monte Carlo noise and daily price
moves should not fail the check; a structural error should.
"""
import csv, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'results')
rows = list(csv.DictReader(open(os.path.join(OUT, 'set_summary.csv'))))
gp = {r[0]: r[1] for r in csv.reader(open(os.path.join(OUT, 'godpack.csv')))}
def fl(x): return float(x) if x not in ('', None) else None

claims = []
def claim(name, value, expect, tol):
    ok = abs(value - expect) <= tol
    claims.append((ok, name, value, expect, tol)); return ok

play = [r for r in rows if r['kind'] == 'play' and r['ev_to_price']]
coll = [r for r in rows if r['kind'] == 'collector' and r['ev_to_price']]
claim('median Play Booster box EV / price (market)', st.median(fl(r['ev_to_price']) for r in play), 1.35, 0.15)
claim('median Play Booster box cash-out / price', st.median(fl(r['real_to_price']) for r in play), 0.49, 0.08)
claim('median Collector box EV / price (market)', st.median(fl(r['ev_to_price']) for r in coll), 0.62, 0.10)
claim('median P(Play box beats price, cash-out)', st.median(fl(r['p_box_beats_price_realizable']) for r in play), 0.014, 0.03)
claim('max P(Play box beats price, cash-out) = Karlov Manor', max(fl(r['p_box_beats_price_realizable']) for r in play), 0.11, 0.05)
claim('Play boxes above 1 at market (of 16)', sum(fl(r['ev_to_price']) > 1 for r in play), 15, 0)
claim('Draft boxes above 1 at market (of 31)', sum(fl(r['ev_to_price']) > 1 for r in rows if r['kind'] == 'draft' and r['ev_to_price']), 17, 1)
claim('no product clears 1.0 in cash (max ratio)', max(fl(r['real_to_price']) for r in rows if r['real_to_price']) < 1, 1, 0)
claim('Booster god pack value ($)', fl(gp['Booster Pack GOD PACK value (10 R/M + 2 BF + 2 foil BF, no celeb card)']), 65, 15)
claim('Collector god pack value ($)', fl(gp['Collector GOD PACK value (foil land + 3 foil R/M + 3 BF + 5 foil BF, no celeb)']), 101, 25)
claim('EV lift per Booster Pack ($)', fl(gp['EV lift per Booster Pack from god packs ($)']), 0.058, 0.02)
claim('foil change break-even rate (%)', fl(gp['break-even new foil R/M rate so pack EV is unchanged (%)']), 12.6, 3.0)
claim('Collector shrink EV removed ($/pack)', fl(gp['EV removed per Collector Booster (2 foil C + 1 foil U) ($)']), 1.07, 0.4)
claim('rares+mythics per Booster Pack', fl(gp['rares+mythics per Booster Pack today (all slots)']), 1.38, 0.1)

# significance outputs (run significance.py first; skipped if absent)
sig = os.path.join(OUT, 'significance_across_sets.csv')
if os.path.exists(sig):
    cs = {(r['group'], r['measure']): r for r in csv.DictReader(open(sig))}
    claim('Play Boosters above 1 at market: Wilcoxon p < 0.01', float(cs[('Play Booster boxes 2024-26', 'market EV / price')]['wilcoxon_p']) < 0.01, 1, 0)
    claim('Play Boosters below 1 in cash: Wilcoxon p < 0.001', float(cs[('Play Booster boxes 2024-26', 'cash-out / price')]['wilcoxon_p']) < 0.001, 1, 0)
    claim('Collector boxes below 1 at market: Wilcoxon p < 0.001', float(cs[('Collector boxes (all years)', 'market EV / price')]['wilcoxon_p']) < 0.001, 1, 0)

# the ad-lib bank (run fun_facts.py first; skipped if absent)
ffp = os.path.join(OUT, 'fun_facts.json')
if os.path.exists(ffp):
    import json; ff = json.load(open(ffp))
    claim('ad-lib: a god pack is ~15x likelier than the top play-booster card', ff['godpack_vs_top_card'], 15, 5)
    claim('ad-lib: % of rare-slot pulls under $1 (reality fracture)', ff['fra_rare_slot_bulk_pct'], 55, 8)
    claim('ad-lib: mythic in the rare slot, 1 in N packs', ff['fra_rare_slot_mythic_one_in'], 6.0, 0.6)
    claim('ad-lib: $10+ rare-slot pulls per play box', ff['fra_rare_slot_over_10_per_box'], 1.75, 0.6)
    claim('ad-lib: % of play boxes with no $20 card', ff['play_pct_boxes_with_zero_20plus'], 38, 8)
    claim('ad-lib: top 10 printings, % of pack EV', ff['fra_top10_share_of_ev'], 20, 5)
    claim('ad-lib: median card in a pack (cents)', ff['fra_median_card_cents'], 23, 8)
    claim('ad-lib: msrp per card (cents)', ff['fra_msrp_per_card_cents'], 39, 1)
    claim('ad-lib: boxes to see every mythic once', ff['fra_boxes_to_see_every_mythic'], 100, 20)
    claim('ad-lib: all the commons in a box ($)', ff['fra_box_commons_value'], 47, 10)
    claim('ad-lib: kaladesh sealed box / cards inside (x)', ff['sealed_premium_x'], 4.5, 1)
    claim('ad-lib: packs simulated (millions)', ff['packs_simulated'] / 1e6, 10.3, 0.05)
    claim('ad-lib: best cash-out play box ratio (MH3)', ff['best_cash_ratio'], 0.76, 0.06)
    claim('selling time: sub-$1 cards in a box', ff['fra_box_under_1_count'], 395, 10)
    claim('selling time: listable ($1+) cards in a box', ff['fra_box_listable_count'], 25, 4)
    claim('ad-lib: omnipresence chase, boxes for a coin flip', ff['fra_collector_top_boxes_for_half'], 130, 30)

# what-ifs: god packs in every set since 2016, and the collector cut on every collector box since 2019
gh = os.path.join(OUT, 'godpack_history.csv'); cc = os.path.join(OUT, 'collector_cut.csv')
if os.path.exists(gh) and os.path.exists(cc):
    G = list(csv.DictReader(open(gh))); CC = list(csv.DictReader(open(cc)))
    Gp = [r for r in G if r['ratio_before']]
    claim('history: boxes that flip across 1.0 on paper with 1-in-1,000 god packs', sum((fl(r['ratio_before']) < 1) != (fl(r['ratio_after']) < 1) for r in Gp), 0, 0)
    claim('history: boxes that flip on paper at 1 in 100', sum((fl(r['ratio_before']) < 1) != (fl(r['ratio_after_1in100']) < 1) for r in Gp), 2, 1)
    claim('history: most a god pack ever adds to a box ($)', max(fl(r['lift_box']) for r in G), 2.1, 0.6)
    claim('history: median god pack lift per box ($)', st.median(fl(r['lift_box']) for r in G), 0.9, 0.3)
    claim('history: biggest change in P(box pays in cash), pct points', max(100 * (fl(r['p_cash_after']) - fl(r['p_cash_before'])) for r in Gp), 0.6, 0.6)
    claim('history: most valuable god pack (LotR / MH3, $)', max(fl(r['gp_mean']) for r in G), 69, 15)
    claim('collector cut: median value removed per pack ($)', st.median(fl(r['cut_per_pack']) for r in CC), 0.97, 0.3)
    claim('collector cut: median value removed per box ($)', st.median(fl(r['cut_per_box']) for r in CC), 11.6, 3)
    claim('collector cut: median share of pack ev (%)', 100 * st.median(fl(r['share_of_pack_ev']) for r in CC), 3.0, 1.5)
    claim('collector cut: median cash value per pack ($)', st.median(fl(r['cut_cash_per_pack']) for r in CC), 0.10, 0.08)
    claim('collector cut: reality fracture per box ($)', fl(next(r for r in CC if r['product'] == 'fra-collector')['cut_per_box']), 12.8, 3)
    claim('collector cut: biggest box (MH3, $)', max(fl(r['cut_per_box']) for r in CC), 23.8, 5)

# arithmetic that does not depend on prices at all
claim('P(>=1 god pack) in a 30-pack box (%)', 100 * (1 - (1 - 1/1000) ** 30), 2.96, 0.01)
claim('P(>=1 god pack) in a 6-box case (%)', 100 * (1 - (1 - 1/1000) ** 180), 16.5, 0.1)
claim('boxes for a 50% chance at a god pack', __import__('math').log(0.5) / __import__('math').log(1 - 1/1000) / 30, 23.1, 0.1)
claim('Collector MSRP per card, 15 -> 12 cards (% increase)', 100 * (26.99 / 12) / (26.99 / 15) - 100, 25.0, 0.01)

w = max(len(c[1]) for c in claims)
for ok, name, v, e, tol in claims:
    print(f"{'PASS' if ok else 'FAIL'}  {name:{w}}  got {v:8.3f}  claimed {e:8.3f}  (±{tol})")
bad = [c for c in claims if not c[0]]
print(f"\n{len(claims) - len(bad)}/{len(claims)} claims hold." + ('' if not bad else '  Prices move daily; if only the dollar claims fail, re-read the as-of date in README.'))
sys.exit(1 if bad else 0)
