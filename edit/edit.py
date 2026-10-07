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
FPS = 30; W, H = 1920, 1080

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
def norm(t): return re.sub(r"[^a-z0-9$%¢ ]", '', t.lower().replace('-', ' ').replace('’', "'").replace("'", ''))

def find_retakes(words):
    cuts = []
    for k, w in enumerate(words):
        if norm(w['w']).replace(' ', '') in ('redo',) or (norm(w['w']) == 're' and k + 1 < len(words) and norm(words[k + 1]['w']) == 'do'):
            end_k = k + (1 if norm(w['w']) == 're' else 0)
            j = k - 1
            while j > 0:
                prev = words[j - 1]
                if re.search(r'[.?!]$', prev['w']) or words[j]['s'] - prev['e'] > 1.0: break
                j -= 1
            cuts.append((words[max(j, 0)]['s'] - 0.05, words[end_k]['e'] + 0.1, ' '.join(x['w'] for x in words[j:end_k + 1])))
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
        else:
            pick = max(cands) if cands else (0, None, None)
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
    cuts = find_retakes(words); clean = drop_cut_words(words, cuts)
    marks = align(clean, cues)
    segs = keep_segments(clean, total, max_gap); m, tdur = make_mapper(segs)
    # inserts (full-frame cards that add time) are placed after their phrase; build the final clock
    # an insert goes in the pause after its phrase. pauses get trimmed, so never let it land past the next word.
    def insert_at(c):
        t0 = m(c['we']); nxt = next((w for w in clean if w['s'] > c['we'] + 0.01), None)
        lim = m(nxt['s']) - 0.05 if nxt else t0 + 1
        return max(t0 + 0.1, min(t0 + c.get('offset', 0.3), lim))
    inserts = sorted([(insert_at(c), c) for c in marks if c['matched'] and c['type'] == 'insert'], key=lambda x: x[0])
    end_card = [c for c in cues if c['type'] == 'endcard']
    def final_t(t):  # trimmed time -> final time (after inserts before t)
        return t + sum(c['dur'] for at, c in inserts if at <= t)
    events = []
    for c in marks:
        if not c['matched'] or c['type'] in ('insert', 'mark', 'endcard'): continue
        start = final_t(m(c['ws'] if c.get('anchor', 'start') == 'start' else c['we'])) + c.get('offset', 0)
        if c.get('until'):
            nxt = next((x for x in marks if x['id'] == c['until'] and x['matched']), None)
            end = final_t(m(nxt['ws'])) - 0.15 if nxt else start + c.get('max', 8)
        else: end = start + c.get('dur', 4)
        if c.get('max'): end = min(end, start + c['max'])
        if c.get('min'): end = max(end, start + c['min'])
        # overlays never sit on top of a full-frame card (title insert, end card)
        for at, ic in inserts:
            a0 = final_t(at) - ic['dur']; a1 = a0 + ic['dur']
            if a0 - 0.01 <= start < a1: end += a1 - start; start = a1
            elif start < a0 < end: end = a0
        end = min(end, final_t(tdur) - 0.1)
        if end - start < 0.5: continue
        events.append({'id': c['id'], 'type': c['type'], 'asset': c['asset'], 'start': round(start, 3), 'end': round(end, 3), 'pip': c.get('pip', True)})
    final_dur = final_t(tdur) + sum(c['dur'] for c in end_card)
    # captions on the final clock
    cap = []
    for w in clean:
        cap.append({'w': w['w'], 's': final_t(m(w['s'])), 'e': final_t(m(w['e']))})
    plan = {'src': os.path.abspath(src), 'cut': cut, 'segments': segs, 'inserts': [{'at': round(at, 3), 'asset': c['asset'], 'dur': c['dur']} for at, c in inserts],
            'end_card': end_card[0] if end_card else None, 'events': sorted(events, key=lambda e: e['start']), 'duration': round(final_dur, 2), 'captions': cap}
    json.dump(plan, open(wpath(f'plan_{cut}.json'), 'w'), indent=1)
    write_captions(cap, wpath(f'captions_{cut}.srt'), wpath(f'captions_{cut}.ass'))
    # human-readable report + youtube chapters
    L = [f'plan for cut {cut}: {os.path.basename(src)}', f'recorded {total / 60:.1f} min -> edit {final_dur / 60:.1f} min  ({total - tdur:.0f} s of pauses and retakes removed)', '']
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
                 'tag_b5.png': 'pricing a god pack', 'tag_b6.png': 'the foil change is the real ev story', 'tag_b7.png': 'collector shrink', 'tag_b8.png': 'behind the counter'}

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
        a, b = g[0][0], g[-1][1]
        sel = '+'.join(f'between(t,{x - a:.3f},{y - a:.3f})' for x, y in g)
        vf = (f"select='{sel}',setpts=N/FRAME_RATE/TB,scale={W}:{H}:force_original_aspect_ratio=decrease,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a19,fps={FPS},format=yuv420p")
        af = f"aselect='{sel}',asetpts=N/SR/TB,aresample=48000"
        run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{a:.3f}', '-to', f'{b + 0.05:.3f}', '-i', src, '-vf', vf, '-af', af,
             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'pcm_s16le', o.replace('.mp4', '.mkv')])
        os.replace(o.replace('.mp4', '.mkv'), o)
        print(f'render: trimmed piece {i + 1}/{len(parts)}')
    # 3b. one concat list: trimmed pieces split at inserts + insert cards + end card
    joined = wpath('trimmed_all.mkv')
    if not os.path.exists(joined):
        with open(wpath('trim_list.txt'), 'w') as f:
            for o in trimmed: f.write(f"file '{o}'\n")
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', wpath('trim_list.txt'), '-c', 'copy', joined])
    cards = [(x['at'], x['asset'], x['dur']) for x in pl['inserts']]
    clips = []; last = 0.0; jd = duration(joined)
    def card_clip(asset, dur, name):
        o = wpath(name)
        if not os.path.exists(o):
            run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-t', f'{dur}', '-i', asset_path(asset), '-f', 'lavfi', '-t', f'{dur}', '-i', 'anullsrc=r=48000:cl=mono',
                 '-vf', f'scale={W}:{H},fps={FPS},format=yuv420p,fade=in:st=0:d=0.25,fade=out:st={dur - 0.3}:d=0.3', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16',
                 '-c:a', 'pcm_s16le', '-shortest', o])
        return o
    for k, (at, asset, dur) in enumerate(cards):
        o = wpath(f'seg_{k:02d}.mkv')
        if not os.path.exists(o): run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{last:.3f}', '-to', f'{at:.3f}', '-i', joined, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'pcm_s16le', o])
        clips += [o, card_clip(asset, dur, f'card_{k:02d}.mkv')]; last = at
    o = wpath('seg_last.mkv')
    if not os.path.exists(o): run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{last:.3f}', '-i', joined, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'pcm_s16le', o])
    clips.append(o)
    if pl['end_card']: clips.append(card_clip(pl['end_card']['asset'], pl['end_card']['dur'], 'card_end.mkv'))
    with open(wpath('base_list.txt'), 'w') as f:
        for c in clips: f.write(f"file '{c}'\n")
    raw = wpath('base_raw.mkv')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', wpath('base_list.txt'), '-c', 'copy', raw])
    # 3c. audio clean-up once, on the whole thing (needs to see all of it for loudness)
    aout = wpath('voice.wav')
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-vn', '-af', 'highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,'
         'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', aout])
    run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-i', aout, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'pcm_s16le', out.replace('.mp4', '.mkv')])
    os.replace(out.replace('.mp4', '.mkv'), out)
    print('render: base done'); return out

