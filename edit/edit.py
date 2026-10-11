"""
talking-head -> finished edit. you record yourself reading the script; this cuts in the charts, animations and
graphics at the right moments, strips retakes and dead air, cleans the audio, and renders.

    python3 edit/edit.py transcribe  path/to/recording.mp4         # resumable, ~2 min chunks
    python3 edit/edit.py plan        path/to/recording.mp4 --cut a  # writes edit/work/<name>/plan_a.txt for you to check
    python3 edit/edit.py render      path/to/recording.mp4 --cut a  # resumable, renders in pieces then joins
    python3 edit/edit.py all         path/to/recording.mp4 --cut a

options: --cut a|b (public or nerd cut)  --no-pip (no picture-in-picture over b-roll)  --burn-captions
         --music bed.mp3 (ducked under your voice)  --max-gap 0.45 (longest pause kept, seconds)

retakes: if you flub a sentence, say "redo", pause, and start the sentence again. everything from the start of
the flubbed sentence through "redo" is cut.

every step writes into edit/work/<recording name>/ and skips work that is already done, so if a run is interrupted, run it again.
"""
import argparse, json, os, re, subprocess, sys, time, math

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
WORK = os.environ.get('EDIT_WORK') or os.path.join(HERE, 'work'); os.makedirs(WORK, exist_ok=True)
GFX = os.path.join(HERE, 'gfx'); FONTS = os.path.join(HERE, 'fonts')
FPS = 60; W, H = 1920, 1080   # --fps to change; match the camera
# voice chain. no broadband denoiser: the mic's own gate already leaves the pauses near silent, and afftdn was
# shaving ~5 dB off 2-5 kHz and ~10 dB off 5-10 kHz (that's the 'muffled' sound). instead: rumble cut, a little
# presence and air, gentle de-ess, light compression, then two-pass loudnorm to -14 LUFS / -1.5 dBTP.
VOICE_CHAIN = ('highpass=f=80,equalizer=f=3500:t=q:w=0.9:g=3,treble=g=3:f=9000,deesser=i=0.3,'
               'acompressor=threshold=-20dB:ratio=3:attack=5:release=120')
LOUD = 'I=-14:TP=-1.5:LRA=11'
# place every audio sample by its timestamp: the joined clips have millisecond gaps at the joins, and reading the
# audio as one continuous run would pull it ~70 ms ahead of the picture by the end of an 8-minute edit
ASYNC = 'aresample=async=1:first_pts=0'

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-4000:]); raise SystemExit(f'command failed: {cmd[0]}')
    return r.stdout

def duration(path):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', path]).strip())

def wpath(*p): return os.path.join(WORK, *p)

# ============================================================================= 1. transcribe (resumable)
CHUNK = 120.0  # seconds of audio per chunk

def transcribe(src, model_dir=None, budget=150):
    t0 = time.time()
    wav = wpath('audio16k.wav')
    if not os.path.exists(wav):
        run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-vn', '-ac', '1', '-ar', '16000', wav])
    total = duration(wav)
    from faster_whisper import WhisperModel
    model_dir = model_dir or os.path.join(HERE, 'models', 'faster-whisper-small.en')
    model = WhisperModel(model_dir, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 4)
    n = math.ceil(total / CHUNK)
    for i in range(n):
        out = wpath(f'tx_{i:03d}.json')
        if os.path.exists(out): continue
        if time.time() - t0 > budget:
            print(f'transcribe: {i}/{n} chunks done, run again to continue'); return False
        s = i * CHUNK; e = min(total, s + CHUNK + 2.0)   # 2 s overlap so no word is cut at a boundary
        piece = wpath(f'piece_{i:03d}.wav')
        run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{s}', '-to', f'{e}', '-i', wav, piece])
        segs, _ = model.transcribe(piece, language='en', word_timestamps=True, vad_filter=True, beam_size=5,
                                   initial_prompt='magic the gathering, booster boxes, god packs, collector boosters, EV, tcgplayer, scryfall, msrp, foil, mythic')
        words = []
        for sg in segs:
            for w in sg.words:
                ws, we = s + w.start, s + w.end
                if i > 0 and ws < s + 1.0: continue            # owned by the previous chunk's overlap
                if i < n - 1 and ws >= s + CHUNK + 1.0: continue
                words.append({'w': w.word.strip(), 's': round(ws, 3), 'e': round(we, 3), 'p': round(w.probability, 3)})
        json.dump(words, open(out, 'w')); os.remove(piece)
        print(f'transcribe: chunk {i + 1}/{n} ({len(words)} words)')
    words = []
    for i in range(n): words += json.load(open(wpath(f'tx_{i:03d}.json')))
    words.sort(key=lambda x: x['s'])
    json.dump(words, open(wpath('transcript.json'), 'w'), indent=0)
    print(f'transcribe: done, {len(words)} words, {total / 60:.1f} min'); return True

# ============================================================================= 2. plan
_ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
_TENS = 'twenty thirty forty fifty sixty seventy eighty ninety'.split()
def _num_word(n):
    if n < 20: return _ONES[n]
    t, o = divmod(n, 10); return _TENS[t - 2] + ('' if o == 0 else ' ' + _ONES[o])
def norm(t):
    """lowercase, drop punctuation, and spell out small numbers so the transcriber's '15' matches a cue's 'fifteen'."""
    t = re.sub(r"[^a-z0-9$%¢ ]", '', t.lower().replace('-', ' ').replace('’', "'").replace("'", ''))
    return ' '.join(_num_word(int(w.lstrip('$'))) if re.fullmatch(r'\$?\d{1,2}', w) else w for w in t.split())

