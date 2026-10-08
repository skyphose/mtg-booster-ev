"""
five more clips, same look as animations.py, all numbers pulled from results/ (run_all.sh first).

    python3 animations2.py                 # all of them (~6-8 min)
    python3 animations2.py reveal cut      # just some

  reveal   - a god pack flips open card by card (a median one, not a lucky one), then the 1-in-1,000 math
  cut      - a 15-card collector booster loses its 2 foil commons + 1 foil uncommon; price per card ticks up
  clock    - selling one box: sort, list, ship bars fill while the hours and the dollars count up
  foil     - the unknown 2027 foil-rare rate sweeps from 5% to 25%; pack ev goes red to green past break-even
  history  - god packs bolted onto every set since 2016, appearing year by year; boxes flipped: 0
"""
import csv, os, sys, math, random, json
import numpy as np
from matplotlib.patches import FancyBboxPatch
from animations import plt, FuncAnimation, writer, fig, ease, AN, OUT, FPS, usd, BY_CODE, card_price, realizable, \
    BLUE, ORANGE, AQUA, YELLOW, MAGENTA, RED, SURF, INK, INK2, MUTED, GRID, BASE, GP_VALUE

GP = {r[0]: r[1] for r in csv.reader(open(os.path.join(OUT, 'godpack.csv')))}
FF = json.load(open(os.path.join(OUT, 'fun_facts.json')))
def D(s): return s.replace('$', r'\$')   # matplotlib reads two $ as math mode

def tile(ax, x, y, w, h, fc, ec=None, lw=0, alpha=1.0):
    p = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.08', fc=fc, ec=ec or fc, lw=lw, alpha=alpha)
    ax.add_patch(p); return p

# ----------------------------------------------------------------------------- god pack reveal
def anim_reveal(seconds=14):
    P, C = BY_CODE['fra-play'], BY_CODE['fra-collector']
    def sheet(x, n): sh = x['sheets'][n]['cards']; return list(sh), list(sh.values())
    rm, bfn, bff = sheet(P, 'rare_mythic'), sheet(C, 'non_foil_boosterfun'), sheet(C, 'foil_boosterfun')
    def draw(seed):
        r = random.Random(seed)
        picks = [('rare', k) for k in r.choices(*rm, k=10)] + [('booster fun', k) for k in r.choices(*bfn, k=2)] + [('foil booster fun', k) for k in r.choices(*bff, k=2)]
        return [(lab, card_price(k)[3], card_price(k)[0]) for lab, k in picks]
    target = float(next(r['value'] for r in csv.DictReader(open(os.path.join(OUT, 'significance_summary.csv'))) if r['test'] == 'E god pack spread' and r['metric'] == 'median'))
    seed = min(range(3000), key=lambda s: abs(sum(c[2] for c in draw(s)) - target))   # a median god pack, so the clip isn't a highlight reel
    cards = draw(seed); total = sum(c[2] for c in cards)
    f, ax = fig(); ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis('off')
    ax.set_title('opening a god pack (a typical one)', loc='left')
    W, H = 1.9, 2.6; xs = [0.6 + (i % 7) * 2.18 for i in range(14)]; ys = [5.3 if i < 7 else 2.3 for i in range(14)]
    col = {'rare': BLUE, 'booster fun': AQUA, 'foil booster fun': YELLOW}
    backs = [tile(ax, x, y, W, H, BASE) for x, y in zip(xs, ys)]
    names = [ax.text(x + W / 2, y + H * 0.62, '', ha='center', va='center', fontsize=11, color=INK, wrap=True) for x, y in zip(xs, ys)]
    vals = [ax.text(x + W / 2, y + H * 0.28, '', ha='center', va='center', fontsize=20, fontweight='bold') for x, y in zip(xs, ys)]
    labs = [ax.text(x + W / 2, y + 0.18, '', ha='center', fontsize=10, color=INK2) for x, y in zip(xs, ys)]
    run = ax.text(15.4, 8.55, '', ha='right', fontsize=26, fontweight='bold', color=YELLOW)
    m1 = ax.text(8, 1.2, '', ha='center', fontsize=30, fontweight='bold', color=INK)
    m2 = ax.text(8, 0.4, '', ha='center', fontsize=22, color=INK2)
    flip_frames = int(FPS * 0.45); per = int(FPS * 0.55); reveal_end = per * 14 + flip_frames; frames = FPS * seconds
    def short(n): n = n.split(' // ')[0]; return n if len(n) <= 16 else n[:15] + '…'
    def upd(fr):
        shown = 0.0
        for i, (lab, name, v) in enumerate(cards):
            t0 = i * per; t = (fr - t0) / flip_frames
            if t <= 0: continue
            t = min(1, t); w = W * abs(math.cos(math.pi * t / 2)) if t < 0.5 else W * abs(math.sin(math.pi * (t - 0.5)))   # flip: shrink then grow
            p = backs[i]; p.set_width(max(0.02, w)); p.set_x(xs[i] + (W - max(0.02, w)) / 2)
            if t >= 0.5:
                p.set_facecolor(col[lab]); p.set_alpha(0.9)
                names[i].set_text(short(name)); vals[i].set_text(D(f'${v:,.2f}')); labs[i].set_text(lab); shown += v
        run.set_text(D(f'${shown:,.2f}'))
        if fr > reveal_end + FPS * 0.6:
            m1.set_text(D(f'this one: ${total:,.0f}.   the average god pack: ${GP_VALUE:,.0f}.'))
        if fr > reveal_end + FPS * 2.2:
            m2.set_text(D(f'${GP_VALUE:,.0f} at 1 in 1,000 packs  =  {100 * float(GP["EV lift per Booster Pack from god packs ($)"]):.0f}¢ added to every pack'))
        return backs + names + vals + labs + [run, m1, m2]
    FuncAnimation(f, upd, frames=frames, blit=False).save(os.path.join(AN, 'anim_godpack_reveal.mp4'), writer=writer()); plt.close(f); print('reveal done')

