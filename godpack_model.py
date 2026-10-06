"""
the 2027 changes, priced on reality fracture (the newest set, so the closest thing to nauctis we have).

  A. god packs      - what one is worth, what 1-in-1,000 does to pack ev, how many boxes until you have a coin-flip shot
  B. foil change    - foil commons/uncommons leave, no guaranteed foil, foil rare rate "increased" (to what? unpublished) -> break-even
  C. collector cut  - 2 foil commons + 1 foil uncommon gone, price unchanged
  D. supply         - how many rares god packs actually add (spoiler: about 1%)

run ev_model.py first.
"""
import json, csv, os, math, random, statistics as st
from ev_model import BY_CODE, card_price, sheet_stats, product_ev, simulate_boxes, realizable, OUT, HERE, DATA

random.seed(11)
PLAY = BY_CODE['fra-play']; COLL = BY_CODE['fra-collector']
play_ev, play_cov, play_sheets, play_counts = product_ev('fra-play')
coll_ev, coll_cov, coll_sheets, coll_counts = product_ev('fra-collector')

def sheet_ev(x, name): return sheet_stats(x['sheets'][name])[0]

# --- building blocks (average value of one card drawn from each sheet)
rm_nonfoil      = sheet_ev(PLAY, 'rare_mythic')              # default-frame rare/mythic, non-foil
bf_nonfoil      = sheet_ev(COLL, 'non_foil_boosterfun')      # booster fun rare/mythic, non-foil
bf_foil         = sheet_ev(COLL, 'foil_boosterfun')          # booster fun rare/mythic, traditional foil (incl. rare fancy treatments)
rm_foil         = sheet_ev(COLL, 'foil_rare_mythic')         # default-frame rare/mythic, foil
foil_land       = sheet_ev(COLL, 'foil_tower_land')
foil_common     = sheet_ev(COLL, 'foil_common')
foil_uncommon   = sheet_ev(COLL, 'foil_uncommon')

# play booster foil slot decomposition (from the sheet itself)
fs = PLAY['sheets']['foil']; tw = sum(fs['cards'].values())
foil_by_r = {}
for k, w in fs['cards'].items():
    p, found, r, _ = card_price(k)
    foil_by_r.setdefault(r, [0.0, 0.0]); foil_by_r[r][0] += w; foil_by_r[r][1] += w * p
foil_share = {r: v[0] / tw for r, v in foil_by_r.items()}
foil_avg   = {r: v[1] / v[0] for r, v in foil_by_r.items()}
foil_slot_ev = sum(v[1] for v in foil_by_r.values()) / tw
p_foil_rm_today = foil_share.get('r', 0) + foil_share.get('m', 0)
foil_rm_avg = (foil_by_r.get('r', [0, 0])[1] + foil_by_r.get('m', [0, 0])[1]) / max(1e-9, (foil_by_r.get('r', [0, 0])[0] + foil_by_r.get('m', [0, 0])[0]))
foil_cu_ev = (foil_by_r.get('c', [0, 0])[1] + foil_by_r.get('u', [0, 0])[1]) / tw   # EV contributed by foil C/U in the slot
nonfoil_cu_avg = (sheet_ev(PLAY, 'common') * 0.6 + sheet_ev(PLAY, 'uncommon') * 0.4)   # a plain C/U card filling the slot when no foil

# --- A. god packs
CELEB = [0, 10, 25]   # celebration card value scenarios (unknown product; treat as a promo)
gp_play = 10 * rm_nonfoil + 2 * bf_nonfoil + 2 * bf_foil
gp_coll = foil_land + 3 * rm_foil + 3 * bf_nonfoil + 5 * bf_foil
lift_play = (gp_play - play_ev) / 1000
lift_coll = (gp_coll - coll_ev) / 300

