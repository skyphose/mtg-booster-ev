# is opening magic boosters +EV? ten years of boxes, and what god packs change

this is the model behind the video. i work at a game store and i order, sell, and watch people open these boxes every week. i also have a stats degree i don't use enough, so i built the thing properly: official pack odds, real card prices, real completed box sales, and a monte carlo on top. every number i say in the video comes out of this repo, and `verify.py` re-checks all of them. if you think i'm wrong, don't argue in the comments, change an input and run it.

## the short version (prices as of 2026-10-05)

| what i checked | what i got |
|---|---|
| median 2024-26 play booster box: cards at tcgplayer market ÷ what the box actually sells for | **1.35×** (range 0.92× to 1.70×). on paper, you win. |
| same boxes if you actually sell everything (bulk = $0, $1-5 cards at 50%, $5+ at 70%) | **49¢ on the dollar** |
| chance one box pays for itself in cash (4,000 simulated boxes per set) | **about 1 in 70** for the typical set. karlov manor is the best at 11%. |
| median collector booster box, cards at market ÷ box price | **0.62×**. under water even on paper, all 33 of them. |
| a 2027 booster-pack god pack (14 rares/mythics, reality fracture prices) | **mean $65, median $51.** about half of them are under fifty bucks. |
| what that adds to a $5.49 pack at 1 in 1,000 | **six cents.** $1.74 on a box. |
| the foil change: break-even for the new foil-rare rate wizards hasn't published yet | **about 1 in 8 packs** (today it's about 1 in 12) |
| collector boosters: 15 cards → 12 at the same $26.99 | **+25% per card**, about -$1.07 of ev per pack |

## run it yourself

```bash
pip install -r requirements.txt
./run_all.sh                      # ~8 minutes. writes results/ and runs verify.py at the end
python3 ev_model.py --help        # change the cash-out haircut or the number of simulated boxes
python3 scripts/fetch_prices.py   # pull today's prices from scryfall and re-run on them
python3 fun_facts.py              # every one-liner i drop in the video (odds of the top pull, how many rares are bulk, ...)
```

everything lands in `results/`: `set_summary.csv` (one row per box product), `box_sim.csv` (simulated boxes), `godpack.csv`, `foil_scenarios.csv`, the `significance_*.csv` files, ten charts, and `MTG_Booster_EV_Model.xlsx` with every assumption as a cell you can edit. `fun_facts.json` is every side fact from the video, and verify.py checks those too.

## animations

`animations.py` renders five short mp4 clips (1080p, 30 fps, dark) straight from the model, so the motion graphics in the video are the data, not an illustration of it: a box opening pack by pack with running market vs cash totals, 4,000 boxes dropping into a histogram, the god-pack odds curve filling in as you buy packs, 420 cards sorting into price tiers, and ten years of boxes appearing year by year. `python3 animations.py` (about 5 minutes; needs ffmpeg) writes them to `results/animations/`.

## the edit

`edit/` is how the video itself got cut. i read the script to camera, and `edit/edit.py` transcribes it, finds the cue lines, cuts retakes and dead air, and drops the charts and animations in at the right words. details and the recording checklist are in [`edit/README.md`](edit/README.md).

## how it works