FILLER = {'this', 'uh', 'um', 'okay', 'ok', 'again', 'that'}
def find_retakes(words):
    """two ways to flag a flub:
      'redo'           - cut the flubbed sentence and the word redo
      "let's restart"  - you went back and said a line (or a few) again; find where that line first started, up to
                         90 seconds back, and cut everything from there to the restart, so only the clean take stays"""
    from rapidfuzz import fuzz
    toks = [norm(w['w']) for w in words]; cuts = []; k = 0
    while k < len(words):
        t = toks[k].replace(' ', '')
        if t == 'redo' or (t == 're' and k + 1 < len(words) and toks[k + 1] == 'do'):
            end_k = k + (1 if t == 're' else 0); j = k - 1
            while j > 0:
                prev = words[j - 1]
                if re.search(r'[.?!]$', prev['w']) or words[j]['s'] - prev['e'] > 1.0: break
                j -= 1
            cuts.append((words[max(j, 0)]['s'] - 0.05, words[end_k]['e'] + 0.1, ' '.join(x['w'] for x in words[j:end_k + 1]))); k = end_k + 1; continue
        if t == 'restart':
            m0 = k - 1 if k > 0 and toks[k - 1].replace(' ', '') in ('lets', 'let') else k
            m = k + 1
            while m < len(words) and toks[m] in FILLER: m += 1
            if m >= len(words): break
            probe = ' '.join(toks[m:m + 5]); start = None; best = 0
            for j in range(m0 - 1, -1, -1):
                if words[m0]['s'] - words[j]['s'] > 90: break
                sc = fuzz.ratio(probe, ' '.join(toks[j:j + 5]))
                if sc > best: best, start = sc, j
            if best < 75:   # couldn't find the earlier attempt: fall back to cutting the sentence the restart sits in
                start = m0
                while start > 0 and not re.search(r'[.?!]$', words[start - 1]['w']) and words[start]['s'] - words[start - 1]['e'] <= 1.0: start -= 1
            cuts.append((words[start]['s'] - 0.05, words[m]['s'] - 0.05, ' '.join(x['w'] for x in words[start:m]))); k = m; continue
        k += 1
    return cuts

def drop_cut_words(words, cuts):
    return [w for w in words if not any(a <= w['s'] < b for a, b, _ in cuts)]

def align(words, cues):
    """monotonic fuzzy match of each cue phrase. prefers the EARLIEST strong match after the previous cue, so a phrase
    that recurs later in the script can't drag the cursor forward. cues with same_as reuse another cue's match."""
    from rapidfuzz import fuzz
    toks = [norm(w['w']) for w in words]; pos = 0; out = []; byid = {}
    for c in cues:
        if c['type'] == 'endcard' or not c.get('phrase'):
            out.append(dict(c, score=100, matched=True)); continue
        if c.get('same_as') and byid.get(c['same_as'], {}).get('matched'):
            ref = byid[c['same_as']]; rec = dict(c, score=ref['score'], matched=True, ws=ref['ws'], we=ref['we'], heard=ref['heard'])
            out.append(rec); byid[c['id']] = rec; continue
        ph = norm(c['phrase']); L = len(ph.split()); cands = []
        for i in range(pos, min(len(words), pos + c.get('window', 700))):
            best = (0, None)
            for l in (L - 1, L, L + 1, L + 2):
                if l < 1 or i + l > len(words): continue
                sc = fuzz.ratio(ph, ' '.join(toks[i:i + l]))
                if sc > best[0]: best = (sc, l)
            if best[1]: cands.append((best[0], i, i + best[1] - 1))
        strong = [x for x in cands if x[0] >= 88]
        if strong:  # earliest strong hit, then the best-scoring start within 2 words of it (drops a stray leading word)
            first = min(strong, key=lambda x: x[1])
            pick = max([x for x in strong if x[1] - first[1] <= 2], key=lambda x: (x[0], x[1]))
        else:   # no strong match: only look nearby, so one weak guess can't drag the cursor minutes ahead
            near = [x for x in cands if x[1] - pos <= 250]
            pick = max(near) if near else (0, None, None)
        ok = pick[0] >= c.get('min_score', 72)
        rec = dict(c, score=round(pick[0]), matched=ok)
        if ok:
            rec['ws'], rec['we'] = words[pick[1]]['s'], words[pick[2]]['e']
            rec['heard'] = ' '.join(w['w'] for w in words[pick[1]:pick[2] + 1]); pos = pick[1] + 1
        out.append(rec); byid[c['id']] = rec
    return out

def keep_segments(words, total, max_gap, pad_in=0.12, pad_out=0.22):
    segs = []
    for w in words:
        a, b = max(0, w['s'] - pad_in), min(total, w['e'] + pad_out)
        if segs and a - segs[-1][1] <= max_gap: segs[-1][1] = max(segs[-1][1], b)
        else: segs.append([a, b])
    return segs

def make_mapper(segs):
    starts = []; acc = 0.0
    for a, b in segs: starts.append(acc); acc += b - a
    def m(t):
        for (a, b), s0 in zip(segs, starts):
            if t < a: return s0
            if t <= b: return s0 + (t - a)
        return acc
    return m, acc

