"""
procedural animations for the video, rendered straight from the model. 1920x1080, 30 fps, dark, mp4 (h264).

    python3 animations.py            # all five, into results/animations/  (~5-8 min)
    python3 animations.py box hist   # just some

  box    - open one reality fracture box pack by pack; running "cards at market" vs "cash" totals against the box price
  hist   - 4,000 simulated boxes drop into a histogram; counters for how many beat the price on paper and in cash
  god    - buy packs one by one; the chance of a god pack creeps up while the dollars spent race ahead
  tiers  - 420 cards sort themselves into price tiers, then the dollars show where the "ev" actually sits
  years  - ten years of boxes appear year by year around the break-even line

needs ev_model.py results in results/ (run ev_model.py first) and ffmpeg on the path.
"""
import csv, os, sys, math, random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.ticker import FuncFormatter
from ev_model import BY_CODE, card_price, realizable, OUT, box_price

AN = os.path.join(OUT, 'animations'); os.makedirs(AN, exist_ok=True)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = '#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'
SURF, INK, INK2, MUTED, GRID, BASE = '#1a1a19', '#ffffff', '#c3c2b7', '#898781', '#2c2c2a', '#383835'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'text.color': INK, 'font.family': 'DejaVu Sans', 'font.size': 18, 'axes.titlesize': 26, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 1, 'axes.axisbelow': True, 'legend.frameon': False})
usd = FuncFormatter(lambda v, _: f'${v:,.0f}')
FPS = 30
def writer(): return FFMpegWriter(fps=FPS, codec='libx264', bitrate=8000, extra_args=['-pix_fmt', 'yuv420p', '-preset', 'medium'])
def fig(): return plt.subplots(figsize=(19.2, 10.8), dpi=100)
def ease(t): return 1 - (1 - t) ** 3   # ease-out cubic
def tier_color(p): return MUTED if p < 1 else (BLUE if p < 5 else (AQUA if p < 20 else YELLOW))

rows = list(csv.DictReader(open(os.path.join(OUT, 'set_summary.csv'))))
FRA_PRICE = box_price('fra', 'play')[0]

# ----------------------------------------------------------------------------- shared: draw one simulated box, card by card
def simulate_one_box(code, packs, seed):
    rng = random.Random(seed); x = BY_CODE[code]
    configs = [(b['weight'], b['sheets']) for b in x['boosters']]; cw = [c[0] for c in configs]
    samp = {n: (list(sh['cards'].keys()), list(sh['cards'].values()), sh.get('fixed', False)) for n, sh in x['sheets'].items()}
    out = []
    for _ in range(packs):
        cfg = rng.choices(configs, weights=cw)[0][1]; pack = []
        for s, k in cfg.items():
            keys, w, fixed = samp[s]
            picks = keys if fixed else rng.choices(keys, weights=w, k=k)
            pack += [card_price(p)[0] for p in picks]
        out.append(pack)
    return out

