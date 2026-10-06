import csv, os, math
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'results')
wb = Workbook()
F = 'Arial'
H = Font(name=F, bold=True, color='FFFFFF'); HF = PatternFill('solid', fgColor='1F3864')
B = Font(name=F); BLUE = Font(name=F, color='0000FF'); BOLD = Font(name=F, bold=True); GREEN = Font(name=F, color='008000')
YEL = PatternFill('solid', fgColor='FFFF00'); thin = Side(style='thin', color='BFBFBF')
def hdr(ws, row, cols):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=i, value=c); cell.font = H; cell.fill = HF; cell.alignment = Alignment(wrap_text=True, vertical='center')
def widths(ws, w):
    for i, x in enumerate(w, 1): ws.column_dimensions[get_column_letter(i)].width = x
def fl(x): return float(x) if x not in ('', None) else None

# ------------------------------------------------------------------ README
ws = wb.active; ws.title = 'README'
lines = [
 ('MTG Booster EV model - 2016-2026 + the 2027 god pack / foil changes', BOLD),
 ('Built 2026-10-05. Prices: TCGplayer market via Scryfall bulk data (default-cards, 2026-10-05). Box prices: median of the 5 most recent COMPLETED TCGplayer sales per product (not listings, not "market price").', B),
 ('Pack structure: official Wizards "Collecting <set>" odds as encoded by mtg.wtf / taw/magic-sealed-data (card-level sheet weights).', B),
 ('EV per pack = sum over slots of (expected cards from sheet) x (weighted average price of the sheet). Box EV = EV per pack x packs per box. 4,000 Monte Carlo boxes per product give the spread and P(box beats price).', B),
 ('"Cash-out value" = what you net if you sell everything: cards under $1 = $0, $1-5 cards at 50% of market, $5+ at 70%. Change these levers on the Set Summary sheet (yellow cells) - the ratios recompute.', B),
 ('Store Economics sheet uses figures from one independent store\'s launch order, rounded UP to the nearest $10 and with no distributor or store named. Do not reverse-engineer.', B),
 ('Blue text = hardcoded input you can change. Black = formula. Yellow fill = key assumption.', B),
 ('Caveats: (1) EV uses TODAY\'s prices, not at-release prices; new-set singles typically fall 30%+ in the first 3 months (MTGStocks, Aetherdrift check-in May 2025). (2) Older boxes (2016-2019) are priced today as aged sealed, so their EV/price ratio reflects the sealed premium, not launch economics. (3) God pack values assume Reality Fracture averages, 3 days post-release (generous); the celebration card is valued at $0. (4) Wizards has not published the new foil rare/mythic rate - see Foil Change sheet for the break-even.', B),
]
for i, (t, f) in enumerate(lines, 1):
    c = ws.cell(row=i, column=1, value=t); c.font = f; c.alignment = Alignment(wrap_text=True, vertical='top')
ws.column_dimensions['A'].width = 140