def p_hit(packs, p): return 1 - (1 - p) ** packs
rows = []
rows.append(('Reality Fracture Play Booster EV (market, today)', round(play_ev, 2)))
rows.append(('Reality Fracture Collector Booster EV (market, today)', round(coll_ev, 2)))
rows.append(('avg default-frame R/M non-foil (play rare slot)', round(rm_nonfoil, 2)))
rows.append(('avg Booster Fun R/M non-foil', round(bf_nonfoil, 2)))
rows.append(('avg Booster Fun R/M foil', round(bf_foil, 2)))
rows.append(('avg default-frame R/M foil', round(rm_foil, 2)))
rows.append(('Booster Pack GOD PACK value (10 R/M + 2 BF + 2 foil BF, no celeb card)', round(gp_play, 2)))
rows.append(('Collector GOD PACK value (foil land + 3 foil R/M + 3 BF + 5 foil BF, no celeb)', round(gp_coll, 2)))
rows.append(('EV lift per Booster Pack from god packs ($)', round(lift_play, 4)))
rows.append(('EV lift per Collector Booster from god packs ($)', round(lift_coll, 4)))
rows.append(('EV lift per 30-pack Booster box ($)', round(lift_play * 30, 2)))
rows.append(('EV lift per 12-pack Collector box ($)', round(lift_coll * 12, 2)))
rows.append(('EV lift as % of Booster Pack MSRP $5.49', round(100 * lift_play / 5.49, 2)))
rows.append(('EV lift as % of Collector MSRP $26.99', round(100 * lift_coll / 26.99, 2)))
for packs, label in [(1, '1 pack'), (30, '1 box (30)'), (180, '1 case (6 boxes)'), (1000, '1000 packs')]:
    rows.append((f'P(at least one Booster god pack) in {label}', round(100 * p_hit(packs, 1 / 1000), 2)))
for packs, label in [(1, '1 pack'), (12, '1 box (12)'), (72, '1 case (6 boxes)'), (300, '300 packs')]:
    rows.append((f'P(at least one Collector god pack) in {label}', round(100 * p_hit(packs, 1 / 300), 2)))
rows.append(('Booster boxes to buy for a 50% chance of a god pack', round(math.log(0.5) / math.log(1 - 1 / 1000) / 30, 1)))
rows.append(('Collector boxes to buy for a 50% chance of a god pack', round(math.log(0.5) / math.log(1 - 1 / 300) / 12, 1)))
rows.append(('$ spent (MSRP) for a 50% chance - Booster', round(math.log(0.5) / math.log(1 - 1 / 1000) * 5.49, 0)))
rows.append(('$ spent (MSRP) for a 50% chance - Collector', round(math.log(0.5) / math.log(1 - 1 / 300) * 26.99, 0)))
for c in CELEB:
    rows.append((f'Booster god pack value if celebration card = ${c}', round(gp_play + c, 2)))

# --- B. foil change
rows.append(('--- FOIL CHANGE (Booster Packs) ---', ''))
rows.append(('today: foil slot EV ($)', round(foil_slot_ev, 3)))
rows.append(('today: share of foil slot that is common/uncommon (%)', round(100 * (foil_share.get('c', 0) + foil_share.get('u', 0)), 1)))
rows.append(('today: P(foil rare or mythic in a pack) (%)', round(100 * p_foil_rm_today, 2)))
rows.append(('today: avg value of a foil rare/mythic from that slot ($)', round(foil_rm_avg, 2)))
rows.append(('today: EV contributed by foil commons/uncommons ($/pack)', round(foil_cu_ev, 3)))
rows.append(('avg foil common ($)', round(foil_avg.get('c', 0), 3)))
rows.append(('avg foil uncommon ($)', round(foil_avg.get('u', 0), 3)))
rows.append(('plain common/uncommon filler value ($)', round(nonfoil_cu_avg, 3)))
rows.append(('collector sheet avg foil common ($)', round(foil_common, 3)))
rows.append(('collector sheet avg foil uncommon ($)', round(foil_uncommon, 3)))
foil_rows = []
for p_new in [p_foil_rm_today, 0.10, 0.125, 0.15, 0.20, 0.25, 0.333]:
    new_slot = p_new * foil_rm_avg + (1 - p_new) * nonfoil_cu_avg
    delta = new_slot - foil_slot_ev
    foil_rows.append(dict(p_foil_rm_new=round(p_new, 4), one_in=round(1 / p_new, 1), new_slot_ev=round(new_slot, 3), delta_per_pack=round(delta, 3), delta_per_box=round(delta * 30, 2)))