# ----------------------------------------------------------------------------- collector cut
def anim_cut(seconds=12):
    x = BY_CODE['fra-collector']; cfg = x['boosters'][0]['sheets']
    nice = {'foil_common': 'foil common', 'foil_uncommon': 'foil uncommon', 'foil_tower_land': 'foil land', 'foil_rare_mythic': 'foil rare', 'non_foil_boosterfun': 'booster fun',
            'foil_boosterfun': 'foil booster fun', 'braintwister_frc': 'special slot'}
    slots = []
    for s, n in cfg.items():
        lab = nice.get(s, 'echo card'); slots += [lab] * n
    order = ['foil common', 'foil uncommon', 'echo card', 'foil land', 'special slot', 'booster fun', 'foil booster fun', 'foil rare']
    slots.sort(key=lambda l: order.index(l) if l in order else 99)
    cut_idx = [i for i, l in enumerate(slots) if l == 'foil common'][:2] + [i for i, l in enumerate(slots) if l == 'foil uncommon'][:1]
    n = len(slots); W, H = 1.05, 1.5; xs = [0.35 + i * 1.22 for i in range(n)]
    removed = float(GP['EV removed per Collector Booster (2 foil C + 1 foil U) ($)'])
    cc = next(r for r in csv.DictReader(open(os.path.join(OUT, 'collector_cut.csv'))) if r['product'] == 'fra-collector')
    f, ax = fig(); ax.set_xlim(0, 19); ax.set_ylim(0, 10); ax.axis('off'); ax.set_title('one collector booster, 2027 edition', loc='left')
    tiles = [tile(ax, xx, 5.2, W, H, MAGENTA if i in cut_idx else BASE, alpha=0.95) for i, xx in enumerate(xs)]
    labs = [ax.text(xx + W / 2, 4.85, l.replace(' ', '\n'), ha='center', va='top', fontsize=10, color=INK2) for xx, l in zip(xs, slots)]
    big = ax.text(9.5, 2.6, '', ha='center', fontsize=46, fontweight='bold'); sub = ax.text(9.5, 1.5, '', ha='center', fontsize=22, color=INK2)
    cnt = ax.text(9.5, 8.2, '', ha='center', fontsize=30, fontweight='bold')
    frames = FPS * seconds; fall0, fall1 = int(FPS * 2.5), int(FPS * 5.5)
    def upd(fr):
        t = 0 if fr < fall0 else min(1, (fr - fall0) / (fall1 - fall0)); e = ease(t)
        for i in cut_idx:
            tiles[i].set_y(5.2 - 6 * e * e); tiles[i].set_alpha(0.95 * (1 - e)); labs[i].set_alpha(1 - e)
        left = n - (3 if t >= 1 else 0)
        cnt.set_text(f'{left} cards'); cnt.set_color(INK if t < 1 else MAGENTA)
        ppc = 26.99 / (n if t < 1 else n - 3)
        big.set_text(D(f'$26.99 ÷ {n if t < 1 else n - 3} = ${ppc:.2f} a card')); big.set_color(INK if t < 1 else MAGENTA)
        if fr > fall1 + FPS: sub.set_text(D(f'same price. removed: ${removed:.2f} of cards at market, {100 * float(cc["cut_cash_per_pack"]):.0f}¢ if you sold them'))
        return tiles + labs + [big, sub, cnt]
    FuncAnimation(f, upd, frames=frames, blit=False).save(os.path.join(AN, 'anim_collector_cut.mp4'), writer=writer()); plt.close(f); print('cut done')

