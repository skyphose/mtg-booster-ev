"""
the booster ev model. 2016-2026, 99 box products.

what it does: takes wizards' published pack odds (as card-level sheet weights from mtg.wtf), prices every card off
scryfall (tcgplayer market), and works out what a pack and a box are worth. then it simulates thousands of boxes
so you get the spread and not just the average. box price = median of the 5 most recent completed tcgplayer sales,
because "market price" and "lowest listing" are not what people pay.

inputs live in data/, outputs land in results/. run `python3 ev_model.py --help` for the cash-out levers.
"""
import json, csv, random, statistics as st, os, collections, math

random.seed(7)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data'); OUT = os.path.join(HERE, 'results'); os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------- prices
BULK = {'c': 0.03, 'u': 0.05, 'r': 0.15, 'm': 0.25, 's': 0.05, 'b': 0.05}   # fallback when no price listed
prices = {}
for row in csv.DictReader(open(os.path.join(DATA, 'scryfall_prices.psv'), encoding='utf-8'), delimiter='|'):
    prices[(row['set'], row['cn'])] = row

def card_price(key):
    """key like 'fra:102', 'fra:102:foil', 'fra:102:etched'. Returns (price, found, rarity, name)."""
    parts = key.split(':')
    s, cn = parts[0], parts[1]
    finish = parts[2] if len(parts) > 2 else 'nonfoil'
    row = prices.get((s, cn))
    if row is None:
        return BULK['r'], False, '?', key
    r = row['rarity']
    usd, foil, etched = row['usd'], row['usd_foil'], row['usd_etched']
    if finish == 'foil':
        v = foil or usd
    elif finish == 'etched':
        v = etched or foil or usd
    else:
        v = usd or foil
    if v == '':
        return BULK.get(r, 0.05), False, r, row['name']
    return float(v), True, r, row['name']

# ----------------------------------------------------------------------------- sealed structure
sealed = json.load(open(os.path.join(DATA, 'sealed_basic_data.json')))
BY_CODE = {x['code']: x for x in sealed}

def sheet_stats(sheet):
    """expected value of one card drawn from a sheet, plus coverage (share of weight with a real price)."""
    tw = sum(sheet['cards'].values())
    ev = 0.0; covered = 0.0
    for key, w in sheet['cards'].items():
        p, found, _, _ = card_price(key)
        ev += w * p
        if found: covered += w
    return ev / tw, covered / tw

def product_ev(code):
    x = BY_CODE[code]
    sheets = {name: sheet_stats(sh) for name, sh in x['sheets'].items()}
    tw = sum(b['weight'] for b in x['boosters'])
    ev = 0.0
    exp_count = collections.Counter()
    for b in x['boosters']:
        w = b['weight'] / tw
        for s, n in b['sheets'].items():
            ev += w * n * sheets[s][0]
            exp_count[s] += w * n
    cov = sum(exp_count[s] * sheets[s][1] for s in exp_count) / sum(exp_count.values())
    return ev, cov, sheets, exp_count

# cash-out ("realizable") levers: what you actually net if you sell every card.
# Defaults: cards under $1 are bulk (worth 0), $1-5 cards net 50% (fees, shipping, buylist spread), $5+ net 70%.
# Override from the command line: python3 ev_model.py --bulk-below 1 --mid-keep 0.5 --high-keep 0.7 --boxes 4000
HAIRCUT = {'bulk_below': 1.0, 'mid_keep': 0.5, 'high_keep': 0.7, 'high_from': 5.0}
N_BOXES = 4000

def realizable(p):
    if p < HAIRCUT['bulk_below']: return 0.0
    if p < HAIRCUT['high_from']: return HAIRCUT['mid_keep'] * p
    return HAIRCUT['high_keep'] * p

