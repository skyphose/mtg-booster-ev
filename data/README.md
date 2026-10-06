# Data files

| File | What it is | Source and terms |
|---|---|---|
| `sealed_basic_data.json` | Booster structure for every set: which card sheets a pack draws from, how many cards from each, and each card's weight on its sheet. This is how Wizards' published "Collecting <set>" odds become card-level probabilities. | [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data) (data behind [mtg.wtf](https://mtg.wtf)), MIT. Snapshot 2026-10-05. |
| `scryfall_prices.psv` | One row per printing for the sets used: set, collector number, rarity, USD price (non-foil, foil, etched), whether it appears in boosters, promo/frame flags, name. Prices are TCGplayer market prices as republished by Scryfall. | [Scryfall bulk data](https://scryfall.com/docs/api/bulk-data), default-cards file of 2026-10-05. Free to use; Scryfall asks for attribution and that you do not hammer their servers. Refresh with `scripts/fetch_prices.py`. |
| `tcg_sealed_products.psv` | TCGplayer sealed product ids for each set's booster boxes/displays/packs, with the market price and lowest listing at pull time. | Read from TCGplayer's own site on 2026-10-05 (`scripts/fetch_tcg_sales.js`). |
| `tcg_sealed_sales.psv`, `tcg_sealed_sales_extra.psv` | The 5 most recent completed sales per box product: date, price, shipping, quantity, condition, language. The model uses the median price. | Same. These are the "Latest Sales" TCGplayer shows on every product page; the public view is capped at 5 per product. |

Not in this repo, on purpose: the store invoice and point-of-sale export behind the store-economics section. Those figures appear in the workbook and video only rounded up to the nearest $10 and with no store or distributor named.

Column format is pipe-separated (`|`) because card names contain commas.