1. **pack structure.** wizards publishes slot-by-slot odds in its "collecting <set>" articles (2019 on; for older draft boosters the odds are mtg.wtf's estimates). `data/sealed_basic_data.json` (from [mtg.wtf](https://mtg.wtf) via [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data)) turns those into card-level weights: every booster variant, every sheet it pulls from, how many cards from each sheet, and each printing's weight on the sheet. reality fracture's play booster alone is 109 sheets.
2. **card prices.** scryfall's bulk file carries tcgplayer market price for every printing, foil and non-foil. market price is tcgplayer's smoothed estimate of what things actually sold for, not a listing price. a card with no price falls back to bulk ($0.03-0.25 by rarity); how much of each product had a real price is in `price_coverage` (median 100%). double-faced cards are listed as `100a` in the sheet data and `100` on scryfall, and the model matches them up (an earlier version didn't, which priced every double-faced card as bulk; fixed 2026-10-08).
3. **box price.** the median of the five most recent *completed* tcgplayer sales for that box. not "market price," not the cheapest listing. if nobody paid it, it isn't the price.
4. **ev.** per pack: for each slot, expected cards from that sheet × the sheet's weighted average price. per box: × packs (36 for draft and 2024 play boosters, 30 for set and 2025+ play boosters, 12 collector). then 4,000 simulated boxes per product for the spread and the odds a box beats its price.
5. **cash-out.** what you net if you sell every card. under $1 is bulk and counts as zero. $1-5 you keep half (fees, shipping, buylist spread). $5+ you keep 70%. these are flags (`--bulk-below`, `--mid-keep`, `--high-keep`). even at a very generous 80% on everything over a dollar, the median box gives back 60¢, and the best (modern horizons 3) 93¢. you'd have to keep 90% of every $1+ card for a single box (mh3) to clear a dollar.
6. **god packs and the foil change** (`godpack_model.py`) use reality fracture's sheets as the stand-in for nauctis. god pack = 10 default-frame rares/mythics + 2 non-foil booster fun + 2 foil booster fun (+ a celebration card, which i value at $0 because nobody's seen it). collector god pack = foil land + 3 foil rares/mythics + 3 non-foil booster fun + 5 foil booster fun. the foil change: foil commons/uncommons leave the foil slot, a foil rare/mythic shows up at some rate *p*, a plain card otherwise. i solve for the *p* where pack ev doesn't move.

## is it statistically significant?

yes, and the one place it isn't is worth saying out loud. `significance.py` pulls apart four different uncertainties instead of hiding behind "4,000 simulations":

| what could be wrong | how i tested it | what happened |
|---|---|---|
| monte carlo noise | one-sample t-test, simulated boxes vs box price, per product | not the problem. 15 of 16 play boxes sit above price on paper at t > 5 (the hobbit sits below); cash-out is below price for all 32 products at p < 10⁻⁶ |
| the box price is only 5 sales | bootstrap the 5 sales, recompute everything 2,000 times | intervals are tight because the 5 sales cluster. reality fracture play box: 1.41-1.42 at market, 0.48 cash. widest is final fantasy play at 1.02-1.20, which is why i call that one "about break-even on paper" |
| tcgplayer prices are estimates | lognormal noise, σ = 20% on every printing, 300 redraws | median play ratio 1.34-1.41 at market, 0.48-0.52 in cash. 300 of 300 redraws keep the median set above 1 on paper and below 1 in cash. a *systematic* bias would have to be over 25% to pull the market ratio under 1. nothing plausible rescues the cash number |
| is this the product, or just these 16 sets? | wilcoxon signed-rank + exact sign test on log(ratio), one observation per set | play boosters above 1 at market: 15 of 16, p = 5×10⁻⁵. below 1 in cash: 16 of 16, p = 1.5×10⁻⁵. collector boxes below 1 at market: 33 of 33, p = 3×10⁻⁷. **draft boxes 2016-23 at market: not significant** (17 of 31 above 1, median 1.05, p = 0.54). coin flip. |

god packs have a spread, not a value: 20,000 simulated god packs give a mean of $66, a median of $51, 10th-90th percentile $25-$107, and 1% over $400. the average gets dragged up by the two foil booster fun slots.

## what this doesn't do, so you don't have to tell me

- **release-week prices for reality fracture.** it came out three days before the price pull, and new-set prices fall: aetherdrift's two top mythics lost nearly half their value and its collector boxes about a third in under three months ([mtgstocks](https://www.mtgstocks.com/news/17099-checking-in-on-aetherdrift-prices)). nobody publishes a clean set-wide number for singles, so i don't put one on it. older sets are priced today, months or years after release.
- **no sealed-appreciation model.** a 2017 box is priced today as a collectible, so its ratio is about the sealed premium, not about cracking it. the opening argument is the 2024-26 rows.
- **five sales is thin.** that's what tcgplayer shows without a login. the min/max of the five are in `set_summary.csv` so you can see how tight they are.
- **sell-through is a guess.** the selling-time tab assumes 60% of listings sell in 90 days. nobody publishes that number. it's a yellow cell, change it.
- **collector ev leans on a few huge foils.** on some collector boxes, up to 29% of the ev comes from cards priced at $300+ (march of the machine, final fantasy), and those prices come from thin markets. if they're too high, collector boxes look even worse, so this cuts in my favor, but it's why the simulated *median* box sits well under the mean.
- **five sales is thin.** for reality fracture (play and collector) and foundations play, the five sales look like one seller's listing bought out on one day. they line up with tcgplayer market and retail prices, so i kept them, but it's really one data point. shipping isn't included in box prices (adding it moves the play median by about 0.03×).
- **the sheet data isn't perfect.** aetherdrift's play booster rare slot gives borderless rares about twice the share wizards publishes (16% vs 8%). fixing it moves that box by about 6 cents, so i left the data as-is. the simulation draws cards with replacement inside a sheet, which doesn't change ev and barely touches the spread.
- **god pack values are generous.** reality fracture was three days old when i pulled prices, and the foil booster fun sheet average ($16) includes japan showcase fracture foils and other rare treatments wizards hasn't said can show up in a god pack (cap any card at $100 and it's $13; drop the japan showcase cards and the god pack is about $54 instead of $65).
- **store numbers are rounded and anonymous.** the store-economics bits come from one independent store's launch order, rounded up to the nearest $10, no store or distributor named. the raw files are not here and won't be.