def anim_box(seconds=24):
    packs = simulate_one_box('fra-play', 30, seed=5)
    per_pack = FPS * seconds // 30
    frames = per_pack * 30 + FPS * 3
    f, (ax, side) = plt.subplots(1, 2, figsize=(19.2, 10.8), dpi=100, gridspec_kw={'width_ratios': [2.2, 1]})
    f.suptitle('opening one reality fracture box, pack by pack', x=0.02, ha='left', fontsize=28, fontweight='bold')
    ax.set_xlim(0, 30); ax.set_ylim(0, 260); ax.yaxis.set_major_formatter(usd); ax.set_xlabel('packs opened'); ax.grid(True)
    ax.axhline(FRA_PRICE, color=YELLOW, lw=2.5, ls='--'); ax.text(0.3, FRA_PRICE + 4, f'box price ${FRA_PRICE:.0f} (recent sales)', color=YELLOW, fontsize=17)
    lm, = ax.plot([], [], color=BLUE, lw=4, label='cards at market price'); lc, = ax.plot([], [], color=AQUA, lw=4, label='what you could cash out')
    ax.legend(loc='upper left', fontsize=17, bbox_to_anchor=(0, 0.93))
    side.set_xlim(0, 7); side.set_ylim(0, 14); side.axis('off'); side.set_title('this pack', fontsize=22)
    tiles = [side.add_patch(plt.Rectangle((i % 7 + 0.1, 13 - i // 7 * 1.3 - 1.1), 0.8, 1.1, color=SURF, ec=BASE)) for i in range(14)]
    labels = [side.text(i % 7 + 0.5, 13 - i // 7 * 1.3 - 0.55, '', ha='center', va='center', fontsize=13, color=INK) for i in range(14)]
    tm = side.text(0.1, 9.0, '', fontsize=22, color=BLUE, fontweight='bold'); tc = side.text(0.1, 8.2, '', fontsize=22, color=AQUA, fontweight='bold')
    note = side.text(0.1, 6.8, '', fontsize=16, color=INK2, wrap=True); legend_t = side.text(0.1, 0.4, 'grey < \\$1   blue \\$1-5   green \\$5-20   gold \\$20+', fontsize=14, color=MUTED)
    mv = np.cumsum([sum(p) for p in packs]); cv = np.cumsum([sum(realizable(v) for v in p) for p in packs])
    def upd(fr):
        k = min(fr // per_pack, 29); t = (fr % per_pack) / per_pack if fr < per_pack * 30 else 1.0
        shown = int(math.ceil(ease(min(1, t * 1.3)) * 14)) if fr < per_pack * 30 else 14
        pack = sorted(packs[k], reverse=True)
        for i, (tile, lab) in enumerate(zip(tiles, labels)):
            if i < shown and i < len(pack):
                tile.set_color(tier_color(pack[i])); lab.set_text(f'${pack[i]:.2f}' if pack[i] >= 1 else '')
            else: tile.set_color(SURF); lab.set_text('')
        xs = np.arange(0, k + 1); xs2 = np.concatenate([[0], xs + 1])[: k + 2]
        ym = np.concatenate([[0], mv[: k + 1]]); yc = np.concatenate([[0], cv[: k + 1]])
        if fr < per_pack * 30:  # interpolate the last segment
            ym = ym.copy(); yc = yc.copy(); ym[-1] = ym[-2] + (mv[k] - (mv[k - 1] if k else 0)) * ease(t); yc[-1] = yc[-2] + (cv[k] - (cv[k - 1] if k else 0)) * ease(t)
            xs2[-1] = k + ease(t)
        lm.set_data(xs2, ym); lc.set_data(xs2, yc)
        tm.set_text(f'market  ${ym[-1]:,.0f}'); tc.set_text(f'cash     ${yc[-1]:,.0f}')
        if fr >= per_pack * 30: note.set_text(f'30 packs. {int((mv[-1] > FRA_PRICE))*"on paper the box won." or "on paper the box lost."}\nin cash it returned ${cv[-1]:.0f} on a ${FRA_PRICE:.0f} box.')
        return [lm, lc, tm, tc, note, *tiles, *labels]
    a = FuncAnimation(f, upd, frames=frames, blit=False)
    a.save(os.path.join(AN, 'anim_open_a_box.mp4'), writer=writer()); plt.close(f); print('box done')

def anim_hist(seconds=16):
    sim = [float(r['box_value']) for r in csv.DictReader(open(os.path.join(OUT, 'box_sim.csv'))) if r['product'] == 'fra-play']
    simr = [float(r['realizable']) for r in csv.DictReader(open(os.path.join(OUT, 'box_sim.csv'))) if r['product'] == 'fra-play']
    n = len(sim); frames = FPS * seconds; hold = FPS * 3
    f, ax = fig(); ax.set_title('4,000 simulated boxes of the same product')
    bins = np.linspace(0, 350, 50)
    ax.set_xlim(0, 350); ax.set_ylim(0, 40); ax.xaxis.set_major_formatter(usd); ax.set_xlabel('value of one 30-pack box'); ax.set_ylabel('boxes')
    ax.axvline(FRA_PRICE, color=YELLOW, lw=3); ax.text(FRA_PRICE + 3, 37, f'box price ${FRA_PRICE:.0f}', color=YELLOW, fontsize=18)
    bm = ax.bar(bins[:-1], np.zeros(49), width=np.diff(bins), align='edge', color=BLUE, alpha=0.9, label='cards at market')
    bc = ax.bar(bins[:-1], np.zeros(49), width=np.diff(bins), align='edge', color=AQUA, alpha=0.9, label='cash-out value')
    ax.legend(loc='upper right', fontsize=18)
    cm = ax.text(0.98, 0.72, '', transform=ax.transAxes, ha='right', fontsize=22, color=BLUE, fontweight='bold')
    cc = ax.text(0.98, 0.64, '', transform=ax.transAxes, ha='right', fontsize=22, color=AQUA, fontweight='bold')
    cnt = ax.text(0.98, 0.80, '', transform=ax.transAxes, ha='right', fontsize=18, color=INK2)
    def upd(fr):
        k = int(ease(min(1, fr / (frames - hold))) * n)
        hm, _ = np.histogram(sim[:k], bins); hc, _ = np.histogram(simr[:k], bins)
        for r_, h in zip(bm, hm): r_.set_height(h)
        for r_, h in zip(bc, hc): r_.set_height(h)
        ax.set_ylim(0, max(40, hm.max() * 1.15 if k else 40))
        cnt.set_text(f'{k * 10:,} boxes' if k else '')
        if k:
            cm.set_text(f'beat the price on paper: {100 * np.mean(np.array(sim[:k]) > FRA_PRICE):.0f}%'); cc.set_text(f'beat the price in cash: {100 * np.mean(np.array(simr[:k]) > FRA_PRICE):.1f}%')
        return [*bm, *bc, cm, cc, cnt]
    a = FuncAnimation(f, upd, frames=frames, blit=False)
    a.save(os.path.join(AN, 'anim_histogram.mp4'), writer=writer()); plt.close(f); print('hist done')

def anim_god(seconds=16):
    frames = FPS * seconds; hold = FPS * 3; max_packs = 1000
    f, (g, ax) = plt.subplots(1, 2, figsize=(19.2, 10.8), dpi=100, gridspec_kw={'width_ratios': [1, 1.3]})
    f.suptitle('chasing a god pack at 1 in 1,000', x=0.02, ha='left', fontsize=28, fontweight='bold')
    g.set_xlim(0, 40); g.set_ylim(0, 25); g.axis('off')
    rng = random.Random(3); god_at = 693  # scripted: the "coin flip" pack
    cells = g.scatter([i % 40 + 0.5 for i in range(max_packs)], [i // 40 + 0.5 for i in range(max_packs)], s=55, marker='s', c=[SURF] * max_packs, edgecolors=GRID, linewidths=0.4)
    ax.set_xlim(0, max_packs); ax.set_ylim(0, 100); ax.set_xlabel('packs opened'); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%')); ax.set_ylabel('chance you have seen at least one')
    xs = np.arange(0, max_packs + 1); ys = 100 * (1 - (1 - 1 / 1000) ** xs)
    ln, = ax.plot([], [], color=YELLOW, lw=4); ax.axhline(50, color=INK2, ls='--', lw=1.5)
    for p, lab in [(30, '1 box'), (180, '1 case')]: ax.axvline(p, color=GRID, lw=1); ax.text(p + 6, 66, lab, color=INK2, fontsize=15)
    t1 = ax.text(0.03, 0.9, '', transform=ax.transAxes, fontsize=22, fontweight='bold'); t2 = ax.text(0.03, 0.83, '', transform=ax.transAxes, fontsize=20, color=INK2)
    t3 = ax.text(0.03, 0.76, '', transform=ax.transAxes, fontsize=20, color=YELLOW)
    def upd(fr):
        k = int(ease(min(1, fr / (frames - hold))) * max_packs)
        cols = [BLUE] * k + [SURF] * (max_packs - k)
        if k > god_at: cols[god_at] = YELLOW
        cells.set_color(cols); ln.set_data(xs[: k + 1], ys[: k + 1])
        t1.set_text(f'{k:,} packs   =   {k / 30:.1f} boxes'); t2.set_text(f'${k * 5.49:,.0f} at msrp'); t3.set_text(f'chance of a god pack so far: {ys[k]:.0f}%' + ('   there it is. about $63.' if k > god_at else ''))
        return [cells, ln, t1, t2, t3]
    a = FuncAnimation(f, upd, frames=frames, blit=False)
    a.save(os.path.join(AN, 'anim_godpack_odds.mp4'), writer=writer()); plt.close(f); print('god done')

def anim_tiers(seconds=14):
    packs = simulate_one_box('fra-play', 30, seed=5); cards = sorted([v for p in packs for v in p])
    n = len(cards); frames = FPS * seconds; hold = FPS * 3
    tiers = [('under $1', lambda p: p < 1), ('$1-5', lambda p: 1 <= p < 5), ('$5-20', lambda p: 5 <= p < 20), ('$20+', lambda p: p >= 20)]
    cols = [MUTED, BLUE, AQUA, YELLOW]
    # target positions: columns of dots per tier
    tx = []; ty = []; tc = []
    counters = [0, 0, 0, 0]
    for v in cards:
        ti = next(i for i, (_, fn) in enumerate(tiers) if fn(v)); c = counters[ti]; counters[ti] += 1
        tx.append(ti * 4 + 1 + (c % 10) * 0.28); ty.append(1 + (c // 10) * 0.28); tc.append(cols[ti])
    tx, ty = np.array(tx), np.array(ty)
    rng = np.random.default_rng(1); sx = rng.uniform(0.5, 15.5, n); sy = rng.uniform(8, 13.5, n)
    f, ax = fig(); ax.set_xlim(0, 16); ax.set_ylim(0, 14); ax.axis('off'); ax.set_title('one box, 420 cards, sorted by what they are worth')
    sc = ax.scatter(sx, sy, s=60, c=[INK2] * n)
    labs = [ax.text(i * 4 + 2.3, 0.5, name, ha='center', fontsize=20, color=cols[i]) for i, (name, _) in enumerate(tiers)]
    cnts = [ax.text(i * 4 + 2.3, 0.0, '', ha='center', fontsize=17, color=INK2) for i in range(4)]
    vals = [sum(v for v in cards if fn(v)) for _, fn in tiers]
    msg = ax.text(8, 13.3, '', ha='center', fontsize=22, color=INK)
    def upd(fr):
        t = ease(min(1, fr / (frames - hold)))
        sc.set_offsets(np.c_[sx + (tx - sx) * t, sy + (ty - sy) * t]); sc.set_color(tc if t > 0.5 else [INK2] * n)
        for i, c in enumerate(cnts): c.set_text(f'{int(counters[i] * t)} cards  ·  ${vals[i] * t:,.0f}')
        if fr > frames - hold: msg.set_text(f'{counters[0]} of {n} cards are under a dollar. together: ${vals[0]:.0f} on paper, about $1.50 at bulk.')
        return [sc, *cnts, msg]
    a = FuncAnimation(f, upd, frames=frames, blit=False)
    a.save(os.path.join(AN, 'anim_where_the_ev_sits.mp4'), writer=writer()); plt.close(f); print('tiers done')

def anim_years(seconds=16):
    pts = [r for r in rows if r['ev_to_price']]
    kinds = {'draft': ('draft booster box', BLUE), 'set': ('set booster box', ORANGE), 'play': ('play booster box', AQUA), 'collector': ('collector box', MAGENTA)}
    rng = random.Random(3); data = [(int(r['year']) + rng.uniform(-0.18, 0.18), float(r['ev_to_price']), kinds[r['kind']][1], int(r['year'])) for r in pts]
    frames = FPS * seconds; hold = FPS * 3
    f, ax = fig(); ax.set_title('ten years of boxes: cards at market ÷ what the box sells for')
    ax.set_xlim(2015.5, 2026.6); ax.set_ylim(0, 1.9); ax.set_xticks(range(2016, 2027)); ax.axhline(1, color=INK2, ls='--', lw=2)
    ax.text(2015.6, 1.03, 'break-even', color=INK2, fontsize=16)
    for k, (lab, col) in kinds.items(): ax.scatter([], [], color=col, s=120, label=lab)
    ax.legend(loc='upper left', fontsize=16, ncol=4, bbox_to_anchor=(0, 0.95))
    sc = ax.scatter([], [], s=130, zorder=4); yr = ax.text(0.98, 0.9, '', transform=ax.transAxes, ha='right', fontsize=40, fontweight='bold', color=INK2)
    def upd(fr):
        year = 2016 + ease(min(1, fr / (frames - hold))) * 10.99
        vis = [d for d in data if d[3] <= year]
        if vis: sc.set_offsets(np.c_[[d[0] for d in vis], [d[1] for d in vis]]); sc.set_color([d[2] for d in vis])
        yr.set_text(str(int(min(year, 2026))))
        return [sc, yr]
    a = FuncAnimation(f, upd, frames=frames, blit=False)
    a.save(os.path.join(AN, 'anim_ten_years.mp4'), writer=writer()); plt.close(f); print('years done')

if __name__ == '__main__':
    want = sys.argv[1:] or ['box', 'hist', 'god', 'tiers', 'years']
    {'box': anim_box, 'hist': anim_hist, 'god': anim_god, 'tiers': anim_tiers, 'years': anim_years}
    for w in want: {'box': anim_box, 'hist': anim_hist, 'god': anim_god, 'tiers': anim_tiers, 'years': anim_years}[w]()
