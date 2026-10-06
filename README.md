# Is opening Magic boosters +EV? Ten years of boxes, and what the 2027 god packs change

This repository is the model behind the video. Everything the video claims is reproducible from the files here, and `verify.py` re-checks the headline numbers against the results. If you think a number is wrong, the fastest way to show it is to change an input and re-run.

**Headline results (prices as of 2026-10-05):**

| Claim | Number |
|---|---|
| Median 2024-26 Play Booster box: value of the cards at TCGplayer market ÷ what the box actually sells for | **1.27×** (range 0.85× to 1.70×) |
| Same boxes, if you sell everything (bulk at $0, $1-5 cards at 50%, $5+ at 70%) | **46¢ per dollar** |
| Chance a single box pays for itself in cash (4,000 simulated boxes per set) | **about 1%** for the median set; best case Murders at Karlov Manor, 11% |
| Median Collector Booster box, cards at market ÷ box price | **0.58×** |
| Value of a 2027 Booster Pack god pack (14 rares/mythics, Reality Fracture prices) | **about $63** |
| What that adds to the EV of one $5.49 pack at 1 in 1,000 | **$0.06** (1% of MSRP); $1.70 per box |
| Foil change: break-even for Wizards' unpublished new foil-rare rate | **1 in 8.5 packs** (today: 1 in 13) |
| Collector Booster: 15 → 12 cards at the same $26.99 | **+25% per card**; about −$1.02 of EV per pack |

## Reproduce it

```bash
pip install -r requirements.txt
./run_all.sh                      # ~5 minutes; writes results/ and runs verify.py
python3 ev_model.py --help        # change the cash-out haircut or the Monte Carlo size
python3 scripts/fetch_prices.py   # pull today's prices from Scryfall and re-run on them
```

Outputs land in `results/`: `set_summary.csv` (one row per box product), `box_sim.csv` (simulated boxes), `godpack.csv` and `foil_scenarios.csv`, ten charts, and `MTG_Booster_EV_Model.xlsx` with every lever as an editable cell.

## How the model works

