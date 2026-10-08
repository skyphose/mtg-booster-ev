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
claim('median Play Booster box EV / price (market)', st.median(fl(r['ev_to_price']) for r in play), 1.27, 0.15)
claim('median Play Booster box cash-out / price', st.median(fl(r['real_to_price']) for r in play), 0.46, 0.08)
claim('median Collector box EV / price (market)', st.median(fl(r['ev_to_price']) for r in coll), 0.58, 0.10)
claim('median P(Play box beats price, cash-out)', st.median(fl(r['p_box_beats_price_realizable']) for r in play), 0.01, 0.03)
claim('max P(Play box beats price, cash-out) = Karlov Manor', max(fl(r['p_box_beats_price_realizable']) for r in play), 0.11, 0.05)
claim('Booster god pack value ($)', fl(gp['Booster Pack GOD PACK value (10 R/M + 2 BF + 2 foil BF, no celeb card)']), 63, 15)
claim('Collector god pack value ($)', fl(gp['Collector GOD PACK value (foil land + 3 foil R/M + 3 BF + 5 foil BF, no celeb)']), 99, 25)
claim('EV lift per Booster Pack ($)', fl(gp['EV lift per Booster Pack from god packs ($)']), 0.056, 0.02)
claim('foil change break-even rate (%)', fl(gp['break-even new foil R/M rate so pack EV is unchanged (%)']), 11.8, 3.0)
claim('Collector shrink EV removed ($/pack)', fl(gp['EV removed per Collector Booster (2 foil C + 1 foil U) ($)']), 1.02, 0.4)
claim('rares+mythics per Booster Pack', fl(gp['rares+mythics per Booster Pack today (all slots)']), 1.28, 0.1)

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
    claim('ad-lib: % of rare-slot pulls under $1 (reality fracture)', ff['fra_rare_slot_bulk_pct'], 58, 8)
    claim('ad-lib: mythic in the rare slot, 1 in N packs', ff['fra_rare_slot_mythic_one_in'], 6.3, 0.6)
    claim('ad-lib: $10+ rare-slot pulls per play box', ff['fra_rare_slot_over_10_per_box'], 1.75, 0.6)
    claim('ad-lib: % of play boxes with no $20 card', ff['play_pct_boxes_with_zero_20plus'], 39, 8)
    claim('ad-lib: top 10 printings, % of pack EV', ff['fra_top10_share_of_ev'], 20, 5)
    claim('ad-lib: median card in a pack (cents)', ff['fra_median_card_cents'], 22, 8)
    claim('ad-lib: msrp per card (cents)', ff['fra_msrp_per_card_cents'], 39, 1)
    claim('ad-lib: boxes to see every mythic once', ff['fra_boxes_to_see_every_mythic'], 100, 20)
    claim('ad-lib: all the commons in a box ($)', ff['fra_box_commons_value'], 41, 10)
    claim('ad-lib: kaladesh sealed box / cards inside (x)', ff['sealed_premium_x'], 4.5, 1)
    claim('ad-lib: packs simulated (millions)', ff['packs_simulated'] / 1e6, 10.3, 0.05)
    claim('ad-lib: omnipresence chase, boxes for a coin flip', ff['fra_collector_top_boxes_for_half'], 130, 30)

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