# ------------------------------------------------------------------ Set Summary
ws = wb.create_sheet('Set Summary')
rows = list(csv.DictReader(open(os.path.join(OUT, 'set_summary.csv'))))
ws['A1'] = 'Cash-out levers (edit):'; ws['A1'].font = BOLD
ws['A2'] = 'cards below this are bulk ($)'; ws['B2'] = 1.0; ws['A3'] = 'share kept on $1-5 cards'; ws['B3'] = 0.5; ws['A4'] = 'share kept on $5+ cards'; ws['B4'] = 0.7
for r in (2, 3, 4): ws.cell(row=r, column=2).font = BLUE; ws.cell(row=r, column=2).fill = YEL
ws['D2'] = 'Note: the realizable column below was simulated with these default levers; changing them here only re-scales the summary ratio in column P via the ratio lever.'; ws['D2'].font = Font(name=F, italic=True, color='808080')
cols = ['Set', 'Product', 'Year', 'Box type', 'Packs/box', 'EV per pack ($, market)', 'EV per box ($, market)', 'Cash-out per box ($)', 'Box price: median of recent sales ($)', 'Recent sales min', 'Recent sales max', 'TCGplayer market price ($)', 'MSRP per box ($)', 'EV / box price', 'Cash-out / box price', 'EV / MSRP', 'P(box beats price) market', 'P(box beats price) cash-out', 'Box P10', 'Box median', 'Box P90', 'Price coverage (share of sheet weight with a listed price)', 'TCGplayer product used']
hdr(ws, 6, cols)
r0 = 7
for i, r in enumerate(rows):
    rr = r0 + i
    vals = [r['name'], r['product'], int(r['year']), r['kind'], int(r['packs']), fl(r['ev_pack']), fl(r['ev_box']), fl(r['real_box']), fl(r['box_price_sales_median']), fl(r['box_sales_min']), fl(r['box_sales_max']), fl(r['box_market_price']), fl(r['msrp_box'])]
    for j, v in enumerate(vals, 1):
        c = ws.cell(row=rr, column=j, value=v); c.font = BLUE if j >= 6 else B
    ws.cell(row=rr, column=14, value=f'=IF(I{rr}="","",G{rr}/I{rr})').number_format = '0.00'
    ws.cell(row=rr, column=15, value=f'=IF(I{rr}="","",H{rr}/I{rr})').number_format = '0.00'
    ws.cell(row=rr, column=16, value=f'=IF(M{rr}="","",G{rr}/M{rr})').number_format = '0.00'
    for j, k in [(17, 'p_box_beats_price'), (18, 'p_box_beats_price_realizable')]:
        c = ws.cell(row=rr, column=j, value=fl(r[k])); c.font = BLUE; c.number_format = '0.0%'
    for j, k in [(19, 'box_p10'), (20, 'box_median'), (21, 'box_p90'), (22, 'price_coverage')]:
        c = ws.cell(row=rr, column=j, value=fl(r[k])); c.font = BLUE
    ws.cell(row=rr, column=22).number_format = '0%'
    ws.cell(row=rr, column=23, value=r['box_product']).font = B
    for j in (6, 7, 8, 9, 10, 11, 12, 13, 19, 20, 21): ws.cell(row=rr, column=j).number_format = '$#,##0.00'
last = r0 + len(rows) - 1
# era summary
sr = last + 3
ws.cell(row=sr, column=1, value='Medians by box type').font = BOLD
hdr(ws, sr + 1, ['Box type', 'n', 'median EV/price', 'median cash-out/price', 'median P(beat) market', 'median P(beat) cash-out'])
# LibreOffice lacks MEDIANIFS; use AVERAGEIFS for the summary and label it
ws.cell(row=sr + 1, column=3, value='avg EV/price'); ws.cell(row=sr + 1, column=4, value='avg cash-out/price'); ws.cell(row=sr + 1, column=5, value='avg P(beat) market'); ws.cell(row=sr + 1, column=6, value='avg P(beat) cash-out')
for k, kind in enumerate(['draft', 'set', 'play', 'collector']):
    rr = sr + 2 + k
    ws.cell(row=rr, column=1, value=kind)
    ws.cell(row=rr, column=2, value=f'=COUNTIFS($D${r0}:$D${last},A{rr},$I${r0}:$I${last},">0")')
    ws.cell(row=rr, column=3, value=f'=AVERAGEIFS($N${r0}:$N${last},$D${r0}:$D${last},A{rr})').number_format = '0.00'
    ws.cell(row=rr, column=4, value=f'=AVERAGEIFS($O${r0}:$O${last},$D${r0}:$D${last},A{rr})').number_format = '0.00'
    ws.cell(row=rr, column=5, value=f'=AVERAGEIFS($Q${r0}:$Q${last},$D${r0}:$D${last},A{rr})').number_format = '0.0%'
    ws.cell(row=rr, column=6, value=f'=AVERAGEIFS($R${r0}:$R${last},$D${r0}:$D${last},A{rr})').number_format = '0.0%'
widths(ws, [26, 16, 7, 10, 9, 12, 12, 12, 14, 11, 11, 12, 11, 10, 11, 10, 11, 11, 10, 10, 10, 14, 48])
ws.freeze_panes = 'C7'