# ----------------------------------------------------------------------------- selling clock
def anim_clock(seconds=14):
    cards, listable, lv = FF['fra_box_cards'], FF['fra_box_listable_count'], FF['fra_box_listable_value']
    sell, fee, sup, ship_min = 0.6, 0.13, 0.75, 8
    sort_h = cards * 15 / 3600; list_h = listable * 3 / 60; orders = listable * sell; ship_h = orders * ship_min / 60
    net = lv * sell * (1 - fee) - orders * sup; bulk = (cards - listable) * 4 / 1000; cash = net + bulk; hours = sort_h + list_h + ship_h
    stages = [(f'sort {cards} cards', sort_h, 0.0, MUTED), (f'list {listable} cards', list_h, 0.0, BLUE), (f'pack + ship {orders:.0f} orders', ship_h, net, AQUA), ('sell the bulk', 0.05, bulk, YELLOW)]
    total_h = sum(s_[1] for s_ in stages)   # includes the bulk drop-off, so the cash ends at the full amount
    f, ax = fig(); ax.set_xlim(0, total_h * 1.05); ax.set_ylim(-0.6, 4.4); ax.set_yticks([]); ax.grid(False)
    ax.set_title('turning one box into cash', loc='left'); ax.set_xlabel('hours'); ax.spines['left'].set_visible(False)
    starts = np.cumsum([0] + [s[1] for s in stages[:-1]])
    bars = [ax.barh(3 - i, 0, left=st, height=0.6, color=s[3]) for i, (s, st) in enumerate(zip(stages, starts))]
    for i, (s, st) in enumerate(zip(stages, starts)): ax.text(st, 3 - i + 0.42, s[0], fontsize=17, color=INK2)
    clock = ax.text(0.98, 0.92, '', transform=ax.transAxes, ha='right', fontsize=40, fontweight='bold')
    money = ax.text(0.98, 0.80, '', transform=ax.transAxes, ha='right', fontsize=34, fontweight='bold', color=AQUA)
    rate = ax.text(0.02, 0.06, '', transform=ax.transAxes, ha='left', fontsize=36, fontweight='bold', color=YELLOW)
    frames = FPS * seconds; run = FPS * (seconds - 4)
    def upd(fr):
        h = total_h * ease(min(1, fr / run)); got = 0.0
        for (s, st, b) in zip(stages, starts, bars):
            done = max(0, min(s[1], h - st)); b.patches[0].set_width(done)
            if s[1] and done >= s[1] * 0.999: got += s[2]
            elif s[1]: got += s[2] * done / s[1]
        clock.set_text(f'{min(h, hours):.1f} hours'); money.set_text(D(f'${got:,.2f} in hand'))
        if fr > run + FPS * 0.5: rate.set_text(D(f'${cash / hours:,.2f} an hour'))
        return [clock, money, rate] + [b.patches[0] for b in bars]
    FuncAnimation(f, upd, frames=frames, blit=False).save(os.path.join(AN, 'anim_selling_clock.mp4'), writer=writer()); plt.close(f); print('clock done')

