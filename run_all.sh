#!/usr/bin/env bash
# rebuilds everything in results/ from data/. about 8 minutes on a laptop; the simulations are the slow part.
set -e
cd "$(dirname "$0")"
python3 ev_model.py "$@"      # results/set_summary.csv, box_sim.csv, coverage.csv, chase_cards.csv
python3 godpack_model.py      # results/godpack.csv, foil_scenarios.csv
python3 godpack_history.py    # results/godpack_history.csv + chart 11: god packs bolted onto every set since 2016 (~3 min)
python3 packs8000.py          # results/packs8000.csv + chart 13: 8,000 packs of every product, and the break-even pack price (~3 min)
python3 collector_cut.py      # results/collector_cut.csv + chart 12: the 2027 collector cut applied to every collector box since 2019
python3 charts.py             # results/charts/*.png
python3 fun_facts.py          # results/fun_facts.json: every number in the ad-lib bank (and the selling-time inputs)
python3 build_xlsx.py         # results/MTG_Booster_EV_Model.xlsx (open in Excel/LibreOffice to recalculate formulas)
python3 significance.py       # results/significance_*.csv (~4 min)
python3 verify.py             # compares results to the numbers claimed in the video