def plan(src, cut, max_gap):
    words = json.load(open(wpath('transcript.json'))); total = duration(src)
    cues = json.load(open(os.path.join(HERE, f'cues_{cut}.json')))
    cuts = find_retakes(words)
    # optional per-recording settings next to the video: '<recording>.edit.json'
    #   {"phrases": {"cue_id": "what you actually said"}, "cuts": [[start_s, end_s, "why"], ...]}
    ov_path = os.path.splitext(os.path.abspath(src))[0] + '.edit.json'
    if os.path.exists(ov_path):
        ov = json.load(open(ov_path))
        cues = [dict(c, phrase=ov.get('phrases', {}).get(c['id'], c.get('phrase'))) for c in cues]
        cuts += [(float(a), float(b), f'[manual] {why}') for a, b, why in ov.get('cuts', [])]
        print(f'using {os.path.basename(ov_path)}: {len(ov.get("phrases", {}))} phrase overrides, {len(ov.get("cuts", []))} manual cuts')
    cuts.sort(key=lambda c: c[0]); clean = drop_cut_words(words, cuts)
    marks = align(clean, cues)
    segs = keep_segments(clean, total, max_gap); m, tdur = make_mapper(segs)
    # inserts (full-frame cards that add time) are placed after their phrase; build the final clock
    # an insert goes in the pause after its phrase. pauses get trimmed, so never let it land past the next word.
    def insert_at(c):
        t0 = m(c['we']); nxt = next((w for w in clean if w['s'] > c['we'] + 0.01), None)
        lim = m(nxt['s']) - 0.05 if nxt else t0 + 1
        return round(max(t0 + 0.1, min(t0 + c.get('offset', 0.3), lim)) * FPS) / FPS   # on the frame grid, or the pieces after it drift
    inserts = sorted([(insert_at(c), c) for c in marks if c['matched'] and c['type'] == 'insert'], key=lambda x: x[0])
    end_card = [c for c in cues if c['type'] == 'endcard']
    holds = []   # (trimmed time, seconds): pauses in the talking so an animation can finish
    def final_t(t):  # trimmed time -> final time (after inserts and holds before t)
        return t + sum(c['dur'] for at, c in inserts if at <= t) + sum(h for at, h in holds if at <= t)
    def anim_len(asset):
        return duration(asset_path(asset)) if asset.endswith('.mp4') else None
    def build_events():
        events = []
        for c in marks:
            if not c['matched'] or c['type'] in ('insert', 'mark', 'endcard'): continue
            start = final_t(m(c['ws'] if c.get('anchor', 'start') == 'start' else c['we'])) + c.get('offset', 0)
            nxt = next((x for x in marks if x['id'] == c.get('until') and x['matched']), None) if c.get('until') else None
            if c.get('until'):
                end = final_t(m(nxt['ws'])) - 0.15 if nxt else start + c.get('max', 8)
            else: end = start + c.get('dur', c.get('max', 4))
            D = anim_len(c['asset']) if c['type'] == 'broll' else None
            # an animation gets at least its own length (up to where the talking moves on), whatever 'max' says
            if c.get('max'): end = min(end, start + max(c['max'], D + ANIM_BEAT if D else 0))
            if c.get('min'): end = max(end, start + c['min'])
            for at, ic in inserts:   # overlays never sit on top of a full-frame card (title insert, end card)
                a0 = final_t(at) - ic['dur']; a1 = a0 + ic['dur']
                if a0 - 0.01 <= start < a1: end += a1 - start; start = a1
                elif start < a0 < end: end = a0
            end = min(end, final_t(tdur) - 0.1)
            if end - start < 0.5: continue
            e = {'id': c['id'], 'type': c['type'], 'asset': c['asset'], 'start': round(start, 3), 'end': round(end, 3), 'pip': c.get('pip', True)}
            if D:
                slot = end - start
                e['speed'] = round(min(ANIM_MAX_SPEED, max(1.0, D / max(0.1, slot - ANIM_BEAT))), 3)
                e['_short'] = D / e['speed'] + ANIM_BEAT - slot   # still this many seconds short at full speed
                e['_resume'] = nxt                            # the cue that cuts it off (where a pause can go)
            events.append(e)
        return events
    # pass 1: find animations that can't finish even sped up, and pause the talking right before the line that
    # cuts them off (in the gap between sentences). pass 2: lay everything out again with those pauses in.
    for e in build_events():
        if e.get('_short', 0) > 0.2 and e['_resume']:
            ws = e['_resume']['ws']; prev = max((w for w in clean if w['e'] <= ws + 0.01), key=lambda w: w['e'], default=None)
            at = (m(prev['e']) + m(ws)) / 2 if prev else m(ws) - 0.1
            holds.append((round(at * FPS) / FPS, math.ceil((e['_short'] + 0.05) * FPS) / FPS))   # frame-grid place and length
    holds.sort()
    events = build_events()
    for e in events: e.pop('_short', None); e.pop('_resume', None)
    final_dur = final_t(tdur) + sum(c['dur'] for c in end_card)
    # captions on the final clock
    cap = []
    for w in clean:
        cap.append({'w': w['w'], 's': final_t(m(w['s'])), 'e': final_t(m(w['e']))})
    allins = [(at, c['asset'], c['dur']) for at, c in inserts] + [(at, None, h) for at, h in holds]
    plan = {'src': os.path.abspath(src), 'cut': cut, 'segments': segs, 'inserts': [{'at': round(at, 3), 'asset': a, 'dur': d} for at, a, d in sorted(allins, key=lambda x: x[0])],
            'holds': [[round(final_t(at) - h, 3), round(final_t(at), 3)] for at, h in holds],
            'end_card': end_card[0] if end_card else None, 'events': sorted(events, key=lambda e: e['start']), 'duration': round(final_dur, 2), 'captions': cap}
    json.dump(plan, open(wpath(f'plan_{cut}.json'), 'w'), indent=1)
    write_captions(cap, wpath(f'captions_{cut}.srt'), wpath(f'captions_{cut}.ass'))
    # human-readable report + youtube chapters
    L = [f'plan for cut {cut}: {os.path.basename(src)}', f'recorded {total / 60:.1f} min -> edit {final_dur / 60:.1f} min  ({total - tdur:.0f} s of pauses and retakes removed)', '']
    L.append(f'animation pauses ({len(holds)}):'); L += [f'  {h:.1f}s pause at {final_t(at) - h:.1f}s' for at, h in holds] or ['  none']
    L.append(f'retakes cut ({len(cuts)}):'); L += [f'  {a:7.1f}s  "{t[:90]}"' for a, b, t in cuts] or ['  none']
    L += ['', 'cues:']
    for c in marks:
        if 'ws' not in c and c['matched']:
            L.append(f"  END {c['id']:16} ({c['type']}, {c.get('dur', 0)}s)"); continue
        flag = 'OK ' if c['matched'] and c['score'] >= 85 else ('?? ' if c['matched'] else 'MISSING')
        L.append(f"  {flag} {c['id']:16} score {c['score']:3}  " + (f"@{c['ws']:7.1f}s heard: \"{c.get('heard', '')[:70]}\"" if c['matched'] else f"wanted: \"{c['phrase']}\""))
    L += ['', 'youtube chapters (paste into the description):', '0:00 cold open']
    for e in events:
        if e['type'] == 'tag':
            mm, ss = divmod(int(e['start']), 60); L.append(f"{mm}:{ss:02d} {CHAPTER_NAMES.get(e['asset'], e['id'])}")
    open(wpath(f'plan_{cut}.txt'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))