## did someone else get the same answer?

[tabletopmeta](https://www.tabletopmeta.com/ev) does the same kind of math with live prices, and it agrees with me within about 1% on most sets (foundations, aetherdrift, bloomburrow, edge of eternities, lorwyn). that's not independent confirmation: it looks like it uses the same scryfall prices and booster data, and it still matches my *old* numbers on sets with lots of double-faced cards (final fantasy collector: $829 there, $1,001 here after the fix), so it probably has the same double-faced-card gap mine had.

## sources

official: [updating our boosters in 2027](https://magic.wizards.com/en/news/announcements/updating-our-boosters-in-2027) · [wpn: 2027 booster changes for retailers](https://wpn.wizards.com/en/news/2027-booster-changes-for-wpn-retailers) · [collecting reality fracture](https://magic.wizards.com/en/news/feature/collecting-reality-fracture) · [magic returns to listing msrp](https://magic.wizards.com/en/news/announcements/magic-returns-to-listing-msrp-with-foundations) · collecting [avatar](https://magic.wizards.com/en/news/feature/collecting-avatar-the-last-airbender), [spider-man](https://magic.wizards.com/en/news/feature/collecting-marvels-spider-man), [the hobbit](https://magic.wizards.com/en/news/feature/collecting-the-hobbit), [secrets of strixhaven](https://magic.wizards.com/en/news/feature/collecting-secrets-of-strixhaven)
data: [scryfall bulk data](https://scryfall.com/docs/api/bulk-data) · [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data) · tcgplayer latest sales
context: [draftsim](https://draftsim.com/mtg-2027-booster-pack-changes/) · [mtg rocks](https://mtgrocks.com/mtg-god-pack-announcement/) · [gamespot](https://www.gamespot.com/articles/magic-the-gathering-has-a-price-problem-and-its-sabotaging-universes-beyond/1100-6533484/) · [kotaku](https://kotaku.com/magic-the-gathering-adding-god-packs-2000740004) · [tcgtalk on pokémon god pack odds](https://tcgtalk.com/guides/ascended-heroes-pull-rates-god-pack)

## found something?

open an issue with the product, the number you got, and the input you changed. prs that add sets, swap the price source, or make the cash-out model smarter are welcome. if you find a play booster box that returns a dollar in cash, i'll put it in a video. i don't think you will.

code is mit. data terms are in `data/README.md`.