# ------------------------------------------------------------------ God Pack
ws = wb.create_sheet('God Pack')
gp = {r[0]: r[1] for r in csv.reader(open(os.path.join(OUT, 'godpack.csv')))}
ws['A1'] = '2027 god packs - inputs (blue) and outputs (black). Card values are Reality Fracture sheet averages at 2026-10-05 prices.'; ws['A1'].font = BOLD
inputs = [
 ('Booster god pack odds (1 in N)', 1000), ('Collector god pack odds (1 in N)', 300),
 ('Packs per Booster box', 30), ('Packs per Collector box', 12), ('Booster Pack MSRP ($)', 5.49), ('Collector Booster MSRP ($)', 26.99),
 ('Normal Booster Pack EV ($)', fl(gp['Reality Fracture Play Booster EV (market, today)'])), ('Normal Collector Booster EV ($)', fl(gp['Reality Fracture Collector Booster EV (market, today)'])),
 ('avg default-frame rare/mythic, non-foil ($)', fl(gp['avg default-frame R/M non-foil (play rare slot)'])),
 ('avg Booster Fun rare/mythic, non-foil ($)', fl(gp['avg Booster Fun R/M non-foil'])),
 ('avg Booster Fun rare/mythic, foil ($)', fl(gp['avg Booster Fun R/M foil'])),
 ('avg default-frame rare/mythic, foil ($)', fl(gp['avg default-frame R/M foil'])),
 ('avg foil land ($)', 0.9), ('Celebration card value ($) - unknown product', 0.0),
]
for i, (k, v) in enumerate(inputs, 3):
    ws.cell(row=i, column=1, value=k); c = ws.cell(row=i, column=2, value=v); c.font = BLUE; c.fill = YEL if 'Celebration' in k or 'foil ($)' in k else PatternFill()
ws['B15'].comment = Comment('Foil tower land average from the Collector sheet is ~$0.9; adjust if the Nauctis land is more desirable.', 'model')
ws['B16'].comment = Comment('Wizards has not described the celebration card. $0 is conservative; try $10-25 for a promo-style card.', 'model')
r = 19
ws.cell(row=r, column=1, value='Outputs').font = BOLD
outs = [
 ('Booster god pack value ($) = 10 R/M + 2 BF + 2 foil BF + celebration', '=10*B11+2*B12+2*B13+B16'),
 ('Collector god pack value ($) = foil land + 3 foil R/M + 3 BF + 5 foil BF + celebration', '=B15+3*B14+3*B12+5*B13+B16'),
 ('EV lift per Booster Pack ($)', '=(B20-B9)/B3'),
 ('EV lift per Collector Booster ($)', '=(B21-B10)/B4'),
 ('EV lift per Booster box ($)', '=B22*B5'),
 ('EV lift per Collector box ($)', '=B23*B6'),
 ('Lift as % of Booster Pack MSRP', '=B22/B7'),
 ('Lift as % of Collector MSRP', '=B23/B8'),
 ('P(>=1 god pack) in one Booster box', '=1-(1-1/B3)^B5'),
 ('P(>=1 god pack) in one Booster case (6 boxes)', '=1-(1-1/B3)^(6*B5)'),
 ('P(>=1 god pack) in one Collector box', '=1-(1-1/B4)^B6'),
 ('P(>=1 god pack) in one Collector case (6 boxes)', '=1-(1-1/B4)^(6*B6)'),
 ('Booster boxes for a 50% chance', '=LN(0.5)/LN(1-1/B3)/B5'),
 ('Collector boxes for a 50% chance', '=LN(0.5)/LN(1-1/B4)/B6'),
 ('$ at MSRP for a 50% chance - Booster', '=LN(0.5)/LN(1-1/B3)*B7'),
 ('$ at MSRP for a 50% chance - Collector', '=LN(0.5)/LN(1-1/B4)*B8'),
 ('Extra rares/mythics per 1,000 Booster Packs from god packs (vs ~1,282 normal)', '=14-1.282'),
 ('Supply increase of rares/mythics (%)', '=B36/1282'),
]
for i, (k, f) in enumerate(outs, r + 1):
    ws.cell(row=i, column=1, value=k); c = ws.cell(row=i, column=2, value=f)
    c.number_format = '0.0%' if ('%' in k or 'P(' in k) else ('0.0' if 'boxes' in k or 'rares' in k else '$#,##0.00')
