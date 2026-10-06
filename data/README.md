# data

| file | what it is | where it came from |
|---|---|---|
| `sealed_basic_data.json` | how every booster is built: which card sheets a pack draws from, how many cards from each, and each card's weight on its sheet. this is how wizards' published "collecting <set>" odds become card-level probabilities. | [taw/magic-sealed-data](https://github.com/taw/magic-sealed-data) (the data behind [mtg.wtf](https://mtg.wtf)), mit. snapshot 2026-10-05. |
| `scryfall_prices.psv` | one row per printing for the sets i used: set, collector number, rarity, usd price (non-foil, foil, etched), whether it shows up in boosters, promo/frame flags, name. prices are tcgplayer market as republished by scryfall. | [scryfall bulk data](https://scryfall.com/docs/api/bulk-data), default-cards file of 2026-10-05. free to use; scryfall asks for credit and that you don't hammer them. refresh with `scripts/fetch_prices.py`. |
| `tcg_sealed_products.psv` | tcgplayer product ids for each set's booster boxes, displays and packs, with market price and lowest listing at pull time. | read from tcgplayer's own site on 2026-10-05 (`scripts/fetch_tcg_sales.js`). |
| `tcg_sealed_sales.psv`, `tcg_sealed_sales_extra.psv` | the 5 most recent completed sales per box product: date, price, shipping, quantity, condition, language. the model uses the median price. | same. these are the "latest sales" tcgplayer shows on every product page; the public view stops at 5. |

not in here, on purpose: the store invoice and point-of-sale export behind the store-economics section. those show up in the workbook and the video only rounded up to the nearest $10 with no store or distributor named.

files are pipe-separated (`|`) because card names have commas in them.