CHAPTER_NAMES = {'tag_p1.png': 'the number everyone gets wrong', 'tag_p2.png': 'where the money actually goes', 'tag_p3.png': 'ten years',
                 'tag_p4.png': "what's a god pack worth", 'tag_p5.png': 'the part you skipped', 'tag_p6.png': 'from behind the counter',
                 'tag_b1.png': 'how the model works', 'tag_b2.png': 'on paper, you win', 'tag_b3.png': 'the haircut, and the hours', 'tag_b4.png': 'ten years, with the caveats',
                 'tag_b5.png': 'pricing a god pack', 'tag_b6.png': 'the foil change is the real ev story', 'tag_b7.png': 'collector shrink', 'tag_b8.png': 'behind the counter', 'tag_h1.png': 'what if god packs had always existed'}

def fmt_srt(t): h, r = divmod(t, 3600); mi, s = divmod(r, 60); return f'{int(h):02d}:{int(mi):02d}:{s:06.3f}'.replace('.', ',')
def fmt_ass(t): h, r = divmod(t, 3600); mi, s = divmod(r, 60); return f'{int(h)}:{int(mi):02d}:{s:05.2f}'
def write_captions(cap, srt, ass):
    lines = []; cur = []
    for w in cap:
        if cur and (len(cur) >= 7 or w['s'] - cur[-1]['e'] > 0.6 or w['e'] - cur[0]['s'] > 2.8 or re.search(r'[.?!]$', cur[-1]['w'])):
            lines.append(cur); cur = []
        cur.append(w)
    if cur: lines.append(cur)
    with open(srt, 'w') as f:
        for i, l in enumerate(lines, 1): f.write(f"{i}\n{fmt_srt(l[0]['s'])} --> {fmt_srt(l[-1]['e'] + 0.15)}\n{' '.join(x['w'] for x in l)}\n\n")
    with open(ass, 'w') as f:
        f.write('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\n'
                'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                'Style: Cap,Inter,58,&H00FFFFFF,&H00FFFFFF,&H00191A1A,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,2,200,200,70,1\n\n'
                '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
        for l in lines: f.write(f"Dialogue: 0,{fmt_ass(l[0]['s'])},{fmt_ass(l[-1]['e'] + 0.15)},Cap,,0,0,0,,{' '.join(x['w'] for x in l)}\n")

# ============================================================================= 3. render (resumable, in pieces)
PIECE = 45.0   # seconds of finished video per piece

def asset_path(a):
    for base in (GFX, os.path.join(ROOT, 'results', 'charts'), os.path.join(ROOT, 'results', 'animations')):
        p = os.path.join(base, a)
        if os.path.exists(p): return p
    raise SystemExit(f'asset not found: {a}')

def build_base(pl, budget):
    """trimmed + cleaned a-roll with inserts and end card, at final timing. audio is processed here once."""
    out = wpath(f'base_{pl["cut"]}.mp4')
    if os.path.exists(out): return out
    src = pl['src']; segs = pl['segments']
    # 3a. trim the a-roll to the kept segments, in chunks of segments so each ffmpeg call is short
    parts = []; group = []; acc = 0.0
    for s in segs:
        group.append(s); acc += s[1] - s[0]
        if acc >= 60: parts.append(group); group = []; acc = 0.0
    if group: parts.append(group)
    t0 = time.time(); trimmed = []
    for i, g in enumerate(parts):
        o = wpath(f'trim_{i:03d}.mp4'); trimmed.append(o)
        if os.path.exists(o): continue
        if time.time() - t0 > budget: print(f'render: trimmed {i}/{len(parts)} pieces, run again'); return None
        # snap every cut to the frame grid and use half-open windows, so each kept stretch has exactly as many
        # video frames as it has audio (48000/60 = 800 samples a frame). otherwise every cut can add a frame of
        # picture the audio doesn't have, and over a few hundred cuts the voice drifts ahead of the lips.
        snap = lambda v: round(v * FPS) / FPS
        a, b = snap(g[0][0]), snap(g[-1][1])
        sel = '+'.join(f'gte(t,{snap(x) - a - 0.25 / FPS:.5f})*lt(t,{snap(y) - a - 0.25 / FPS:.5f})' for x, y in g if snap(y) > snap(x))
        vf = (f"select='{sel}',setpts=N/FRAME_RATE/TB,scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a19,fps={FPS},format=yuv420p")
        # aselect keeps or drops whole audio frames, so cut the audio into one-video-frame blocks first
        af = f"aresample=48000,asetnsamples=n={48000 // FPS}:p=0,aselect='{sel}',asetpts=N/SR/TB"
        run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{a:.3f}', '-to', f'{b + 0.05:.3f}', '-i', src, '-vf', vf, '-af', af,
             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'pcm_s16le', o.replace('.mp4', '.mkv')])
        os.replace(o.replace('.mp4', '.mkv'), o)
        print(f'render: trimmed piece {i + 1}/{len(parts)}')
    # 3b. one concat list: trimmed pieces split at inserts + insert cards + end card
    joined = wpath('trimmed_all.mkv')
    if not os.path.exists(joined):
        with open(wpath('trim_list.txt'), 'w') as f:
            for o in trimmed: f.write(f"file '{o}'\n")
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', wpath('trim_list.txt'), '-c', 'copy', joined + '.part.mkv'])
        os.replace(joined + '.part.mkv', joined)
    cards = [(round(x['at'] * FPS) / FPS, x['asset'], x['dur']) for x in pl['inserts']]   # back onto the exact frame grid
    clips = []; last = 0.0; jd = duration(joined)
    def card_clip(asset, dur, name):
        o = wpath(name)
        if not os.path.exists(o) and asset is None:   # an animation pause: black (keys to the backdrop) and silence
            run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-t', f'{dur}', '-i', f'color=c=black:s={W}x{H}:r={FPS}', '-f', 'lavfi', '-t', f'{dur}',
                 '-i', 'anullsrc=r=48000:cl=stereo', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le',
                 '-shortest', o + '.part.mkv'])
            os.replace(o + '.part.mkv', o)
        if not os.path.exists(o):
            run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-t', f'{dur}', '-i', asset_path(asset), '-f', 'lavfi', '-t', f'{dur}', '-i', 'anullsrc=r=48000:cl=stereo',   # must match the voice track: a mono card concatenated as stereo halves its length and throws sync off
                 '-vf', f'scale={W}:{H},fps={FPS},format=yuv420p,fade=in:st=0:d=0.25,fade=out:st={dur - 0.3}:d=0.3', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16',
                 '-c:a', 'pcm_s16le', '-shortest', o + '.part.mkv'])
            os.replace(o + '.part.mkv', o)
        return o
    def enc_range(a, b, name):
        # re-encode [a, b) of the joined a-roll in 60 s pieces, each written to a temp file and renamed when done,
        # so a run that gets cut off never leaves a half-written piece behind
        outs = []; j = 0; x = a
        while x < b - 0.01:
            y = min(b, x + 60); o = wpath(f'{name}_{j:02d}.mkv'); outs.append(o)
            if not os.path.exists(o):
                if time.time() - t0 > budget: return None
                tmp = o.replace('.mkv', '.part.mkv')
                run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{x - 0.25 / FPS:.5f}', '-to', f'{y - 0.25 / FPS:.5f}', '-i', joined, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'pcm_s16le', tmp])
                os.replace(tmp, o); print(f'render: encoded {name}_{j:02d}')
            x = y; j += 1
        return outs
    for k, (at, asset, dur) in enumerate(cards):
        r = enc_range(last, at, f'seg_{k:02d}')
        if r is None: print('render: base not finished, run again'); return None
        clips += r + [card_clip(asset, dur, f'card_{k:02d}.mkv')]; last = at
    r = enc_range(last, jd, 'seg_last')
    if r is None: print('render: base not finished, run again'); return None
    clips += r
    if pl['end_card']: clips.append(card_clip(pl['end_card']['asset'], pl['end_card']['dur'], 'card_end.mkv'))
    with open(wpath('base_list.txt'), 'w') as f:
        for c in clips: f.write(f"file '{c}'\n")
    raw = wpath('base_raw.mkv')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', wpath('base_list.txt'), '-c', 'copy', raw])
    # sync guard: every clip must carry the same audio format, and audio must run as long as the picture
    fmts = {subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=sample_rate,channels', '-of', 'csv=p=0', c],
                           capture_output=True, text=True).stdout.strip() for c in clips}
    if len(fmts) != 1: sys.exit(f'render: clips have mixed audio formats {fmts}, sync would drift. delete the odd ones and rerun')
    adur = float(subprocess.run(['ffmpeg', '-v', 'error', '-i', raw, '-vn', '-f', 'wav', '-'], capture_output=True).stdout.__len__() - 44) / (48000 * 2 * int(fmts.pop().split(',')[1]))
    if abs(adur - duration(raw)) > 0.15: sys.exit(f'render: audio {adur:.2f}s vs video {duration(raw):.2f}s, refusing to continue')
    # 3c. audio clean-up once, on the whole thing (needs to see all of it for loudness)
    aout = wpath('voice.wav')
    meas = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', raw, '-vn', '-af', f'{ASYNC},{VOICE_CHAIN},loudnorm={LOUD}:print_format=json',
                           '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
    ln = (f"loudnorm={LOUD}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-vn', '-af', f'{ASYNC},{VOICE_CHAIN},{ln}', '-ar', '48000', aout])
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-i', aout, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le', out.replace('.mp4', '.mkv')])
    os.replace(out.replace('.mp4', '.mkv'), out)
    print('render: base done'); return out