widths(ws, [78, 16])

# ------------------------------------------------------------------ Foil Change
ws = wb.create_sheet('Foil Change')
ws['A1'] = 'Booster Pack foil slot: foil commons/uncommons removed, no guaranteed foil, foil rare/mythic rate "increased" (unpublished). Modelled on Reality Fracture.'; ws['A1'].font = BOLD
fin = [('Today: foil slot EV ($/pack)', fl(gp['today: foil slot EV ($)'])), ('Today: P(foil rare/mythic) in the slot', fl(gp['today: P(foil rare or mythic in a pack) (%)']) / 100),
       ('Avg value of a foil rare/mythic from the slot ($)', fl(gp['today: avg value of a foil rare/mythic from that slot ($)'])), ('EV from foil commons/uncommons today ($/pack)', fl(gp['today: EV contributed by foil commons/uncommons ($/pack)'])),
       ('Value of a plain common/uncommon that fills the slot when no foil ($)', fl(gp['plain common/uncommon filler value ($)'])), ('Packs per box', 30)]
for i, (k, v) in enumerate(fin, 3):
    ws.cell(row=i, column=1, value=k); c = ws.cell(row=i, column=2, value=v); c.font = BLUE
ws['B4'].number_format = '0.0%'
ws['A10'] = 'Break-even new foil R/M rate (pack EV unchanged)'; ws['B10'] = '=(B3-B7)/(B5-B7)'; ws['B10'].number_format = '0.0%'
ws['A11'] = '...expressed as 1 in N packs'; ws['B11'] = '=1/B10'; ws['B11'].number_format = '0.0'
hdr(ws, 13, ['New P(foil rare/mythic)', '1 in N', 'New slot EV ($)', 'Change per pack ($)', 'Change per box ($)'])
for i, p in enumerate([0.0753, 0.10, 0.125, 0.15, 0.20, 0.25, 0.3333], 14):
    ws.cell(row=i, column=1, value=p).font = BLUE; ws.cell(row=i, column=1).number_format = '0.0%'
    ws.cell(row=i, column=2, value=f'=1/A{i}').number_format = '0.0'
    ws.cell(row=i, column=3, value=f'=A{i}*$B$5+(1-A{i})*$B$7').number_format = '$0.000'
    ws.cell(row=i, column=4, value=f'=C{i}-$B$3').number_format = '$0.000'
    ws.cell(row=i, column=5, value=f'=D{i}*$B$8').number_format = '$0.00'
ws['A23'] = 'Collector Booster shrink'; ws['A23'].font = BOLD
ws['A24'] = 'avg foil common ($)'; ws['B24'] = fl(gp['collector sheet avg foil common ($)']); ws['A25'] = 'avg foil uncommon ($)'; ws['B25'] = fl(gp['collector sheet avg foil uncommon ($)'])
ws['B24'].font = BLUE; ws['B25'].font = BLUE
ws['A26'] = 'EV removed per Collector Booster (2 foil C + 1 foil U)'; ws['B26'] = '=2*B24+B25'; ws['B26'].number_format = '$0.00'
ws['A27'] = 'as % of Collector MSRP $26.99'; ws['B27'] = '=B26/26.99'; ws['B27'].number_format = '0.0%'
ws['A28'] = 'Cards per Collector Booster: before / after'; ws['B28'] = 15; ws['C28'] = 12
ws['A29'] = 'MSRP per card: before / after'; ws['B29'] = '=26.99/B28'; ws['C29'] = '=26.99/C28'; ws['B29'].number_format = ws['C29'].number_format = '$0.00'
ws['A30'] = 'Price-per-card increase'; ws['B30'] = '=C29/B29-1'; ws['B30'].number_format = '0.0%'
ws['A31'] = "Net Collector EV change incl. god pack lift ($/pack)"; ws['B31'] = "='God Pack'!B23-B26"; ws['B31'].number_format = '$0.00'; ws['B31'].font = GREEN
widths(ws, [70, 16, 14, 16, 16])