# ----------------------------------------------------------------------------- foil break-even slider
def anim_foil(seconds=12):
    fr_ = list(csv.DictReader(open(os.path.join(OUT, 'foil_scenarios.csv'))))
    px = np.array([100 * float(r['p_foil_rm_new']) for r in fr_]); py = np.array([float(r['delta_per_box']) for r in fr_])
    be = float(GP['break-even new foil R/M rate so pack EV is unchanged (%)']); today = float(GP['today: P(foil rare or mythic in a pack) (%)'])
    lift_box = float(GP['EV lift per 30-pack Booster box ($)'])
    xs = np.linspace(5, 25, 400); ys = np.interp(xs, px, py, left=None)
    slope = (py[-1] - py[0]) / (px[-1] - px[0]); ys = np.where(xs < px[0], py[0] + slope * (xs - px[0]), ys)
    f, ax = fig(); ax.set_xlim(5, 25); ax.set_ylim(min(ys) - 2, max(ys) + 4)
    ax.set_title("2027's unknown: how often the foil slot is a rare", loc='left'); ax.set_xlabel('new foil rare/mythic rate (% of packs)'); ax.set_ylabel('change in box ev vs today')
    ax.yaxis.set_major_formatter(usd); ax.axhline(0, color=INK2, lw=1.5, ls='--')
    ax.axvline(today, color=MUTED, lw=2); ax.text(today + 0.2, max(ys) + 2.5, f'today\n1 in {100 / today:.0f}', color=MUTED, fontsize=15)
    ax.axvline(be, color=AQUA, lw=2); ax.text(be + 0.2, max(ys) + 2.5, f'break-even\n1 in {100 / be:.0f}', color=AQUA, fontsize=15)
    ax.axhline(-lift_box, color=YELLOW, lw=1, ls=':'); ax.text(24.8, -lift_box - 1.4, D(f'god packs give back ${lift_box:.2f}/box'), ha='right', color=YELLOW, fontsize=14)
    ln, = ax.plot([], [], lw=4, color=BLUE); dot, = ax.plot([], [], 'o', ms=18)
    read = ax.text(0.03, 0.88, '', transform=ax.transAxes, fontsize=34, fontweight='bold')
    frames = FPS * seconds; run = FPS * (seconds - 3)
    def upd(fr):
        k = int((len(xs) - 1) * ease(min(1, fr / run))); v = ys[k]; c = AQUA if v >= 0 else RED
        ln.set_data(xs[: k + 1], ys[: k + 1]); dot.set_data([xs[k]], [v]); dot.set_color(c)
        read.set_text(D(f'1 in {100 / xs[k]:.1f}:  {"+" if v >= 0 else "−"}${abs(v):.2f} a box')); read.set_color(c)
        return [ln, dot, read]
    FuncAnimation(f, upd, frames=frames, blit=False).save(os.path.join(AN, 'anim_foil_breakeven.mp4'), writer=writer()); plt.close(f); print('foil done')

# ----------------------------------------------------------------------------- god packs through history
def anim_history(seconds=14):
    rows = [r for r in csv.DictReader(open(os.path.join(OUT, 'godpack_history.csv')))]
    rows.sort(key=lambda r: (int(r['year']), r['product']))
    col = {'draft': MUTED, 'set': AQUA, 'play': BLUE}
    priced = [r for r in rows if r['ratio_before']]
    flips = sum((float(r['ratio_before']) < 1) != (float(r['ratio_after']) < 1) for r in priced)
    f, ax = fig(); ax.set_xlim(2015.5, 2026.9); ax.set_yscale('log'); ax.set_ylim(8, 400)
    ax.yaxis.set_major_formatter(usd); ax.set_ylabel('what a god pack would be worth today')
    ax.set_title('if every set since 2016 had god packs', loc='left')
    jit = {}; px = []
    for r in rows:
        y = int(r['year']); jit[y] = jit.get(y, 0) + 1; px.append(y - 0.35 + 0.7 * (jit[y] - 1) / max(1, sum(1 for q in rows if int(q['year']) == y) - 1 or 1))
    py = [float(r['gp_mean']) for r in rows]; pc = [col[r['kind']] for r in rows]
    sc = ax.scatter([], [], s=140)
    best = max(rows, key=lambda r: float(r['lift_box']))
    t1 = ax.text(0.02, 0.92, '', transform=ax.transAxes, fontsize=28, fontweight='bold')
    t2 = ax.text(0.02, 0.84, '', transform=ax.transAxes, fontsize=24, color=INK2)
    t3 = ax.text(0.02, 0.76, '', transform=ax.transAxes, ha='left', fontsize=30, fontweight='bold', color=RED)
    for lab, c in (('draft booster', MUTED), ('set booster', AQUA), ('play booster', BLUE)): ax.scatter([], [], c=c, s=120, label=lab)
    ax.legend(loc='upper right', fontsize=15)
    frames = FPS * seconds; run = FPS * (seconds - 4)
    def upd(fr):
        k = int(len(rows) * min(1, fr / run))
        if k: sc.set_offsets(np.c_[px[:k], py[:k]]); sc.set_color(pc[:k])
        if k: t1.set_text(f'{rows[k - 1]["year"]}: {k} sets')
        mx = max([float(r['lift_box']) for r in rows[:k]] or [0])
        t2.set_text(D(f'most a god pack adds to a box so far: ${mx:.2f}'))
        if fr > run + FPS * 0.5: t3.set_text(f'boxes it flips from losing to winning: {flips} of {len(priced)}')
        return [sc, t1, t2, t3]
    FuncAnimation(f, upd, frames=frames, blit=False).save(os.path.join(AN, 'anim_godpack_history.mp4'), writer=writer()); plt.close(f); print('history done')

if __name__ == '__main__':
    todo = {'reveal': anim_reveal, 'cut': anim_cut, 'clock': anim_clock, 'foil': anim_foil, 'history': anim_history}
    for w in (sys.argv[1:] or list(todo)): todo[w]()