1. **Pack structure.** Wizards publishes slot-by-slot odds for every set in its "Collecting <set>" articles. `data/sealed_basic_data.json` (from [mtg.wtf](https://mtg.wtf) via [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data)) encodes those as card-level weights: each booster variant, each sheet it draws from, how many cards from each sheet, and each printing's weight on its sheet. Reality Fracture's Play Booster alone has 109 sheets.
2. **Prices.** Scryfall's bulk file carries TCGplayer market price for every printing, foil and non-foil. Market price is TCGplayer's smoothed estimate of recent sale prices, not a listing price. Cards with no listed price fall back to a bulk value ($0.03-0.25 by rarity); the share of sheet weight with a real price is reported per product (`price_coverage`, median 98%).
3. **Box price.** The median of the five most recent *completed* TCGplayer sales for each box product. TCGplayer's own "market price" and lowest listing are kept only as a cross-check. If nobody paid it, it is not the price.
4. **EV.** For each pack: sum over slots of (expected cards from the sheet) × (weighted mean price of the sheet). Box EV = pack EV × packs per box (36 for Draft and 2024 Play Boosters, 30 for Set and 2025+ Play Boosters, 12 for Collector). A Monte Carlo of 4,000 boxes per product gives the spread and the probability that a box beats its price.
5. **Cash-out.** What you net if you sell every card: cards under $1 are bulk and count as $0; $1-5 cards net 50% (marketplace fees, shipping, buylist spread); $5+ cards net 70%. These are levers (`--bulk-below`, `--mid-keep`, `--high-keep`). At a generous 80% on everything over $1 the median box still returns 57¢.
6. **God packs and the foil change** (`godpack_model.py`) use Reality Fracture's sheets as the proxy for Nauctis: the god pack is 10 default-frame rares/mythics + 2 non-foil Booster Fun + 2 foil Booster Fun (+ a celebration card, valued at $0 by default); the Collector god pack is a foil land + 3 foil rares/mythics + 3 non-foil Booster Fun + 5 foil Booster Fun. The foil change is modelled as: foil commons/uncommons removed from the foil slot, a foil rare/mythic at rate *p*, a plain common/uncommon otherwise; the break-even *p* is solved for.

## What this model does not do, and why

- **It uses today's prices, not day-one prices.** New-set singles typically fall 30% or more in their first three months ([MTGStocks, Aetherdrift](https://www.mtgstocks.com/news/17099-checking-in-on-aetherdrift-prices)). Anyone opening on release day does worse than these numbers.
- **It does not model sealed appreciation.** Boxes from 2016-2019 are priced today as collectibles, so their EV/price ratio describes the sealed premium, not launch economics. The argument about opening rests on 2024-2026 products.
- **Five sales per box is a thin sample.** TCGplayer's public view stops at five. The five were tightly clustered for nearly every product (min/max are in `set_summary.csv`); illiquid products like LotR Collector can swing.
- **Sell-through is assumed, not measured.** The Selling Time tab in the workbook uses 60% of listings selling within 90 days; no public per-card sell-through data exists. It is a yellow cell.
- **The god pack values are generous.** Reality Fracture was three days old when prices were pulled; the foil Booster Fun sheet average ($16) includes shattered-mirror and serialized treatments that will not be in a god pack (capped at $100 per card it is $13).
- **Store figures are rounded and anonymized.** The store-economics section comes from one independent store's launch order, rounded up to the nearest $10, with no store or distributor named. The raw files are not in this repo.

## Is it statistically significant?

`significance.py` separates four sources of uncertainty (results in `results/significance_*.csv`):

| Source | Test | Result |
|---|---|---|
| Monte Carlo noise | one-sample t-test, simulated boxes vs box price, per product | not the binding uncertainty: every 2024-26 product has \|t\| > 5; cash-out value is below price for all 32 products with p < 10⁻⁶ |
| Box price from only 5 sales | bootstrap the 5 sales, recompute ratio and P(box beats price) | 95% intervals are narrow because the 5 sales cluster (e.g. Reality Fracture Play box market ratio 1.37-1.38; Final Fantasy Play, the widest, 0.90-1.06) |
| Card-price measurement error | lognormal noise, σ = 20% per printing, 300 redraws | median Play Booster market ratio 1.27-1.34, cash-out 0.45-0.49; in 300/300 draws the median set is above 1 at market and below 1 in cash. A *systematic* overstatement of all card prices would need to exceed 21% to pull the market ratio under 1; no plausible bias rescues the cash-out ratio |
| Across sets (is it the population, not this sample?) | Wilcoxon signed-rank and exact sign test on log(ratio), one observation per set | Play Boosters above break-even at market: 14 of 16 sets, Wilcoxon p = 2×10⁻⁴. Below break-even in cash: 16 of 16, p = 1.5×10⁻⁵. Collector boxes below break-even at market: 33 of 33, p = 3×10⁻⁷. Draft boxes at market: no significant direction (median 0.99) |

God pack spread (20,000 simulated god packs): mean $64, **median $50**, 10th-90th percentile $23-$106, 1% above $400. Half of all god packs will be worth less than $50; the mean is pulled up by the two foil Booster Fun slots.

## Independent cross-check

[TableTopMeta](https://www.tabletopmeta.com/ev) runs the same kind of calculation with live prices. On the day of the pull: Foundations $265 vs this model's $266; Aetherdrift $171 vs $166; Modern Horizons 3 $417 vs $385; Final Fantasy Collector $722 vs $831.

## Sources

Official: [Updating Our Boosters in 2027](https://magic.wizards.com/en/news/announcements/updating-our-boosters-in-2027) · [WPN: 2027 booster changes for retailers](https://wpn.wizards.com/en/news/2027-booster-changes-for-wpn-retailers) · [Collecting Reality Fracture](https://magic.wizards.com/en/news/feature/collecting-reality-fracture) · [Magic returns to listing MSRP](https://magic.wizards.com/en/news/announcements/magic-returns-to-listing-msrp-with-foundations) · Collecting [Avatar](https://magic.wizards.com/en/news/feature/collecting-avatar-the-last-airbender), [Spider-Man](https://magic.wizards.com/en/news/feature/collecting-marvels-spider-man), [The Hobbit](https://magic.wizards.com/en/news/feature/collecting-the-hobbit), [Secrets of Strixhaven](https://magic.wizards.com/en/news/feature/collecting-secrets-of-strixhaven).
Data: [Scryfall bulk data](https://scryfall.com/docs/api/bulk-data) · [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data) · TCGplayer latest sales.
Context: [Draftsim](https://draftsim.com/mtg-2027-booster-pack-changes/) · [MTG Rocks](https://mtgrocks.com/mtg-god-pack-announcement/) · [GameSpot](https://www.gamespot.com/articles/magic-the-gathering-has-a-price-problem-and-its-sabotaging-universes-beyond/1100-6533484/) · [Kotaku](https://kotaku.com/magic-the-gathering-adding-god-packs-2000740004) · [TCGTalk on Pokémon god pack odds](https://tcgtalk.com/guides/ascended-heroes-pull-rates-god-pack).

## Found a mistake?

Open an issue with the product, the number you got, and the input you changed. Pull requests that add sets, swap in a different price source, or tighten the cash-out model are welcome. Code is MIT; data terms are in `data/README.md`.