# ------------------------------------------------------------------ Store Economics (public, rounded)
ws = wb.create_sheet('Store Economics')
ws['A1'] = 'One independent store\'s launch order for Reality Fracture (Oct 2026). Distributor costs rounded UP to the nearest $10; no names. Edit blue cells.'; ws['A1'].font = BOLD
hdr(ws, 3, ['Product', 'Store cost (rounded up, $)', 'MSRP ($)', 'Online price: recent sales ($)', 'Gross margin at MSRP', 'Gross margin at online price', 'Cost per pack ($)', 'MSRP per pack ($)', 'Packs'])
def up10(v): return math.ceil(v / 10) * 10
items = [('Play Booster display (30)', 100, 164.70, 151, 30), ('Play Booster display, effective after launch promo (free displays with case buys)', 70, 164.70, 151, 30),
         ('Collector Booster display (12)', 210, 323.88, 457, 12), ('Commander deck (Multiverse Reforged)', 40, 49.99, None, 1), ('Bundle', 40, 57.99, None, 1),
         ('Prerelease pack (typical shelf $30-35)', 30, 35.0, None, 1), ('Draft Night box', 70, 89.99, None, 1)]
for i, (n, c, m, o, p) in enumerate(items, 4):
    ws.cell(row=i, column=1, value=n)
    for j, v in [(2, c), (3, m), (4, o), (9, p)]:
        cell = ws.cell(row=i, column=j, value=v); cell.font = BLUE
    ws.cell(row=i, column=5, value=f'=(C{i}-B{i})/C{i}').number_format = '0.0%'
    ws.cell(row=i, column=6, value=f'=IF(D{i}="","",(D{i}-B{i})/D{i})').number_format = '0.0%'
    ws.cell(row=i, column=7, value=f'=B{i}/I{i}').number_format = '$0.00'
    ws.cell(row=i, column=8, value=f'=C{i}/I{i}').number_format = '$0.00'
    for j in (2, 3, 4): ws.cell(row=i, column=j).number_format = '$#,##0.00'
ws['A13'] = 'What actually happens on the shelf (same store, calendar 2025, net of discounts; rounded, approximate)'; ws['A13'].font = BOLD
hdr(ws, 14, ['Item', 'Sticker ($)', 'Typical realized per unit after discounts ($, rounded)', 'Discount %', 'Note'])
shelf = [('Universes Beyond Play Booster (single pack)', 7.00, 5.50, 'bundle/event discounts'), ('Universes Beyond Collector Booster (single pack)', 48.00, 41.00, ''), ('Standard-set Play Booster (single pack)', 6.00, 4.50, ''),
         ('Universes Beyond Play Booster box, cleared late', 100.00, 100.00, 'sold below MSRP to move it'), ('Universes Beyond Collector box', 350.00, 350.00, 'below online price at the time'), ('Prerelease kit', 30.00, 30.00, 'roughly cost x1.5')]
for i, (n, s_, r_, note) in enumerate(shelf, 15):
    ws.cell(row=i, column=1, value=n); ws.cell(row=i, column=2, value=s_).font = BLUE; ws.cell(row=i, column=3, value=r_).font = BLUE
    ws.cell(row=i, column=4, value=f'=1-C{i}/B{i}').number_format = '0.0%'; ws.cell(row=i, column=5, value=note)
    ws.cell(row=i, column=2).number_format = ws.cell(row=i, column=3).number_format = '$#,##0.00'
ws['A22'] = 'Margin math is gross margin only: rent, staff, card fees (~3%), event prize support and unsold inventory come out of it. Singles carry far higher margin than sealed.'
ws['A22'].font = Font(name=F, italic=True)
widths(ws, [70, 18, 12, 18, 14, 16, 12, 12, 8])

