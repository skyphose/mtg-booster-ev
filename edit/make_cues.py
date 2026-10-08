"""
builds cues_a.json (public cut) and cues_b.json (nerd cut).

a cue = "when i say <phrase>, show <asset>". phrases are copied from the script; the matcher is fuzzy, so small
ad-libs are fine, but the closer you stay to these lines the better. phrases avoid numbers on purpose (the
transcriber writes "$63" or "sixty-three" unpredictably).

types: insert (full-frame card that adds time) · endcard · broll (full screen, your face in a corner)
       callout / tag / lower / badge (png overlays on top of whatever is showing)
fields: anchor start|end of the phrase · offset seconds · dur seconds · until <cue id> (ends when that cue starts)
        max / min seconds
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

def C(id, phrase, type, asset, **kw): return dict(id=id, phrase=phrase, type=type, asset=asset, **kw)

COLD = [
    C('lower', 'i work at a game store', 'lower', 'lower_name.png', dur=5),
    C('six_cents', 'six cents', 'callout', 'callout_six_cents.png', dur=1.4, min_score=80),
    C('title', 'six cents', 'insert', 'card_title.png', same_as='six_cents', anchor='end', offset=0.9, dur=2.6),
]
A1 = [
    C('tag_p1', "here's what surprised me", 'tag', 'tag_p1.png', dur=4),
    C('chart01', 'take every play booster box since', 'broll', '01_play_boxes_ev_vs_price.png', until='box_worth', max=30),
    C('ratio_127', 'of cards in it for every dollar the box sells for', 'callout', 'callout_ratio_127.png', dur=4),
    C('box_worth', 'so the box is worth more than it costs', 'mark', ''),
]
A2 = [
    C('tag_p2', "here's one box of reality fracture", 'tag', 'tag_p2.png', dur=4),
    C('anim_box', "here's one box of reality fracture", 'broll', 'anim_open_a_box.mp4', same_as='tag_p2', until='anim_hist', max=24),
    C('bulk_396', 'of them are under a dollar', 'callout', 'callout_bulk_396.png', dur=4),
    C('anim_hist', 'same product simulated boxes', 'broll', 'anim_histogram.mp4', until='chart04', max=16, min_score=65),
    C('cash_46', 'cents on the dollar', 'callout', 'callout_cash_46.png', dur=4),
    C('chart04', 'i did that for every set', 'broll', '04_p_box_beats_price.png', until='anim_tiers', max=25),
    C('one_in_100', 'pays for itself in cash', 'callout', 'callout_one_in_100.png', dur=4),
    C('anim_tiers', 'nobody puts in the thumbnail', 'broll', 'anim_where_the_ev_sits.mp4', until='plastic', max=14),
    C('hours', 'about five hours of work', 'callout', 'callout_hours.png', dur=5),
    C('plastic', "the money's gone when you crack the plastic", 'mark', ''),
    C('chart02', 'the median collector box sells for about one and a half', 'broll', '02_collector_boxes_ev_vs_price.png', until='tag_p3', max=20),
]
A3 = [
    C('tag_p3', "this isn't a bad set problem", 'tag', 'tag_p3.png', dur=4),
    C('anim_years', "this isn't a bad set problem", 'broll', 'anim_ten_years.mp4', same_as='tag_p3', until='tag_p4', max=16),
]
A4 = [
    C('tag_p4', 'now the god pack', 'tag', 'tag_p4.png', dur=4),
    C('chart05', 'now the god pack', 'broll', '05_godpack_value_and_odds.png', same_as='tag_p4', until='anim_god', max=25),
    C('gp_63', 'if the celebration card is good', 'callout', 'callout_gp_63.png', dur=4),
    C('six_cents_2', 'of the pack price', 'callout', 'callout_six_cents.png', dur=3),
    C('anim_god', 'chance of having one', 'broll', 'anim_godpack_odds.mp4', anchor='start', offset=-1.2, until='avg', max=16),
    C('gp_23', 'if you want a coin flip at seeing one', 'callout', 'callout_gp_23.png', dur=4),
    C('avg', 'is the average', 'mark', '', min_score=70),
    C('gp_50', 'the median one is', 'callout', 'callout_gp_50.png', dur=5),
]
A5 = [
    C('tag_p5', 'same post two paragraphs down', 'tag', 'tag_p5.png', dur=4),
    C('chart07', 'price per card goes up', 'broll', '07_collector_shrink.png', offset=-2.5, until='chart06', max=20),
    C('shrink', 'price per card goes up', 'callout', 'callout_shrink.png', same_as='chart07', dur=4),
    C('net_80', 'your collector booster got about', 'callout', 'callout_net_80.png', dur=4),
    C('chart06', 'it comes down to one number wizards', 'broll', '06_foil_change_breakeven.png', until='tag_p6', max=25),
    C('foil_85', 'if the new rate is better than one in', 'callout', 'callout_foil_85.png', dur=5),
]
A6 = [
    C('tag_p6', 'one thing from my side of the counter', 'tag', 'tag_p6.png', dur=4),
    C('chart08', 'one thing from my side of the counter', 'broll', '08_store_economics.png', same_as='tag_p6', until='verdict', max=25),
    C('verdict', 'buy singles for the deck', 'callout', 'callout_verdict.png', dur=5),
    C('repo', 'public github repo', 'badge', 'badge_repo.png', dur=60),
]
END = [C('end', '', 'endcard', 'card_end.png', dur=6)]

cues_a = COLD + A1 + A2 + A3 + A4 + A5 + A6 + END

# ---------------------------------------------------------------- nerd cut: same spine, extra beats in between
B_COLD_EXTRA = [C('repo_early', 'public github repo in the description', 'badge', 'badge_repo.png', dur=8)]
B1 = [
    C('tag_b1', 'three ingredients', 'tag', 'tag_b1.png', dur=4),
    C('chart01_xc', 'a tracker that runs the same kind of math', 'broll', '01_play_boxes_ev_vs_price.png', max=10),
]
B2_EXTRA = [C('chart01_ub', 'look at the bottom of this chart', 'broll', '01_play_boxes_ev_vs_price.png', until='b_crossover', max=20),
            C('b_crossover', 'the box carries the premium', 'mark', '')]
B3_EXTRA = [
    C('anim_tiers_b', 'now the thing the haircut hides', 'broll', 'anim_where_the_ev_sits.mp4', until='b_trap', max=14),
    C('hours_b', 'call it five hours', 'callout', 'callout_hours.png', dur=5),
    C('b_trap', "here's the sunk cost trap", 'mark', ''),
]
B4_EXTRA = [
    C('chart03', "caveat about the left side of this chart", 'broll', '03_ten_years_ev_ratio.png', until='b_sig', max=40),
    C('b_sig', "significance since someone's gonna ask", 'broll', '09_box_distribution_fra.png', max=12),
    C('wilcoxon', 'treat each set as one data point', 'callout', 'callout_wilcoxon.png', dur=6),
    C('coin_flip', "the one thing that isn't significant", 'callout', 'callout_coin_flip.png', dur=6),
]
B5_EXTRA = [C('chart05_b', 'the contents are published the values are mine', 'broll', '05_godpack_value_and_odds.png', max=25)]
B6 = [C('chart06_b', 'solve for break even', 'broll', '06_foil_change_breakeven.png', max=20)]
B7 = [C('tag_b7', 'two foil commons and one foil uncommon', 'tag', 'tag_b7.png', dur=4),
      C('chart07_b', 'two foil commons and one foil uncommon', 'broll', '07_collector_shrink.png', same_as='tag_b7', max=25)]
B8 = [C('chart08_b', 'the margin chain', 'broll', '08_store_economics.png', max=30)]

cues_b = (COLD + B_COLD_EXTRA + B1 + A1 + B2_EXTRA + A2 + B3_EXTRA + A3 + B4_EXTRA
          + A4 + B5_EXTRA + A5 + B6 + B7 + A6 + B8 + END)
# the nerd cut numbers its parts differently, so the script-a part tags get swapped for nerd-cut ones at the same spots
TAG_B = {'tag_p1': 'b2', 'tag_p2': 'b3', 'tag_p3': 'b4', 'tag_p4': 'b5', 'tag_p5': 'b6', 'tag_p6': 'b8'}
cues_b = [dict(c, id='tag_' + TAG_B[c['id']], asset=f"tag_{TAG_B[c['id']]}.png") if c['id'] in TAG_B else c for c in cues_b]
SAME = {k: 'tag_' + v for k, v in TAG_B.items()}  # same_as pointers follow the rename
cues_b = [dict(c, same_as=SAME.get(c['same_as'], c['same_as'])) if c.get('same_as') else c for c in cues_b]

for name, cues in (('cues_a.json', cues_a), ('cues_b.json', cues_b)):
    ids = [c['id'] for c in cues]; assert len(ids) == len(set(ids)), name
    json.dump(cues, open(os.path.join(HERE, name), 'w'), indent=1); print(name, len(cues), 'cues')
