# is opening magic boosters +EV? ten years of boxes, and what god packs change

this is the model behind the video. i work at a game store and i order, sell, and watch people open these boxes every week. i also have a stats degree i don't use enough, so i built the thing properly: official pack odds, real card prices, real completed box sales, and a monte carlo on top. every number i say in the video comes out of this repo, and `verify.py` re-checks all of them. if you think i'm wrong, don't argue in the comments, change an input and run it.

## the short version (prices as of 2026-10-05)

| what i checked | what i got |
|---|---|
| median 2024-26 play booster box: cards at tcgplayer market ÷ what the box actually sells for | **1.27×** (range 0.85× to 1.70×). on paper, you win. |
| same boxes if you actually sell everything (bulk = $0, $1-5 cards at 50%, $5+ at 70%) | **46¢ on the dollar** |
| chance one box pays for itself in cash (4,000 simulated boxes per set) | **about 1%** for the typical set. karlov manor is the best at 11%. |
| median collector booster box, cards at market ÷ box price | **0.58×**. under water even on paper. |
| a 2027 booster-pack god pack (14 rares/mythics, reality fracture prices) | **mean $63, median $50.** half of them are under fifty bucks. |
| what that adds to a $5.49 pack at 1 in 1,000 | **six cents.** $1.70 on a box. |
| the foil change: break-even for the new foil-rare rate wizards hasn't published yet | **1 in 8.5 packs** (today it's 1 in 13) |
| collector boosters: 15 cards → 12 at the same $26.99 | **+25% per card**, about -$1.02 of ev per pack |

## run it yourself

```bash
pip install -r requirements.txt
./run_all.sh                      # ~8 minutes. writes results/ and runs verify.py at the end
python3 ev_model.py --help        # change the cash-out haircut or the number of simulated boxes
python3 scripts/fetch_prices.py   # pull today's prices from scryfall and re-run on them
```

everything lands in `results/`: `set_summary.csv` (one row per box product), `box_sim.csv` (simulated boxes), `godpack.csv`, `foil_scenarios.csv`, the `significance_*.csv` files, ten charts, and `MTG_Booster_EV_Model.xlsx` with every assumption as a cell you can edit.

## how it works