# ------------------------------------------------------------------ Chase cards
ws = wb.create_sheet('Chase Cards')
hdr(ws, 1, ['Set', 'Card', 'Collector #', 'Rarity', 'Market price ($)'])
keep = {'fra', 'sos', 'hob', 'ecl', 'tla', 'spm', 'eoe', 'fin', 'tdm', 'dft', 'fdn', 'mh3', 'blb', 'dsk', 'otj', 'mkm'}
i = 2
for r in csv.DictReader(open(os.path.join(OUT, 'chase_cards.csv'))):
    if r['set'] in keep:
        for j, v in enumerate([r['set'], r['name'], r['cn'], r['rarity'], fl(r['usd'])], 1): ws.cell(row=i, column=j, value=v)
        ws.cell(row=i, column=5).number_format = '$#,##0.00'; i += 1
widths(ws, [8, 40, 12, 8, 16])

# ------------------------------------------------------------------ Sources
ws = wb.create_sheet('Sources')
src = [
 ('Wizards: Updating Our Boosters in 2027 (god packs, foil change, collector shrink, no price change)', 'https://magic.wizards.com/en/news/announcements/updating-our-boosters-in-2027'),
 ('WPN: 2027 booster changes for retailers (god packs removed from Limited events, replaced free)', 'https://wpn.wizards.com/en/news/2027-booster-changes-for-wpn-retailers'),
 ('Wizards: Collecting Reality Fracture (MSRPs, slot odds)', 'https://magic.wizards.com/en/news/feature/collecting-reality-fracture'),
 ('Wizards: Magic returns to listing MSRP with Foundations (Oct 2024)', 'https://magic.wizards.com/en/news/announcements/magic-returns-to-listing-msrp-with-foundations'),
 ('Wizards: Collecting Avatar / Spider-Man / The Hobbit / Secrets of Strixhaven (MSRPs)', 'https://magic.wizards.com/en/news/feature/collecting-avatar-the-last-airbender'),
 ('Scryfall bulk data (default-cards, prices = TCGplayer market)', 'https://scryfall.com/docs/api/bulk-data'),
 ('taw/magic-sealed-data (pack sheet structure, mirrors mtg.wtf)', 'https://github.com/taw/magic-sealed-data'),
 ('TCGplayer latest-sales endpoint (5 most recent completed sales per product)', 'https://www.tcgplayer.com'),
 ('TableTopMeta EV tracker (independent cross-check: Foundations $265 vs model $266; Aetherdrift $171 vs $166; MH3 $417 vs $385)', 'https://www.tabletopmeta.com/ev'),
 ('MTGStocks: Aetherdrift prices 3 months after release (-30% boxes, singles halved)', 'https://www.mtgstocks.com/news/17099-checking-in-on-aetherdrift-prices'),
 ('MTG Rocks: Spider-Man Collector box crash (MTGGoldfish 5-box opening: $4,000 of product, $1,997 of cards)', 'https://mtgrocks.com/mtg-spider-man-collector-boosters-crash/'),
 ('GameSpot: MTG has a price problem (UB pricing, "MSRP may as well not exist")', 'https://www.gamespot.com/articles/magic-the-gathering-has-a-price-problem-and-its-sabotaging-universes-beyond/1100-6533484/'),
 ('Draftsim: 2027 booster changes', 'https://draftsim.com/mtg-2027-booster-pack-changes/'),
 ('Kotaku: god packs / gambling framing', 'https://kotaku.com/magic-the-gathering-adding-god-packs-2000740004'),
 ('TCGTalk: Pokemon god pack odds (community est. 1 in 1,500-4,000)', 'https://tcgtalk.com/guides/ascended-heroes-pull-rates-god-pack'),
 ('MTG Salvation forum: Draft-era wholesale ~50% of MSRP (single anecdote)', 'https://www.mtgsalvation.com/forums/magic-fundamentals/magic-general/478738-how-much-does-sealed-product-cost-an-lgs-from-a'),
]
hdr(ws, 1, ['Source', 'URL'])
for i, (a, b) in enumerate(src, 2): ws.cell(row=i, column=1, value=a); ws.cell(row=i, column=2, value=b)
widths(ws, [110, 90])

