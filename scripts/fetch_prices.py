"""
Refresh data/scryfall_prices.psv from Scryfall's bulk data (so the model can be re-run on today's prices).

    python3 scripts/fetch_prices.py            # downloads default-cards (~80 MB gz), filters to the sets the model uses
    python3 scripts/fetch_prices.py --keep-gz  # keep the downloaded archive next to the output

Scryfall's prices are TCGplayer market prices (USD) refreshed daily. Bulk files are free to use with attribution:
https://scryfall.com/docs/api/bulk-data
"""
import argparse, gzip, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(os.path.dirname(HERE), 'data')
SETS = set('''fra frc plst spg neo snc ltr ltc one onc afr afc lci lcc khm khc dmu dmc znr znc zne mom moc mul vow voc mid mic woe woc wot bro brc brr
mh3 m3c h2r stx sta stc fin fic fca tdm tdc fdn mkm mkc dft drc dsk dsc tla tlc tle ecl ecc blb blc eoe eoc eos otj otc otp big sos soc soa iko c20 m21
hob hoc eld spm spe mar thb c21 nec ncc slx leg rex bot ala soi emn kld aer akh hou xln rix dom m19 grn rna war m20 pls om1 tmt'''.split())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--keep-gz', action='store_true'); a = ap.parse_args()
    req = urllib.request.Request('https://api.scryfall.com/bulk-data/default-cards', headers={'User-Agent': 'mtg-booster-ev/1.0', 'Accept': 'application/json'})
    meta = json.load(urllib.request.urlopen(req))
    uri = meta.get('jsonl_download_uri')
    if not uri:
        sys.exit('Scryfall no longer offers a JSONL bulk file; adapt this script to the JSON array in meta["download_uri"].')
    print('downloading', uri, f"({meta.get('compressed_size', 0)/1e6:.0f} MB, updated {meta['updated_at']})")
    gz = os.path.join(DATA, 'default-cards.jsonl.gz')
    urllib.request.urlretrieve(uri, gz)
    out = os.path.join(DATA, 'scryfall_prices.psv'); n = k = 0
    opener = gzip.open if uri.endswith('.gz') else open
    with opener(gz, 'rt', encoding='utf-8') as f, open(out, 'w', encoding='utf-8') as o:
        o.write('set|cn|rarity|usd|usd_foil|usd_etched|booster|promo_types|frame_effects|border|released|name\n')
        for line in f:
            n += 1
            c = json.loads(line)
            if c.get('set') not in SETS: continue
            p = c.get('prices') or {}; k += 1
            o.write('|'.join([c['set'], c['collector_number'], c['rarity'][0], p.get('usd') or '', p.get('usd_foil') or '', p.get('usd_etched') or '',
                              '1' if c.get('booster') else '0', ','.join(c.get('promo_types') or []), ','.join(c.get('frame_effects') or []),
                              c.get('border_color', ''), c.get('released_at', ''), c['name'].replace('|', '/')]) + '\n')
    if not a.keep_gz: os.remove(gz)
    print(f'read {n} cards, kept {k} -> {out}')
    print('Prices as of', meta['updated_at'], '- note the date in your results.')

if __name__ == '__main__':
    main()
