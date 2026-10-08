"""
fun facts for the video. every number i drop as an ad-lib comes out of this file, from the same data as the model,
so if you want to check one, run it:

    python3 fun_facts.py            # prints them all
    python3 fun_facts.py --json     # same thing as json (also written to results/fun_facts.json, which verify.py checks)

needs results/ from ev_model.py and godpack_model.py (./run_all.sh does both).
"""
import csv, json, math, os, random, statistics as st, sys, collections
import ev_model as M

HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, 'results')
random.seed(11)
summary = {r['product']: r for r in csv.DictReader(open(os.path.join(RES, 'set_summary.csv')))}
sims = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(RES, 'box_sim.csv'))):
    sims[r['product']].append((float(r['box_value']), float(r['realizable']), int(r['cards_over_20'])))
F = {}  # key -> value, printed and checked

def card_odds(code):
    """per-pack probability that each printing shows up at least once, plus each printing's price.
    sheets draw with replacement (same as the model); fixed sheets give every card."""
    x = M.BY_CODE[code]; tw = sum(b['weight'] for b in x['boosters'])
    miss = collections.defaultdict(lambda: 1.0)  # P(card not in pack), averaged over pack configs below
    acc = collections.defaultdict(float)
    for b in x['boosters']:
        wb = b['weight'] / tw; local = collections.defaultdict(lambda: 1.0)
        for s, n in b['sheets'].items():
            sh = x['sheets'][s]; sw = sum(sh['cards'].values())
            for k, w in sh['cards'].items():
                local[k] *= 0.0 if sh.get('fixed') else (1 - w / sw) ** n
        for k in set(list(local) + list(acc)):
            acc[k] += wb * (1 - local.get(k, 1.0))
    return {k: (p, M.card_price(k)[0], M.card_price(k)[3], M.card_price(k)[2], k) for k, p in acc.items()}

def ev_contrib(code):
    """expected $ per pack from each printing (count-weighted, not just 'at least once')."""
    x = M.BY_CODE[code]; tw = sum(b['weight'] for b in x['boosters']); out = collections.defaultdict(float)
    for b in x['boosters']:
        wb = b['weight'] / tw
        for s, n in b['sheets'].items():
            sh = x['sheets'][s]; sw = sum(sh['cards'].values())
            for k, w in sh['cards'].items():
                out[k] += wb * n * (w / sw) * M.card_price(k)[0]  # same weighting as ev_model.product_ev
    return out

def boxes_for_half(p_pack, packs):
    return math.log(0.5) / (packs * math.log(1 - p_pack)) if p_pack > 0 else float('inf')

# ----------------------------------------------------------------------------- reality fracture play booster
code, packs = 'fra-play', 30
odds = card_odds(code); contrib = ev_contrib(code); ev_pack = sum(contrib.values())
F['fra_printings'] = len(odds)
F['fra_sheets'] = len(M.BY_CODE[code]['sheets'])
top = max(odds.values(), key=lambda v: v[1])
F['fra_top_card'] = f"{top[2]} ({top[4]})"; F['fra_top_price'] = round(top[1], 2)
F['fra_top_one_in_packs'] = round(1 / top[0]); F['fra_top_boxes_for_half'] = round(boxes_for_half(top[0], packs), 1)
F['fra_top_cost_for_half_msrp'] = round(boxes_for_half(top[0], packs) * packs * 5.49)
ranked = sorted(contrib.items(), key=lambda kv: -kv[1])
F['fra_top10_share_of_ev'] = round(100 * sum(v for _, v in ranked[:10]) / ev_pack, 1)
n1 = max(1, round(len(ranked) * 0.01))
F['fra_top1pct_printings'] = n1; F['fra_top1pct_share_of_ev'] = round(100 * sum(v for _, v in ranked[:n1]) / ev_pack, 1)
over20 = sum(v for k, v in contrib.items() if odds[k][1] >= 20)
F['fra_share_of_ev_from_20plus_cards'] = round(100 * over20 / ev_pack, 1)
# the "typical" card: price of a card drawn at random from a pack, by slot weight
x = M.BY_CODE[code]; tw = sum(b['weight'] for b in x['boosters']); draws = []
for b in x['boosters']:
    for s, n in b['sheets'].items():
        sh = x['sheets'][s]; sw = sum(sh['cards'].values())
        for k, w in sh['cards'].items():
            draws.append((M.card_price(k)[0], b['weight'] / tw * n * w / sw))