def render_piece(pl, base, i, n, pip, burn, music):
    s = i * PIECE; e = min(pl['duration'], s + PIECE); o = wpath(f'out_{pl["cut"]}_{i:03d}.mp4')
    if os.path.exists(o): return o
    ev = [x for x in pl['events'] if x['end'] > s and x['start'] < e]
    inputs = ['-ss', f'{s:.3f}', '-to', f'{e:.3f}', '-i', base]; fc = []; k = 1
    fc.append('[0:v]split=2[bg][pp]'); cur = 'bg'; pipwin = []
    def win(x): return f"between(t,{max(0, x['start'] - s):.3f},{x['end'] - s:.3f})"
    for x in ev:
        a = asset_path(x['asset']); st = max(0.0, x['start'] - s); en = x['end'] - s; dur = en - st
        if x['type'] == 'broll':
            if a.endswith('.mp4'):
                skip = max(0.0, s - x['start'])  # piece starts mid-clip
                inputs += ['-ss', f'{skip:.3f}', '-i', a]
                fc.append(f"[{k}:v]scale={W}:{H},fps={FPS},tpad=stop_mode=clone:stop_duration=60,trim=0:{dur:.3f},setpts=PTS-STARTPTS+{st:.3f}/TB,"
                          f"fade=in:st={st:.3f}:d=0.25:alpha=1,format=yuva420p[b{k}]")
            else:
                inputs += ['-loop', '1', '-t', f'{dur + 0.1:.3f}', '-i', a]
                fc.append(f"[{k}:v]scale={W}:{H},fps={FPS},format=yuva420p,setpts=PTS-STARTPTS+{st:.3f}/TB,fade=in:st={st:.3f}:d=0.25:alpha=1[b{k}]")
            fc.append(f"[{cur}][b{k}]overlay=0:0:enable='{win(x)}':eof_action=pass[v{k}]"); cur = f'v{k}'
            if pip and x.get('pip', True): pipwin.append(win(x))
        else:   # png overlays: callout, tag, lower, badge
            inputs += ['-loop', '1', '-t', f'{dur + 0.1:.3f}', '-i', a]
            fo = max(st, en - 0.3)
            fc.append(f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{st:.3f}/TB,fade=in:st={st:.3f}:d=0.25:alpha=1,fade=out:st={fo:.3f}:d=0.3:alpha=1[o{k}]")
            fc.append(f"[{cur}][o{k}]overlay=0:0:enable='{win(x)}':eof_action=pass[v{k}]"); cur = f'v{k}'
        k += 1
    if pipwin:
        en = '+'.join(pipwin)
        fc.append(f"[pp]scale=448:-2,pad=iw+8:ih+8:4:4:color=0x1a1a19[pip]")
        fc.append(f"[{cur}][pip]overlay=W-w-48:H-h-56:enable='{en}'[vp]"); cur = 'vp'
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
           '-t', f'{e - s:.3f}', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', o + '.tmp.mp4']
    run(cmd); os.replace(o + '.tmp.mp4', o); return o

def render(src, cut, pip, burn, music, budget=150):
    pl = json.load(open(wpath(f'plan_{cut}.json'))); t0 = time.time()
    # if the plan or the options changed since the last render, throw away the cached pieces
    import hashlib, glob
    stamp = hashlib.md5(json.dumps([pl, pip, burn, music], sort_keys=True).encode()).hexdigest()
    sf = wpath(f'render_stamp_{cut}.txt')
    if not os.path.exists(sf) or open(sf).read() != stamp:
        for pat in ('out_*', 'base_*', 'card_*', 'seg_*', 'trim*', 'base_raw.mkv'):
            for f in glob.glob(wpath(pat)): os.remove(f)
        open(sf, 'w').write(stamp)
    base = build_base(pl, budget)
    if not base: return False
    n = math.ceil(pl['duration'] / PIECE); outs = []
    for i in range(n):
        o = wpath(f'out_{cut}_{i:03d}.mp4')
        if not os.path.exists(o) and time.time() - t0 > budget:
            print(f'render: {i}/{n} pieces done, run again to continue'); return False
        outs.append(render_piece(pl, base, i, n, pip, burn, music)); print(f'render: piece {i + 1}/{n}')
    with open(wpath(f'out_list_{cut}.txt'), 'w') as f:
        for o in outs: f.write(f"file '{o}'\n")
    final = os.path.join(os.path.dirname(os.path.abspath(src)), f'{os.path.splitext(os.path.basename(src))[0]}_edit_{cut}.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', wpath(f'out_list_{cut}.txt'), '-c', 'copy', '-movflags', '+faststart', final])
    for ext in ('srt',):
        run(['cp', wpath(f'captions_{cut}.{ext}'), final.replace('.mp4', f'.{ext}')])
    print(f'render: DONE -> {final}  ({duration(final) / 60:.1f} min)'); return True

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('step', choices=['transcribe', 'plan', 'render', 'all']); ap.add_argument('src')
    ap.add_argument('--cut', default='a'); ap.add_argument('--no-pip', action='store_true'); ap.add_argument('--burn-captions', action='store_true')
    ap.add_argument('--music'); ap.add_argument('--max-gap', type=float, default=0.45); ap.add_argument('--budget', type=float, default=150)
    a = ap.parse_args()
    # one work folder per recording, so a new take never reuses an old transcript
    WORK = os.path.join(WORK, re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.splitext(os.path.basename(a.src))[0])); os.makedirs(WORK, exist_ok=True)
    if a.step in ('transcribe', 'all') and not transcribe(a.src, budget=a.budget): sys.exit(3)
    if a.step in ('plan', 'all'): plan(a.src, a.cut, a.max_gap)
    if a.step in ('render', 'all') and not render(a.src, a.cut, not a.no_pip, a.burn_captions, a.music, budget=a.budget): sys.exit(3)