def simulate_boxes(code, packs, n_boxes=20000):
    """Monte Carlo of whole boxes. Returns list of (market_value, realizable_value, n_cards_over_20)."""
    x = BY_CODE[code]
    configs = [(b['weight'], b['sheets']) for b in x['boosters']]
    cw = [c[0] for c in configs]
    # pre-build cumulative samplers per sheet
    samplers = {}
    for name, sh in x['sheets'].items():
        keys = list(sh['cards'].keys()); ws = list(sh['cards'].values())
        vals = [card_price(k)[0] for k in keys]
        samplers[name] = (vals, ws, sh.get('fixed', False))
    out = []
    for _ in range(n_boxes):
        mv = 0.0; rv = 0.0; big = 0
        for _p in range(packs):
            cfg = random.choices(configs, weights=cw)[0][1]
            for s, n in cfg.items():
                vals, ws, fixed = samplers[s]
                if fixed:
                    draws = vals  # fixed sheets give every card
                else:
                    draws = random.choices(vals, weights=ws, k=n)
                for v in draws:
                    mv += v; rv += realizable(v)
                    if v >= 20: big += 1
        out.append((mv, rv, big))
    return out

# ----------------------------------------------------------------------------- box prices (actual sales)
sales = collections.defaultdict(list)
for f in ['tcg_sealed_sales.psv', 'tcg_sealed_sales_extra.psv']:
    for line in open(os.path.join(DATA, f), encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if len(p) < 7: continue
        sales[(p[0], p[2])].append((p[3], float(p[4]), float(p[5] or 0), int(p[6])))
market = {}
for line in open(os.path.join(DATA, 'tcg_sealed_products.psv'), encoding='utf-8'):
    p = line.rstrip('\n').split('|')
    if len(p) >= 5: market[(p[0], p[3])] = p[4]

def box_price(set_code, kind):
    """median of the most recent completed TCGplayer sales for the box type."""
    pat = {'draft': ('Draft Booster Box', 'Draft Booster Display', 'Booster Box'),
           'set': ('Set Booster Box', 'Set Booster Display'),
           'play': ('Play Booster Display', 'Play Booster Box'),
           'collector': ('Collector Booster Display',)}[kind]
    for (c, name), lst in sales.items():
        if c != set_code: continue
        if any(name.endswith(p) for p in pat) and 'Case' not in name:
            # draft pattern 'Booster Box' must not match Set/Collector
            if kind == 'draft' and ('Set Booster' in name or 'Collector' in name or 'Play' in name): continue
            ps = [s[1] for s in lst]
            return st.median(ps), min(ps), max(ps), len(ps), market.get((c, name), ''), name
    return None

# ----------------------------------------------------------------------------- products to model
# (set, display name, year, booster code, kind, packs/box, launch MSRP box if known)
PRODUCTS = [
 ('soi','Shadows over Innistrad',2016,'soi-draft','draft',36,None),
 ('emn','Eldritch Moon',2016,'emn-draft','draft',36,None),
 ('kld','Kaladesh',2016,'kld-draft','draft',36,None),
 ('aer','Aether Revolt',2017,'aer-draft','draft',36,None),
 ('akh','Amonkhet',2017,'akh-draft','draft',36,None),
 ('hou','Hour of Devastation',2017,'hou-draft','draft',36,None),
 ('xln','Ixalan',2017,'xln-draft','draft',36,None),
 ('rix','Rivals of Ixalan',2018,'rix-draft','draft',36,None),
 ('dom','Dominaria',2018,'dom-draft','draft',36,None),
 ('m19','Core Set 2019',2018,'m19-draft','draft',36,None),
 ('grn','Guilds of Ravnica',2018,'grn-draft','draft',36,None),
 ('rna','Ravnica Allegiance',2019,'rna-draft','draft',36,None),
 ('war','War of the Spark',2019,'war-draft','draft',36,None),
 ('m20','Core Set 2020',2019,'m20-draft','draft',36,None),
 ('eld','Throne of Eldraine',2019,'eld-draft','draft',36,None),
 ('eld','Throne of Eldraine',2019,'eld-collector','collector',12,None),
 ('thb','Theros Beyond Death',2020,'thb-draft','draft',36,None),
 ('thb','Theros Beyond Death',2020,'thb-collector','collector',12,None),
 ('iko','Ikoria',2020,'iko-draft','draft',36,None),
 ('iko','Ikoria',2020,'iko-collector','collector',12,None),
 ('m21','Core Set 2021',2020,'m21-draft','draft',36,None),
 ('m21','Core Set 2021',2020,'m21-collector','collector',12,None),
 ('znr','Zendikar Rising',2020,'znr-draft','draft',36,None),
 ('znr','Zendikar Rising',2020,'znr-set','set',30,None),
 ('znr','Zendikar Rising',2020,'znr-collector','collector',12,None),
 ('khm','Kaldheim',2021,'khm-draft','draft',36,None),
 ('khm','Kaldheim',2021,'khm-set','set',30,None),
 ('khm','Kaldheim',2021,'khm-collector','collector',12,None),
 ('stx','Strixhaven',2021,'stx-draft','draft',36,None),
 ('stx','Strixhaven',2021,'stx-set','set',30,None),
 ('stx','Strixhaven',2021,'stx-collector','collector',12,None),
 ('afr','Forgotten Realms',2021,'afr-draft','draft',36,None),
 ('afr','Forgotten Realms',2021,'afr-set','set',30,None),
 ('afr','Forgotten Realms',2021,'afr-collector','collector',12,None),
 ('mid','Midnight Hunt',2021,'mid-draft','draft',36,None),
 ('mid','Midnight Hunt',2021,'mid-set','set',30,None),
 ('mid','Midnight Hunt',2021,'mid-collector','collector',12,None),
 ('vow','Crimson Vow',2021,'vow-draft','draft',36,None),
 ('vow','Crimson Vow',2021,'vow-set','set',30,None),
 ('vow','Crimson Vow',2021,'vow-collector','collector',12,None),
 ('neo','Neon Dynasty',2022,'neo-draft','draft',36,None),
 ('neo','Neon Dynasty',2022,'neo-set','set',30,None),
 ('neo','Neon Dynasty',2022,'neo-collector','collector',12,None),
 ('snc','New Capenna',2022,'snc-draft','draft',36,None),
 ('snc','New Capenna',2022,'snc-set','set',30,None),
 ('snc','New Capenna',2022,'snc-collector','collector',12,None),
 ('dmu','Dominaria United',2022,'dmu-draft','draft',36,None),
 ('dmu','Dominaria United',2022,'dmu-set','set',30,None),
 ('dmu','Dominaria United',2022,'dmu-collector','collector',12,None),
 ('bro',"Brothers' War",2022,'bro-draft','draft',36,None),
 ('bro',"Brothers' War",2022,'bro-set','set',30,None),
 ('bro',"Brothers' War",2022,'bro-collector','collector',12,None),
 ('one','All Will Be One',2023,'one-draft','draft',36,None),
 ('one','All Will Be One',2023,'one-set','set',30,None),
 ('one','All Will Be One',2023,'one-collector','collector',12,None),
 ('mom','March of the Machine',2023,'mom-draft','draft',36,None),
 ('mom','March of the Machine',2023,'mom-set','set',30,None),
 ('mom','March of the Machine',2023,'mom-collector','collector',12,None),
 ('ltr','LotR: Tales of Middle-earth',2023,'ltr-draft','draft',36,None),
 ('ltr','LotR: Tales of Middle-earth',2023,'ltr-set','set',30,None),
 ('ltr','LotR: Tales of Middle-earth',2023,'ltr-collector','collector',12,None),
 ('woe','Wilds of Eldraine',2023,'woe-draft','draft',36,None),
 ('woe','Wilds of Eldraine',2023,'woe-set','set',30,None),
 ('woe','Wilds of Eldraine',2023,'woe-collector','collector',12,None),
 ('lci','Lost Caverns of Ixalan',2023,'lci-draft','draft',36,None),
 ('lci','Lost Caverns of Ixalan',2023,'lci-set','set',30,None),
 ('lci','Lost Caverns of Ixalan',2023,'lci-collector','collector',12,None),
 ('mkm','Murders at Karlov Manor',2024,'mkm-play','play',36,None),
 ('mkm','Murders at Karlov Manor',2024,'mkm-collector','collector',12,None),
 ('otj','Outlaws of Thunder Junction',2024,'otj-play','play',36,None),
 ('otj','Outlaws of Thunder Junction',2024,'otj-collector','collector',12,None),
 ('mh3','Modern Horizons 3',2024,'mh3-play','play',36,None),
 ('mh3','Modern Horizons 3',2024,'mh3-collector','collector',12,None),
 ('blb','Bloomburrow',2024,'blb-play','play',36,None),
 ('blb','Bloomburrow',2024,'blb-collector','collector',12,None),
 ('dsk','Duskmourn',2024,'dsk-play','play',36,None),
 ('dsk','Duskmourn',2024,'dsk-collector','collector',12,None),
 ('fdn','Foundations',2024,'fdn-play','play',36,36*5.25),
 ('fdn','Foundations',2024,'fdn-collector','collector',12,12*24.99),
 ('dft','Aetherdrift',2025,'dft-play','play',30,30*5.49),
 ('dft','Aetherdrift',2025,'dft-collector','collector',12,12*24.99),
 ('tdm','Tarkir: Dragonstorm',2025,'tdm-play','play',30,30*5.49),
 ('tdm','Tarkir: Dragonstorm',2025,'tdm-collector','collector',12,12*24.99),
 ('fin','Final Fantasy',2025,'fin-play','play',30,30*6.99),
 ('fin','Final Fantasy',2025,'fin-collector','collector',12,12*37.99),
 ('eoe','Edge of Eternities',2025,'eoe-play','play',30,30*5.49),
 ('eoe','Edge of Eternities',2025,'eoe-collector','collector',12,12*24.99),
 ('spm',"Spider-Man",2025,'spm-play','play',30,30*6.99),
 ('spm',"Spider-Man",2025,'spm-collector','collector',12,12*37.99),
 ('tla','Avatar: The Last Airbender',2025,'tla-play','play',30,30*6.99),
 ('tla','Avatar: The Last Airbender',2025,'tla-collector','collector',12,12*37.99),
 ('ecl','Lorwyn Eclipsed',2026,'ecl-play','play',30,30*5.49),
 ('ecl','Lorwyn Eclipsed',2026,'ecl-collector','collector',12,12*26.99),
 ('hob','The Hobbit',2026,'hob-play','play',30,30*6.99),
 ('hob','The Hobbit',2026,'hob-collector','collector',12,12*37.99),
 ('sos','Secrets of Strixhaven',2026,'sos-play','play',30,30*5.49),
 ('sos','Secrets of Strixhaven',2026,'sos-collector','collector',12,12*26.99),
 ('fra','Reality Fracture',2026,'fra-play','play',30,30*5.49),
 ('fra','Reality Fracture',2026,'fra-collector','collector',12,12*26.99),
]

def main():
    rows = []; sim_rows = []; cov_rows = []
    for (s, name, year, code, kind, packs, msrp) in PRODUCTS:
        if code not in BY_CODE:
            print('missing booster', code); continue
        ev, cov, sheets, expc = product_ev(code)
        bp = box_price(s, kind)
        sim = simulate_boxes(code, packs, n_boxes=N_BOXES)
        mvs = sorted(v[0] for v in sim); rvs = sorted(v[1] for v in sim)
        price = bp[0] if bp else None
        p_beat = (sum(1 for v in mvs if v > price) / len(mvs)) if price else None
        p_beat_real = (sum(1 for v in rvs if v > price) / len(rvs)) if price else None
        row = dict(set=s, name=name, year=year, product=code, kind=kind, packs=packs,
                   ev_pack=round(ev, 2), ev_box=round(ev * packs, 2),
                   real_pack=round(st.mean(rvs) / packs, 2), real_box=round(st.mean(rvs), 2),
                   box_price_sales_median=round(price, 2) if price else '',
                   box_sales_min=round(bp[1], 2) if bp else '', box_sales_max=round(bp[2], 2) if bp else '',
                   box_market_price=bp[4] if bp else '', box_product=bp[5] if bp else '',
                   msrp_box=round(msrp, 2) if msrp else '',
                   ev_to_price=round(ev * packs / price, 3) if price else '',
                   real_to_price=round(st.mean(rvs) / price, 3) if price else '',
                   p_box_beats_price=round(p_beat, 3) if p_beat is not None else '',
                   p_box_beats_price_realizable=round(p_beat_real, 3) if p_beat_real is not None else '',
                   box_p10=round(mvs[int(.1 * len(mvs))], 2), box_median=round(st.median(mvs), 2), box_p90=round(mvs[int(.9 * len(mvs))], 2),
                   price_coverage=round(cov, 3))
        rows.append(row)
        print(f"{code:16} EV/pack ${ev:6.2f}  EV/box ${ev*packs:8.2f}  real/box ${st.mean(rvs):8.2f}  price {price}  ratio {row['ev_to_price']}  P(beat) {row['p_box_beats_price']}  cov {cov:.2f}")
        for i, v in enumerate(sim):
            if i % 10 == 0: sim_rows.append(dict(product=code, box_value=round(v[0], 2), realizable=round(v[1], 2), cards_over_20=v[2]))
        for sn, (sev, scov) in sheets.items():
            cov_rows.append(dict(product=code, sheet=sn, expected_cards=round(expc.get(sn, 0), 4), ev_per_card=round(sev, 3), coverage=round(scov, 3)))

    with open(os.path.join(OUT, 'set_summary.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT, 'box_sim.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(sim_rows[0].keys())); w.writeheader(); w.writerows(sim_rows)
    with open(os.path.join(OUT, 'coverage.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(cov_rows[0].keys())); w.writeheader(); w.writerows(cov_rows)

    # chase cards: top 8 by price per set among booster cards
    chase = []
    bys = collections.defaultdict(list)
    for (s, cn), r in prices.items():
        if r['booster'] == '1' and r['usd']:
            bys[s].append((float(r['usd']), r['name'], cn, r['rarity']))
    for s in bys:
        for p, n, cn, r in sorted(bys[s], reverse=True)[:8]:
            chase.append(dict(set=s, name=n, cn=cn, rarity=r, usd=p))
    with open(os.path.join(OUT, 'chase_cards.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['set', 'name', 'cn', 'rarity', 'usd']); w.writeheader(); w.writerows(chase)
    return rows

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='MTG booster box EV model')
    ap.add_argument('--bulk-below', type=float, default=HAIRCUT['bulk_below'], help='cards priced below this count as $0 when cashing out')
    ap.add_argument('--mid-keep', type=float, default=HAIRCUT['mid_keep'], help='share of market price kept on cards between bulk-below and high-from')
    ap.add_argument('--high-keep', type=float, default=HAIRCUT['high_keep'], help='share of market price kept on cards at or above high-from')
    ap.add_argument('--high-from', type=float, default=HAIRCUT['high_from'])
    ap.add_argument('--boxes', type=int, default=N_BOXES, help='Monte Carlo boxes per product')
    a = ap.parse_args()
    HAIRCUT.update(bulk_below=a.bulk_below, mid_keep=a.mid_keep, high_keep=a.high_keep, high_from=a.high_from); N_BOXES = a.boxes
    main()