breakeven = (foil_slot_ev - nonfoil_cu_avg) / (foil_rm_avg - nonfoil_cu_avg)
rows.append(('break-even new foil R/M rate so pack EV is unchanged (%)', round(100 * breakeven, 2)))
rows.append(('break-even expressed as 1 in N packs', round(1 / breakeven, 1)))

# --- C. collector shrink
rows.append(('--- COLLECTOR SHRINK ---', ''))
loss = 2 * foil_common + foil_uncommon
rows.append(('EV removed per Collector Booster (2 foil C + 1 foil U) ($)', round(loss, 3)))
rows.append(('as % of Collector Booster EV', round(100 * loss / coll_ev, 2)))
rows.append(('as % of Collector MSRP $26.99', round(100 * loss / 26.99, 2)))
rows.append(('net Collector EV change incl. god pack lift ($/pack)', round(lift_coll - loss, 3)))
rows.append(('cards per Collector Booster before -> after', '15 -> 12'))
rows.append(('price per card at MSRP before -> after', f'{26.99/15:.2f} -> {26.99/12:.2f}'))

# --- D. supply
rows.append(('--- SUPPLY ---', ''))
rm_per_pack = play_counts['rare_mythic'] + sum(v for k, v in play_counts.items() if k.startswith('pair') or k.startswith('third')) * 0 \
              + 0  # keep simple: rare slot + wildcard/echo rares estimated below
# estimate R/M per pack from sheet rarity composition
def rm_rate(x):
    tot = 0.0
    twb = sum(b['weight'] for b in x['boosters'])
    for b in x['boosters']:
        w = b['weight'] / twb
        for s, n in b['sheets'].items():
            sh = x['sheets'][s]; tws = sum(sh['cards'].values())
            rshare = sum(wt for k, wt in sh['cards'].items() if card_price(k)[2] in ('r', 'm')) / tws
            tot += w * n * rshare
    return tot
rm_play = rm_rate(PLAY)
rows.append(('rares+mythics per Booster Pack today (all slots)', round(rm_play, 3)))
rows.append(('R/M per 1000 packs: normal vs added by one god pack', f'{rm_play*1000:.0f} vs +{14 - rm_play:.1f} (+{100*(14-rm_play)/(rm_play*1000):.2f}%)'))
foil_cu_per_pack = foil_share.get('c', 0) + foil_share.get('u', 0)
rows.append(('foil commons/uncommons per Booster Pack today -> 2027', f'{foil_cu_per_pack:.3f} -> 0'))
rows.append(('foil C/U per Collector Booster today -> 2027', f'{coll_counts["foil_common"]+coll_counts["foil_uncommon"]+sum(v for k,v in coll_counts.items() if k.startswith("pair"))*0:.0f} (+echo pairs) -> 3 fewer'))

# --- Monte Carlo: box value distribution with and without god packs (Booster box, 30 packs)
sim = simulate_boxes('fra-play', 30, n_boxes=3000)
base = [v[0] for v in sim]
with_gp = []
for v in base:
    hits = sum(1 for _ in range(30) if random.random() < 1 / 1000)
    with_gp.append(v + hits * (gp_play - play_ev))
def q(a, p): a = sorted(a); return a[int(p * (len(a) - 1))]
rows.append(('--- BOX DISTRIBUTION (Reality Fracture Booster box, market value) ---', ''))
rows.append(('mean / median / P10 / P90 / P99 without god packs', f'{st.mean(base):.0f} / {st.median(base):.0f} / {q(base,.1):.0f} / {q(base,.9):.0f} / {q(base,.99):.0f}'))
rows.append(('mean / median / P10 / P90 / P99 with god packs', f'{st.mean(with_gp):.0f} / {st.median(with_gp):.0f} / {q(with_gp,.1):.0f} / {q(with_gp,.9):.0f} / {q(with_gp,.99):.0f}'))
rows.append(('std dev without -> with', f'{st.pstdev(base):.1f} -> {st.pstdev(with_gp):.1f}'))

with open(os.path.join(OUT, 'godpack.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['metric', 'value']); w.writerows(rows)
with open(os.path.join(OUT, 'foil_scenarios.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(foil_rows[0].keys())); w.writeheader(); w.writerows(foil_rows)
for r in rows: print(f'{r[0]:75} {r[1]}')
print()
for r in foil_rows: print(r)