PIP_W, PIP_H, PIP_M = 370, 340, (28, 20)   # cut-out pip incl. 20px glow padding, margins from the edge (x, y)
KEY = True          # the recording has a pure-black background: key it out, put the backdrop behind, cut-out pip
KEY_CROP = (990, 900, 465, 180)    # w, h, x, y of the head-and-shoulders crop used for the pip (source is centered)
SLIDE_IN, SLIDE_OUT = 0.35, 0.30
FACE_DX = 0         # talking head stays centered (callouts on the right, receipts panel on the left)

# the receipts panel: while it's just you on screen, the left side keeps a running list of the numbers so far.
# a receipt is filed when the graphic that shows it ends. (event id -> big, small, colour)
RECEIPTS = {
    'six_cents': ('6¢', 'what a god pack adds to a $5.49 pack', 'BLUE'),
    'ratio_127': ('$1.35', 'of cards per $1 of play box, on paper', 'BLUE'),
    'bulk_396': ('395 of 420', 'cards in a box are under a dollar', 'MUTED'),
    'cash_46': ('49¢', 'per $1 if you actually sell it all', 'AQUA'),
    'one_in_100': ('~1 in 70', 'boxes pay for themselves in cash', 'AQUA'),
    'anim_clock': ('~5 hrs', 'to turn one box into about $50', 'YELLOW'),
    'chart02': ('every set', 'collector boxes cost more than the cards inside', 'MAGENTA'),
    'anim_reveal': ('$65', 'the average god pack', 'YELLOW'),
    'gp_23': ('23 boxes', 'for a coin flip at seeing one god pack', 'RED'),
    'gp_50': ('$51', 'the median god pack. half are worth less', 'YELLOW'),
    'chart11': ('0 of 62', 'boxes god packs would ever have flipped to a win', 'RED'),
    'net_80': ('−$0.85', 'net change per 2027 collector booster', 'RED'),
    'cut_cash': ('3¢', 'what the three cut cards sell for, per pack', 'MAGENTA'),
    'chart06': ('1 in 8', 'foil-rare rate the new slot needs to break even', 'BLUE'),
}
PANEL_ROWS = 4
ANIM_BEAT = 0.8         # every animation gets this long on its finished frame before the edit moves on
ANIM_MAX_SPEED = 1.35   # an animation that doesn't fit its slot plays up to this much faster, then the talking pauses for the rest

# caption clean-up (whisper's spacing around numbers, and the names it hears wrong). applied to the delivered .srt only.
CAPTION_FIXES = [
    (r'\$0 ?\.(\d\d)', r'\1¢'), (r'(\d) \.(\d)', r'\1.\2'), (r'(\d) %', r'\1%'), (r'(\d) ,(\d{3})', r'\1,\2'),
    (r'\ba dollar 35\b', 'about $1.35'), (r'\bdollar 35\b', '$1.35'), (r'Karloff', 'Karlov'), (r'\bI Opened\b', 'I opened'),
    (r'395 of them, comments\.', '395 of them, commons.'), (r'for bulk for \$4 for \$1000\.', 'for bulk, like $4 per 1,000.'),
    (r'\breality fracture\b', 'Reality Fracture'), (r'\btheros\b', 'Theros'), (r'\bPokemon', 'Pokémon'),
]
KEY_T = 16         # luma above this counts as you (the background is digital black: exactly Y=16 in video range)
_corner_cache = {}
# hand-placed spots where the automatic search gets it wrong (it can't tell a lone outlier dot matters)
PIP_SPOT = {'02_collector_boxes_ev_vs_price.png': '1060,720'}