1. **pack structure.** wizards publishes slot-by-slot odds for every set in the "collecting <set>" articles. `data/sealed_basic_data.json` (from [mtg.wtf](https://mtg.wtf) via [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data)) turns those into card-level weights: every booster variant, every sheet it pulls from, how many cards from each sheet, and each printing's weight on the sheet. reality fracture's play booster alone is 109 sheets.
2. **card prices.** scryfall's bulk file carries tcgplayer market price for every printing, foil and non-foil. market price is tcgplayer's smoothed estimate of what things actually sold for, not a listing price. a card with no price falls back to bulk ($0.03-0.25 by rarity); how much of each product had a real price is in `price_coverage` (median 98%).
3. **box price.** the median of the five most recent *completed* tcgplayer sales for that box. not "market price," not the cheapest listing. if nobody paid it, it isn't the price.
4. **ev.** per pack: for each slot, expected cards from that sheet × the sheet's weighted average price. per box: × packs (36 for draft and 2024 play boosters, 30 for set and 2025+ play boosters, 12 collector). then 4,000 simulated boxes per product for the spread and the odds a box beats its price.
5. **cash-out.** what you net if you sell every card. under $1 is bulk and counts as zero. $1-5 you keep half (fees, shipping, buylist spread). $5+ you keep 70%. these are flags (`--bulk-below`, `--mid-keep`, `--high-keep`). even at a very generous 80% on everything over a dollar, the median box gives back 57¢.
6. **god packs and the foil change** (`godpack_model.py`) use reality fracture's sheets as the stand-in for nauctis. god pack = 10 default-frame rares/mythics + 2 non-foil booster fun + 2 foil booster fun (+ a celebration card, which i value at $0 because nobody's seen it). collector god pack = foil land + 3 foil rares/mythics + 3 non-foil booster fun + 5 foil booster fun. the foil change: foil commons/uncommons leave the foil slot, a foil rare/mythic shows up at some rate *p*, a plain card otherwise. i solve for the *p* where pack ev doesn't move.

## is it statistically significant?

yes, and the one place it isn't is worth saying out loud. `significance.py` pulls apart four different uncertainties instead of hiding behind "4,000 simulations":

| what could be wrong | how i tested it | what happened |
|---|---|---|
| monte carlo noise | one-sample t-test, simulated boxes vs box price, per product | not the problem. every 2024-26 product has \|t\| > 5; cash-out is below price for all 32 products at p < 10⁻⁶ |
| the box price is only 5 sales | bootstrap the 5 sales, recompute everything 2,000 times | intervals are tight because the 5 sales cluster. reality fracture play box: 1.37-1.38 at market, 0.46-0.47 cash. widest is final fantasy play at 0.90-1.06, which is why i call that one "about break-even on paper" |
| tcgplayer prices are estimates | lognormal noise, σ = 20% on every printing, 300 redraws | median play ratio 1.27-1.34 at market, 0.45-0.49 in cash. 300 of 300 redraws keep the median set above 1 on paper and below 1 in cash. a *systematic* bias would have to be over 21% to pull the market ratio under 1. nothing plausible rescues the cash number |
| is this the product, or just these 16 sets? | wilcoxon signed-rank + exact sign test on log(ratio), one observation per set | play boosters above 1 at market: 14 of 16, p = 2×10⁻⁴. below 1 in cash: 16 of 16, p = 1.5×10⁻⁵. collector boxes below 1 at market: 33 of 33, p = 3×10⁻⁷. **draft boxes 2016-23 at market: not significant** (15 of 31 above 1, median 0.99). coin flip. |

god packs have a spread, not a value: 20,000 simulated god packs give a mean of $64, a median of $50, 10th-90th percentile $23-$106, and 1% over $400. the average gets dragged up by the two foil booster fun slots.

## what this doesn't do, so you don't have to tell me

- **today's prices, not launch prices.** new-set singles usually drop 30%+ in the first three months ([mtgstocks on aetherdrift](https://www.mtgstocks.com/news/17099-checking-in-on-aetherdrift-prices)). if you opened on release day you did worse than this.
- **no sealed-appreciation model.** a 2017 box is priced today as a collectible, so its ratio is about the sealed premium, not about cracking it. the opening argument is the 2024-26 rows.
- **five sales is thin.** that's what tcgplayer shows without a login. the min/max of the five are in `set_summary.csv` so you can see how tight they are.
- **sell-through is a guess.** the selling-time tab assumes 60% of listings sell in 90 days. nobody publishes that number. it's a yellow cell, change it.
- **god pack values are generous.** reality fracture was three days old when i pulled prices, and the foil booster fun sheet average ($16) includes shattered-mirror and serialized stuff that won't be in a god pack (cap any card at $100 and it's $13).
- **store numbers are rounded and anonymous.** the store-economics bits come from one independent store's launch order, rounded up to the nearest $10, no store or distributor named. the raw files are not here and won't be.

## did someone else get the same answer?

[tabletopmeta](https://www.tabletopmeta.com/ev) does the same kind of math with live prices. same day: foundations $265 vs my $266, aetherdrift $171 vs $166, modern horizons 3 $417 vs $385, final fantasy collector $722 vs $831.

## sources

official: [updating our boosters in 2027](https://magic.wizards.com/en/news/announcements/updating-our-boosters-in-2027) · [wpn: 2027 booster changes for retailers](https://wpn.wizards.com/en/news/2027-booster-changes-for-wpn-retailers) · [collecting reality fracture](https://magic.wizards.com/en/news/feature/collecting-reality-fracture) · [magic returns to listing msrp](https://magic.wizards.com/en/news/announcements/magic-returns-to-listing-msrp-with-foundations) · collecting [avatar](https://magic.wizards.com/en/news/feature/collecting-avatar-the-last-airbender), [spider-man](https://magic.wizards.com/en/news/feature/collecting-marvels-spider-man), [the hobbit](https://magic.wizards.com/en/news/feature/collecting-the-hobbit), [secrets of strixhaven](https://magic.wizards.com/en/news/feature/collecting-secrets-of-strixhaven)
data: [scryfall bulk data](https://scryfall.com/docs/api/bulk-data) · [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data) · tcgplayer latest sales
context: [draftsim](https://draftsim.com/mtg-2027-booster-pack-changes/) · [mtg rocks](https://mtgrocks.com/mtg-god-pack-announcement/) · [gamespot](https://www.gamespot.com/articles/magic-the-gathering-has-a-price-problem-and-its-sabotaging-universes-beyond/1100-6533484/) · [kotaku](https://kotaku.com/magic-the-gathering-adding-god-packs-2000740004) · [tcgtalk on pokémon god pack odds](https://tcgtalk.com/guides/ascended-heroes-pull-rates-god-pack)

## found something?

open an issue with the product, the number you got, and the input you changed. prs that add sets, swap the price source, or make the cash-out model smarter are welcome. if you find a play booster box that returns a dollar in cash, i'll put it in a video. i don't think you will.

code is mit. data terms are in `data/README.md`.