draws.sort(); tot = sum(w for _, w in draws); c = 0
for p, w in draws:
    c += w
    if c >= tot / 2: F['fra_median_card_cents'] = round(p * 100); break
cards_per_pack = tot
F['fra_cards_per_pack'] = round(cards_per_pack, 1)
F['fra_msrp_per_card_cents'] = round(549 / cards_per_pack)
# price tiers in one box (feeds the Selling Time sheet in the workbook)
tiers = {'lt1': [0.0, 0.0], 'ge1': [0.0, 0.0], 'ge5': [0.0, 0.0]}
for pr, wgt in draws:
    e = wgt * packs
    t = tiers['lt1' if pr < 1 else 'ge1']; t[0] += e; t[1] += e * pr
    if pr >= 5: tiers['ge5'][0] += e; tiers['ge5'][1] += e * pr
F['fra_box_cards'] = round(cards_per_pack * packs)
F['fra_box_under_1_count'] = round(tiers['lt1'][0]); F['fra_box_under_1_value'] = round(tiers['lt1'][1], 1)
F['fra_box_listable_count'] = round(tiers['ge1'][0]); F['fra_box_listable_value'] = round(tiers['ge1'][1], 1)
F['fra_box_over_5_count'] = round(tiers['ge5'][0])
# rares and mythics: how many are bulk
rs = M.BY_CODE[code]['sheets']['rare_mythic']['cards']  # the rare slot itself (scryfall's booster flag lags on new sets)
rm = [(M.card_price(k)[0], M.card_price(k)[3]) for k in rs]
F['fra_rare_slot_printings'] = len(rm)
F['fra_rare_slot_under_1_pct'] = round(100 * sum(1 for p, _ in rm if p < 1) / len(rm))
F['fra_rare_slot_median'] = round(st.median(p for p, _ in rm), 2)
F['fra_rare_slot_under_2_pct'] = round(100 * sum(1 for p, _ in rm if p < 2) / len(rm))
# commons: what every common in a box adds up to
com = sum(v for k, v in contrib.items() if odds[k][3] == 'c' and ':foil' not in k)
F['fra_box_commons_value'] = round(com * packs, 2)
# coupon collector: packs to see every default-frame non-foil mythic at least once
def packs_to_collect(ps, trials=400):
    out = []
    for _ in range(trials):
        need = set(ps); n = 0
        while need:
            n += 1
            for k in list(need):
                if random.random() < ps[k]: need.discard(k)
        out.append(n)
    return st.median(out)
mp = {k: odds[k][0] for k in rs if odds[k][3] == 'm'}
F['fra_rare_slot_mythics'] = len(mp)
F['fra_packs_to_see_every_mythic'] = round(packs_to_collect(mp)) if mp else None
F['fra_boxes_to_see_every_mythic'] = round(F['fra_packs_to_see_every_mythic'] / packs, 1) if mp else None

# the rare slot, weighted by how often each card actually shows up
rsw = M.BY_CODE[code]['sheets']['rare_mythic']['cards']; rtot = sum(rsw.values())
F['fra_rare_slot_mythic_one_in'] = round(rtot / sum(w for k, w in rsw.items() if M.card_price(k)[2] == 'm'), 1)
F['fra_rare_slot_bulk_pct'] = round(100 * sum(w for k, w in rsw.items() if M.card_price(k)[0] < 1) / rtot)
F['fra_rare_slot_over_10_pct'] = round(100 * sum(w for k, w in rsw.items() if M.card_price(k)[0] >= 10) / rtot, 1)
F['fra_rare_slot_over_10_per_box'] = round(30 * sum(w for k, w in rsw.items() if M.card_price(k)[0] >= 10) / rtot, 2)

# ----------------------------------------------------------------------------- god pack comparisons
gp = {r['metric']: r['value'] for r in csv.DictReader(open(os.path.join(RES, 'godpack.csv')))}
F['godpack_vs_top_card'] = round((1 / 1000) / top[0], 2)  # >1: a god pack is more likely than the top card
F['god_pack_cards'] = 14
F['rm_added_per_1000_packs_pct'] = float(gp['R/M per 1000 packs: normal vs added by one god pack'].split('(+')[1].rstrip('%)'))

