#!/usr/bin/env bash
# Rebuild every result from the data in data/. About 5 minutes on a laptop (the Monte Carlo is the slow part).
set -e
cd "$(dirname "$0")"
python3 ev_model.py "$@"      # results/set_summary.csv, box_sim.csv, coverage.csv, chase_cards.csv
python3 godpack_model.py      # results/godpack.csv, foil_scenarios.csv
python3 charts.py             # results/charts/*.png
python3 build_xlsx.py         # results/MTG_Booster_EV_Model.xlsx (open in Excel/LibreOffice to recalculate formulas)
python3 verify.py             # compares results to the numbers claimed in the video