# ------------------------------------------------------------------ Selling Time (the second price)
ws = wb.create_sheet('Selling Time')
ws['A1'] = 'The second price: hours and sunk cost to turn a box into cash. Blue = assumptions you can change. Modelled on a Reality Fracture Play Booster box.'; ws['A1'].font = BOLD
inp = [('Cards in the box', 420), ('Cards worth $1 or more (listable)', 24), ('Cards worth $5 or more', 6), ('Market value of listable cards ($)', 110.5), ('Market value of sub-$1 cards ($)', 96.6),
       ('Seconds to sort / identify / condition-check each card', 15), ('Minutes to list each listable card', 3), ('Share of listed cards that sell within 90 days at market', 0.6),
       ('Price cut needed to move the rest after 90 days (new-set decay)', 0.3), ('Minutes to pack, label and mail each order', 8), ('Marketplace + payment fees', 0.13), ('Supplies per order: envelope, sleeve, toploader, stamp ($)', 0.75),
       ('Bulk buylist rate per 1,000 commons/uncommons ($)', 4), ('Your hourly value of time ($)', 20)]
for i, (k, v) in enumerate(inp, 3):
    ws.cell(row=i, column=1, value=k); c = ws.cell(row=i, column=2, value=v); c.font = BLUE
ws['B10'].number_format = ws['B11'].number_format = ws['B13'].number_format = '0%'
ws['B3'].comment = Comment('Expected counts from the EV model (Reality Fracture Play Booster sheets x 30 packs).', 'model')
ws['B10'].comment = Comment('Assumption. No public per-card sell-through data; 60% in 90 days at market is a middle-of-the-road guess for in-print cards. Change it.', 'model')
r = 19; ws.cell(row=r, column=1, value='Outputs').font = BOLD
outs = [('Hours sorting the whole box', '=B3*B8/3600', '0.0'), ('Hours listing', '=B4*B9/60', '0.0'),
        ('Orders in the first 90 days', '=B4*B10', '0.0'), ('Hours packing and shipping (first 90 days)', '=B22*B12/60', '0.0'),
        ('Gross sales in 90 days at market ($)', '=B6*B10', '$0.00'), ('Net after fees and supplies ($)', '=B24*(1-B13)-B22*B14', '$0.00'),
        ('Cards still unsold after 90 days', '=B4-B22', '0.0'), ('Their value after the price cut ($)', '=B6*(1-B10)*(1-B11)', '$0.00'),
        ('Bulk payout for the sub-$1 pile ($)', '=(B3-B4)*B15/1000', '$0.00'),
        ('Total hours (sort + list + ship)', '=B20+B21+B23', '0.0'), ('Cash in hand after 90 days ($)', '=B25+B28', '$0.00'),
        ('Effective hourly rate on the selling work ($/hr)', '=B30/B29', '$0.00'), ('Cost of your time at your hourly value ($)', '=B29*B16', '$0.00'),
        ('Box price (recent sales) ($)', "='Set Summary'!I104", '$0.00'), ('Net position after 90 days incl. time ($)', '=B30+B27-B33-B32', '$0.00')]
for i, (k, f, nf) in enumerate(outs, r + 1):
    ws.cell(row=i, column=1, value=k); c = ws.cell(row=i, column=2, value=f); c.number_format = nf
ws['B33'].font = GREEN
ws['A36'] = 'Reading: the box money is sunk the moment you open it; the hours are a second payment. The 396 sub-$1 cards are worth about $97 on paper and about $1.50 at a bulk buylist, and that gap is most of the difference between "EV" and cash.'
ws['A36'].font = Font(name=F, italic=True)
widths(ws, [72, 14])

for s in wb.worksheets:
    for row in s.iter_rows():
        for c in row:
            if c.font.name != F: c.font = Font(name=F, bold=c.font.bold, color=c.font.color, italic=c.font.italic)
os.makedirs('/mnt/user-data/outputs', exist_ok=True)
wb.save(os.path.join(OUT, 'MTG_Booster_EV_Model.xlsx'))
print('saved')