# ----------------------------------------------------------------------------- across every box we modeled
F['products_modeled'] = len(summary)
F['boxes_simulated'] = len(summary) * M.N_BOXES
F['packs_simulated'] = sum(int(r['packs']) for r in summary.values()) * M.N_BOXES
play = [r for r in summary.values() if r['kind'] == 'play']
F['play_products'] = len(play)
big = [b for r in play for b in sims[r['product']]]
F['play_avg_20plus_cards_per_box'] = round(st.mean(b[2] for b in big), 2)
F['play_pct_boxes_with_zero_20plus'] = round(100 * sum(1 for b in big if b[2] == 0) / len(big))
priced = [r for r in summary.values() if r['box_price_sales_median']]
best_real = max(priced, key=lambda r: float(r['real_to_price']))
F['best_cash_ratio_box'] = best_real['name'] + ' ' + best_real['kind']; F['best_cash_ratio'] = float(best_real['real_to_price'])
old = [r for r in priced if r['kind'] == 'draft' and int(r['year']) <= 2017]
prem = max(old, key=lambda r: float(r['box_price_sales_median']) / float(r['ev_box']))
F['sealed_premium_box'] = prem['name']; F['sealed_premium_x'] = round(float(prem['box_price_sales_median']) / float(prem['ev_box']), 1)
F['sealed_premium_box_price'] = round(float(prem['box_price_sales_median'])); F['sealed_premium_box_cards'] = round(float(prem['ev_box']))
coll = [r for r in priced if r['kind'] == 'collector']
pricey = max(coll, key=lambda r: float(r['box_price_sales_median']))
F['priciest_collector_box'] = pricey['name']; F['priciest_collector_price'] = round(float(pricey['box_price_sales_median']))
F['priciest_collector_cards'] = round(float(pricey['ev_box'])); F['priciest_collector_ratio'] = float(pricey['ev_to_price'])
evp = {r['product']: float(r['ev_pack']) for r in summary.values()}
F['highest_ev_pack'] = max(evp, key=evp.get); F['highest_ev_pack_usd'] = max(evp.values())
d = [r for r in summary.values() if r['kind'] in ('draft', 'play')]
F['highest_ev_main_pack'] = max(d, key=lambda r: float(r['ev_pack']))['name']; F['highest_ev_main_pack_usd'] = max(float(r['ev_pack']) for r in d)
F['lowest_ev_main_pack'] = min(d, key=lambda r: float(r['ev_pack']))['name']; F['lowest_ev_main_pack_usd'] = min(float(r['ev_pack']) for r in d)
# the single most valuable printing you can open in any product we modeled, and the odds
best = None
for (st_, name, year, pcode, kind, pk, _m) in M.PRODUCTS:
    if pcode not in M.BY_CODE: continue
    o = card_odds(pcode)
    k, v = max(o.items(), key=lambda kv: kv[1][1])
    if best is None or v[1] > best[1][1]: best = (pcode, v, pk)
F['priciest_openable'] = f"{best[1][2]} ({best[1][4]})"; F['priciest_openable_usd'] = round(best[1][1], 2)
F['priciest_openable_product'] = best[0]; F['priciest_openable_one_in_packs'] = round(1 / best[1][0])
F['priciest_openable_boxes_for_half'] = round(boxes_for_half(best[1][0], best[2]), 1)
co = card_odds('fra-collector'); k, v = max(co.items(), key=lambda kv: kv[1][1])
F['fra_collector_top'] = f"{v[2]} ({k})"; F['fra_collector_top_usd'] = round(v[1], 2)
F['fra_collector_top_one_in_packs'] = round(1 / v[0]); F['fra_collector_top_boxes_for_half'] = round(boxes_for_half(v[0], 12), 1)
F['fra_collector_top_cost_for_half_msrp'] = round(boxes_for_half(v[0], 12) * 12 * 26.99)
# what the plastic is worth: play box sale price per pack vs ev per pack, median across 2024-26
F['play_median_box_price_per_pack'] = round(st.median(float(r['box_price_sales_median']) / int(r['packs']) for r in play if r['box_price_sales_median']), 2)

json.dump(F, open(os.path.join(RES, 'fun_facts.json'), 'w'), indent=1)

if __name__ == '__main__':
    if '--json' in sys.argv: print(json.dumps(F, indent=1))
    else:
        for k, v in F.items(): print(f'{k:40} {v}')