def pip_corner(asset):
    """find a spot for the face that covers as little of the graphic as possible. looks at the graphic's last
    frame (animations fill up as they play), marks every 16px block that has text or ink in it, and slides the pip
    down the right edge and along the bottom edge. bottom-right wins ties. returns 'x,y' in pixels."""
    a = asset_path(asset)
    if asset in PIP_SPOT: return PIP_SPOT[asset]
    if a in _corner_cache: return _corner_cache[a]
    mx, my = PIP_M; dflt = f'{W - mx - PIP_W},{H - my - PIP_H}'
    try:
        from PIL import Image
        import numpy as np
        if a.endswith('.mp4'):
            fr = wpath('_corner.png')
            run(['ffmpeg', '-y', '-v', 'error', '-sseof', '-0.5', '-i', a, '-frames:v', '1', '-s', f'{W}x{H}', fr])
            im = Image.open(fr).convert('RGB')
        else:
            im = Image.open(a).convert('RGB').resize((W, H))
        px = np.asarray(im).astype(int); bg = np.median(px.reshape(-1, 3), axis=0)
        busy = (np.abs(px - bg).sum(axis=2) > 60)
        B = 16; blk = busy[:H // B * B, :W // B * B].reshape(H // B, B, W // B, B).any(axis=(1, 3))
        def score(x, y): return blk[y // B:(y + PIP_H) // B + 1, x // B:(x + PIP_W) // B + 1].mean()
        # right edge, but never across the callout band (y 400-650), where the big numbers go
        cands = [(W - mx - PIP_W, y) for y in [y for y in range(96, H - my - PIP_H + 1, 16) if y + PIP_H <= 400 or y >= 656]] + \
                [(x, H - my - PIP_H) for x in range(mx, W - mx - PIP_W + 1, 16)]
        best = min(cands, key=lambda c: (round(score(*c), 2), (W - c[0]) + (H - c[1])))
        if score(*best) > score(W - mx - PIP_W, H - my - PIP_H) - 0.03: best = (W - mx - PIP_W, H - my - PIP_H)
        c = f'{best[0]},{best[1]}'
    except Exception as e:
        print('pip spot check failed for', asset, e); c = dflt
    _corner_cache[a] = c; return c

def pip_xy(c): return c.split(',')

def receipt_states(pl):
    """[(start, end, png)] for the receipts panel, from the first chapter tag to the end card."""
    import graphics as G
    from PIL import ImageDraw
    ev = pl['events']; tags = [e for e in ev if e['type'] == 'tag']
    if not tags: return []
    t0 = tags[0]['start']; t1 = pl['duration'] - ((pl.get('end_card') or {}).get('dur', 0))
    trig = sorted([(e['end'] + 0.15, 'r', e['id']) for e in ev if e['id'] in RECEIPTS] + [(e['start'], 't', e['id']) for e in tags])
    states, rows, chap = [], [], 0
    for t, kind, eid in trig:
        if kind == 'r': rows.append(RECEIPTS[eid])
        else: chap = [x['id'] for x in tags].index(eid) + 1
        states.append((max(t, t0), list(rows), chap))
    out = []
    for j, (t, rws, ch) in enumerate(states):
        end = states[j + 1][0] if j + 1 < len(states) else t1
        if end <= max(t, t0) + 0.05 or not rws: continue
        f = wpath(f'panel_{pl["cut"]}_{j:02d}.png')
        if not os.path.exists(f):
            img = G.blank(); d = ImageDraw.Draw(img)
            fh, fb, fs = G.font('semi', 22), G.font('black', 56), G.font('med', 24)
            show = rws[-PANEL_ROWS:]; x0, y0, w = 50, 230, 470
            def wrap(text):
                lines, cur = [], ''
                for word in text.split():
                    if G.tw(d, (cur + ' ' + word).strip(), fs)[0] > w - 84: lines.append(cur); cur = word
                    else: cur = (cur + ' ' + word).strip()
                return lines + [cur]
            heights = [68 + 31 * len(wrap(sm)) + 20 for _, sm, _ in show]
            G.plate(img, (x0, y0, x0 + w, y0 + 78 + sum(heights)), alpha=205)
            d = ImageDraw.Draw(img)
            d.text((x0 + 32, y0 + 26), 'THE RECEIPTS', font=fh, fill=G.YELLOW)
            for q in range(len(tags)):   # chapter progress
                bx = x0 + w - 28 - (len(tags) - q) * 22
                d.rounded_rectangle((bx, y0 + 36, bx + 15, y0 + 42), radius=3, fill=G.YELLOW if q < ch else (70, 70, 66))
            y = y0 + 78
            for r, ((big, sm, col), hh) in enumerate(zip(show, heights)):
                newest = r == len(show) - 1; c = getattr(G, col)
                dim = (lambda rgb: rgb) if newest else (lambda rgb: tuple(int(v * 0.5 + 26 * 0.5) for v in rgb))
                d.rectangle((x0 + 32, y + 6, x0 + 38, y + hh - 18), fill=dim(c))
                d.text((x0 + 56, y), big, font=fb, fill=dim(c))
                for li, line in enumerate(wrap(sm)): d.text((x0 + 58, y + 70 + 31 * li), line, font=fs, fill=dim(G.INK2))
                y += hh
            img.crop(img.getbbox()).save(f); open(f + '.xy', 'w').write('%d,%d' % img.getbbox()[:2])   # small overlay = fast
        out.append((max(t, t0), end, f, end < t1))
    return out

def render_piece(pl, base, i, n, pip, burn, music):
    s = i * PIECE; e = min(pl['duration'], s + PIECE); o = wpath(f'out_{pl["cut"]}_{i:03d}.mkv')
    if os.path.exists(o): return o
    ev = [x for x in pl['events'] if x['end'] > s and x['start'] < e]
    inputs = ['-ss', f'{s:.3f}', '-to', f'{e:.3f}', '-i', base]; fc = []; k = 1
    if KEY:
        # matte from the pure-black background: anything above near-black is you. close small holes (dark hair),
        # pull the edge in a pixel so no black fringe, then soften it.
        inputs += ['-loop', '1', '-i', os.path.join(GFX, 'backdrop.png'), '-loop', '1', '-i', os.path.join(GFX, 'pip_fade.png')]; k = 3
        fc.append(f"[0:v]format=yuv420p,split=2[src][msrc];[msrc]extractplanes=y,scale={W // 2}:{H // 2},lut=y='if(gt(val,{KEY_T}),255,0)',"
                  f"dilation,erosion,erosion,gblur=sigma=0.8,scale={W}:{H}[mask];"
                  "[src][mask]alphamerge,split=2[cut][pp];"
                  f"[1:v]scale={W}:{H},fps={FPS},format=yuv420p[plate];[plate][cut]overlay=x={FACE_DX}:y=0:shortest=1:format=auto[bg]")
    else:
        fc.append('[0:v]split=2[bg][pp]')
    cur = 'bg'; pipwin = {}
    if KEY:
        for a, b, f, linger in receipt_states(pl):
            if b <= s or a >= e: continue
            st, en = max(0.0, a - s), min(e, b + (0.35 if linger else 0)) - s       # each state lingers under the next while it fades in
            inputs += ['-loop', '1', '-t', f'{en + 0.1:.3f}', '-i', f]
            fade_in = f",fade=in:st={st:.3f}:d=0.35:alpha=1" if a >= s else ''
            fc.append(f"[{k}:v]format=rgba{fade_in}[o{k}]")
            px, py = open(f + '.xy').read().split(',')
            fc.append(f"[{cur}][o{k}]overlay={px}:{py}:enable='between(t,{st:.3f},{en:.3f})':eof_action=pass[v{k}]"); cur = f'v{k}'; k += 1
    def win(x): return f"between(t,{max(0, x['start'] - s):.3f},{x['end'] - s:.3f})"
    # one face at a time: a b-roll's pip window stops where the next b-roll starts
    br = sorted([x for x in ev if x['type'] == 'broll'], key=lambda x: x['start'])
    pip_end = {id(x): min([x['end']] + [y['start'] for y in br if y['start'] > x['start']]) for x in br}
    # draw every b-roll first, then tags/callouts/badges on top: a chapter tag that starts with a chart must not hide under it
    for x in sorted(ev, key=lambda x: (x['type'] != 'broll', x['start'])):
        a = asset_path(x['asset']); st = max(0.0, x['start'] - s); en = x['end'] - s; dur = en - st
        if x['type'] == 'broll':
            if a.endswith('.mp4'):
                sp = x.get('speed', 1.0)
                skip = max(0.0, s - x['start']) * sp  # piece starts mid-clip (in the clip's own time)
                skip = min(skip, max(0.0, duration(a) - 0.1))   # already finished: start on its last frame (seeking past the end crashes ffmpeg)
                inputs += ['-ss', f'{skip:.3f}', '-i', a]
                fc.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{sp},scale={W}:{H},fps={FPS},tpad=stop_mode=clone:stop_duration=60,trim=0:{dur:.3f},setpts=PTS-STARTPTS+{st:.3f}/TB,"
                          f"fade=in:st={st:.3f}:d=0.25:alpha=1,format=yuva420p[b{k}]")
            else:
                inputs += ['-loop', '1', '-t', f'{dur + 0.1:.3f}', '-i', a]
                fc.append(f"[{k}:v]scale={W}:{H},fps={FPS},format=yuva420p,setpts=PTS-STARTPTS+{st:.3f}/TB,fade=in:st={st:.3f}:d=0.25:alpha=1[b{k}]")
            fc.append(f"[{cur}][b{k}]overlay=0:0:enable='{win(x)}':eof_action=pass[v{k}]"); cur = f'v{k}'
            if pip and x.get('pip', True): pipwin.setdefault(pip_corner(x['asset']), []).append((max(0, x['start'] - s), pip_end[id(x)] - s, x['start'] < s))
        else:   # png overlays: callout, tag, lower, badge
            inputs += ['-loop', '1', '-t', f'{dur + 0.1:.3f}', '-i', a]
            fo = max(st, en - 0.3)
            fc.append(f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{st:.3f}/TB,fade=in:st={st:.3f}:d=0.25:alpha=1,fade=out:st={fo:.3f}:d=0.3:alpha=1[o{k}]")
            fc.append(f"[{cur}][o{k}]overlay=0:0:enable='{win(x)}':eof_action=pass[v{k}]"); cur = f'v{k}'
        k += 1
    if pipwin:
        cs = sorted(pipwin); lab = ''.join(f'[pip{j}]' for j in range(len(cs)))
        if KEY:
            cw, ch, cx, cy = KEY_CROP; pw, ph = PIP_W - 40, PIP_H - 40
            # head and shoulders, torso fading out, a soft light rim so dark hair reads against dark charts
            fc.append(f"[pp]crop={cw}:{ch}:{cx}:{cy},scale={pw}:{ph},format=yuva420p,split=2[pc][pa0];[pa0]alphaextract[pa1];"
                      f"[2:v]scale={pw}:{ph},fps={FPS},format=gray[fd];[pa1][fd]blend=all_mode=multiply:shortest=1[pa2];"
                      f"[pc][pa2]alphamerge,pad={PIP_W}:{PIP_H}:20:20:color=black@0,split=2[pk][pr0];"
                      f"[pr0]alphaextract,gblur=sigma=9,lut=y='val*0.30'[pr1];color=c=0xdfe6ef:s={PIP_W}x{PIP_H}:r={FPS}[rimc];"
                      f"[rimc][pr1]alphamerge[rim];[rim][pk]overlay=shortest=1:format=auto" + (f",split={len(cs)}{lab}" if len(cs) > 1 else '[pip0]'))
        else:
            fc.append(f"[pp]scale=448:-2,pad=iw+8:ih+8:4:4:color=0x1a1a19" + (f",split={len(cs)}{lab}" if len(cs) > 1 else '[pip0]'))
        for j, c in enumerate(cs):
            x0, y0 = map(int, pip_xy(c)); wins = []
            for a, b, cont in pipwin[c]:   # no face during an animation pause (you're not talking): slide out, slide back in
                for h0, h1 in pl.get('holds', []):
                    h0, h1 = h0 - s, h1 - s
                    if a < h0 < b: wins.append((a, h0, cont)); a, cont = min(b, h1), False
                    elif h0 <= a < h1: a, cont = min(b, h1), False
                if b - a > 0.3: wins.append((a, b, cont))
            if not wins: fc.append(f'[pip{j}]nullsink'); continue
            en = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b, _ in wins)
            # keyframes: ease in from off the right edge, ease back out at the end of the window
            terms = []
            for a, b, cont in wins:
                if not cont: terms.append(f'if(between(t,{a:.3f},{a + SLIDE_IN:.3f}),pow(1-(t-{a:.3f})/{SLIDE_IN},3),0)')
                terms.append(f'if(between(t,{b - SLIDE_OUT:.3f},{b:.3f}),pow((t-{b - SLIDE_OUT:.3f})/{SLIDE_OUT},3),0)')
            xexpr = f"{x0}+({W - x0})*({'+'.join(terms) or '0'})"
            fc.append(f"[{cur}][pip{j}]overlay=x='{xexpr}':y={y0}:eval=frame:enable='{en}'[vp{j}]"); cur = f'vp{j}'
    else:
        fc.append('[pp]nullsink')
    if burn:
        # caption timestamps are absolute; shift the stream onto the absolute clock, burn, shift back
        ass_file = wpath('captions_%s.ass' % pl['cut'])
        fc.append(f"[{cur}]setpts=PTS+{s:.3f}/TB,subtitles={ass_file}:fontsdir={FONTS},setpts=PTS-{s:.3f}/TB[vc]"); cur = 'vc'
    amap = '0:a'
    if music:
        inputs += ['-ss', f'{s:.3f}', '-stream_loop', '-1', '-i', music]
        fc.append(f"[{k}:a]volume=-22dB,aresample=48000[mus];[0:a]asplit=2[vo][sc];[mus][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];[vo][duck]amix=inputs=2:duration=first:normalize=0[am]")
        amap = '[am]'
    cmd = ['ffmpeg', '-y', '-v', 'error'] + inputs + ['-filter_complex', ';'.join(fc), '-map', f'[{cur}]', '-map', amap,
           '-t', f'{e - s:.3f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-profile:v', 'high', '-g', str(FPS // 2), '-bf', '2',
           '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'pcm_s16le', o + '.tmp.mkv']
    run(cmd); os.replace(o + '.tmp.mkv', o); return o

def render(src, cut, pip, burn, music, budget=150):
    pl = json.load(open(wpath(f'plan_{cut}.json'))); t0 = time.time()
    # if the plan or the options changed since the last render, throw away the cached pieces
    import hashlib, glob
    # plan changed -> rebuild everything; only the overlay options/layout changed -> just redo the finished pieces
    stamp = hashlib.md5(json.dumps([pl, FPS, VOICE_CHAIN, LOUD, 'frame-grid-v3'], sort_keys=True).encode()).hexdigest()
    ostamp = hashlib.md5(json.dumps([pl, pip, burn, music, 'overlays-v9', FPS, KEY, FACE_DX, RECEIPTS], sort_keys=True).encode()).hexdigest()
    sf = wpath(f'render_stamp_{cut}.txt'); of = wpath(f'overlay_stamp_{cut}.txt')
    if not os.path.exists(sf) or open(sf).read() != stamp:
        for pat in ('out_*', 'base_*', 'card_*', 'seg_*', 'trim*', 'base_raw.mkv'):
            for f in glob.glob(wpath(pat)): os.remove(f)
        open(sf, 'w').write(stamp)
    if not os.path.exists(of) or open(of).read() != ostamp:
        for f in glob.glob(wpath(f'out_{cut}_*')): os.remove(f)
        open(of, 'w').write(ostamp)
    base = build_base(pl, budget)
    if not base: return False
    n = math.ceil(pl['duration'] / PIECE); outs = []
    for i in range(n):
        o = wpath(f'out_{cut}_{i:03d}.mkv')
        if not os.path.exists(o) and time.time() - t0 > budget:
            print(f'render: {i}/{n} pieces done, run again to continue'); return False
        outs.append(render_piece(pl, base, i, n, pip, burn, music)); print(f'render: piece {i + 1}/{n}')
    with open(wpath(f'out_list_{cut}.txt'), 'w') as f:
        for o in outs: f.write(f"file '{o}'\n")
    final = os.path.join(os.path.dirname(os.path.abspath(src)), f'{os.path.splitext(os.path.basename(src))[0]}_edit_{cut}.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', wpath(f'out_list_{cut}.txt'), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '384k', '-ar', '48000', '-movflags', '+faststart', final])
    srt = open(wpath(f'captions_{cut}.srt')).read()
    for a, b in CAPTION_FIXES: srt = re.sub(a, b, srt)
    open(final.replace('.mp4', '.srt'), 'w').write(srt)
    print(f'render: DONE -> {final}  ({duration(final) / 60:.1f} min)'); return True

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('step', choices=['transcribe', 'plan', 'render', 'all']); ap.add_argument('src')
    ap.add_argument('--cut', default='a'); ap.add_argument('--no-pip', action='store_true'); ap.add_argument('--burn-captions', action='store_true')
    ap.add_argument('--music'); ap.add_argument('--max-gap', type=float, default=0.45); ap.add_argument('--budget', type=float, default=150); ap.add_argument('--fps', type=int, default=60)
    a = ap.parse_args(); FPS = a.fps
    # one work folder per recording, so a new take never reuses an old transcript
    WORK = os.path.join(WORK, re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.splitext(os.path.basename(a.src))[0])); os.makedirs(WORK, exist_ok=True)
    if a.step in ('transcribe', 'all') and not transcribe(a.src, budget=a.budget): sys.exit(3)
    if a.step in ('plan', 'all'): plan(a.src, a.cut, a.max_gap)
    if a.step in ('render', 'all') and not render(a.src, a.cut, not a.no_pip, a.burn_captions, a.music, budget=a.budget): sys.exit(3)
