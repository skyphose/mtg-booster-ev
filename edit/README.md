# edit/: talking head in, finished video out

i record myself reading the script in one take. `edit.py` takes it from there:

- transcribes it with word timestamps
- finds the cue lines
- cuts my retakes and dead air
- drops in the charts, animations, callouts and chapter tags
- shrinks my face into the corner while a chart is up
- cleans and levels the audio: 80 Hz rumble cut, a little presence and air, light de-ess and compression, two-pass loudnorm to -14 LUFS / -1.5 dBTP (what youtube normalizes to). no broadband denoiser: it was dulling the voice and the mic's gate already keeps pauses quiet
- writes captions and the youtube chapter list

nothing in here touches the model. it only reads the pngs and mp4s in `results/` plus the graphics in `edit/gfx/`.

## setup (once)

```bash
# ffmpeg 4.4 or newer
pip install faster-whisper rapidfuzz pillow numpy

# speech model, ~480 MB. any copy of systran/faster-whisper-small.en works:
# config.json, model.bin, tokenizer.json, vocabulary.txt go in
#   edit/models/faster-whisper-small.en/

python3 edit/graphics.py      # rebuilds edit/gfx/ (already committed, only needed if you change a number)
python3 edit/make_cues.py     # rebuilds cues_a.json / cues_b.json from the cue lists
```

## recording

**camera**
- landscape, 1080p or 4k, 30fps. phone is fine.
- face centered or a little left.
- the edit puts stuff in three places, so keep them free of anything you care about:
  - **right third, middle**: big number callouts
  - **top left**: chapter tags
  - **bottom left**: name lower-third (first ~20 seconds only)
- record on a pure-black background (a camera app's background removal works): the edit keys the black out, puts a soft backdrop behind you, and when a chart is up you slide in as a cut-out (head and shoulders, faded torso, light rim) instead of a box. `KEY = False` in `edit.py` turns that off.
- while it's just you on screen, the left side carries **the receipts**: a running list of the numbers so far. each one gets filed there when its callout or graphic ends; the newest is lit, older ones dim, and dashes up top track the chapter. edit `RECEIPTS` in `edit.py` to change what gets filed.
- during charts, your video shrinks into a corner. the tool picks the spot on each graphic that covers the least (usually bottom right, never over the callout band); `PIP_SPOT` in `edit.py` pins it by hand for a graphic where it guesses wrong.

**audio**
- this matters more than the camera. use a lav or a mic within arm's length, in a room with soft stuff in it.
- turn off the fridge / hvac if you can. the cleanup removes hiss, not a dishwasher.

**reading**
- one file, one take, start to finish. stopping and starting is fine, just don't stop the recording.
- **flubbed a line?** say "**redo**" and restart that sentence, or say "**let's restart**" and go back as far as you like (up to ~90 seconds): the tool finds where the repeated line first started and keeps only the clean take.
- don't worry about pauses. anything longer than 0.45s gets trimmed down.
- **pause for a beat after "six cents"** in the cold open. that's where the title card goes.
- ad-lib anywhere you want, **except on the cue lines below**. those are what the edit listens for, so say them close to word for word. the matcher is fuzzy, so "here's what surprised me" vs "here's what surprised me most" is fine.

### cue lines: script a (public cut)

| say this | you get |
|---|---|
| i work at a game store | name lower-third |
| six cents *(pause)* | "six cents" callout, then the title card |
| here's what surprised me | part 1 tag |
| take every play booster box since | chart 01 |
| of cards in it for every dollar the box sells for | $1.35 callout |
| so the box is worth more than it costs | chart 01 ends |
| here's one box of reality fracture | part 2 tag + box-opening animation |
| of them are under a dollar | 395 of 420 callout |
| same product, four thousand simulated boxes | histogram animation |
| cents on the dollar | 49¢ callout |
| i did that for every set | chart 04 |
| pays for itself in cash | ~1 in 70 callout |
| nobody puts in the thumbnail | where-the-ev-sits animation |
| about five hours of work | hours callout |
| the money's gone when you crack the plastic | animation ends |
| the median collector box sells for about one and a half | chart 02 |
| this isn't a bad set problem | part 3 tag + ten-years animation |
| now the god pack | part 4 tag + chart 05 |
| if the celebration card is good | $65 callout |
| of the pack price | six cents callout again |
| chance of having one | god pack odds animation |
| if you want a coin flip at seeing one | 23 boxes callout |
| is the average | animation ends |
| the median one is | $51 callout |
| what if god packs had always been a thing | "what if" tag + chart 11 |
| the most it ever adds is about | ~$2 callout |
| not one box in ten years goes from losing to winning | 0 of 62 callout |
| same post, two paragraphs down | part 5 tag |
| price per card goes up | chart 07 + 15 → 12 callout |
| your collector booster got about | −$0.85 callout |
| run the same cut on every collector booster | chart 12 |
| in cash, those three cards are worth about a dime | 3¢ callout |
| it comes down to one number wizards | chart 06 |
| if the new rate is better than one in | 1 in 8 callout |
| one thing from my side of the counter | part 6 tag + chart 08 |
| buy singles for the deck | verdict callout |
| public github repo | repo badge until the end card |

### extra cue lines: script b (nerd cut)

the nerd cut reads script a's parts plus the new bits, in the order the doc lays out. on top of the list above:

| say this | you get |
|---|---|
| public github repo in the description | repo badge (cold open) |
| three ingredients | part 1 tag |
| a tracker that runs the same kind of math | chart 01 flash |
| look at the bottom of this chart | chart 01 |
| the box carries the premium | chart 01 ends |
| now the thing the haircut hides | where-the-ev-sits animation |
| call it five hours | hours callout |
| here's the sunk cost trap | animation ends |
| caveat about the left side of this chart | chart 03 |
| significance since someone's gonna ask | chart 09 |
| treat each set as one data point | p ≈ 0.00005 callout |
| the one thing that isn't significant | 17 of 31 callout |
| the contents are published, the values are mine | chart 05 |
| solve for break even | chart 06 |
| two foil commons and one foil uncommon | part 7 tag + chart 07 |
| what if god packs had always existed | "what if" tag |
| the top of the list | chart 11 |
| the most a god pack ever adds to a box | ~$2 callout |
| god packs flip zero of them | 0 of 62 callout |
| how much is wizards actually taking out | −$12.83 callout |
| i ran the cut on all | chart 12 |
| in cash, it's a different story | 3¢ callout |
| the margin chain | chart 08 |

in the nerd cut, the part tags are renumbered to match script b (part 2 "on paper, you win", and so on).

## running it

```bash
python3 edit/edit.py all  ~/Movies/take1.mp4 --cut a
```

or one step at a time:

```bash
python3 edit/edit.py transcribe ~/Movies/take1.mp4
python3 edit/edit.py plan       ~/Movies/take1.mp4 --cut a    # read edit/work/take1/plan_a.txt
python3 edit/edit.py render     ~/Movies/take1.mp4 --cut a
```

you get `take1_edit_a.mp4` and `take1_edit_a.srt` next to the recording.

**read `plan_a.txt` before rendering.** it lists:

- every retake it cut
- every cue: `OK`, `??` (fuzzy match, worth a look), or `MISSING`
- the youtube chapters, ready to paste into the description

if a cue is `MISSING`, you probably said it differently. either edit the phrase in `make_cues.py` to what you actually said (it shows you what it heard), or just let that graphic go.

options:
- `--cut b`: nerd cut
- `--no-pip`: charts go fully full-screen, no face in the corner
- `--burn-captions`: captions baked into the video, not just the .srt
- `--music bed.mp3`: background music, ducked under your voice
- `--max-gap 0.6`: keep more breathing room between sentences
- `--fps 30`: output frame rate (default 60, to match the camera). the animations render at 60 too (`ANIM_FPS=30 python3 animations.py` for quick drafts)

every step caches into `edit/work/<recording name>/` and picks up where it left off, so if anything gets interrupted, run the same command again. if you re-run `plan`, `render` notices and starts fresh.

on a laptop, expect transcription at about 1/3 of real time and the render at about real time.

## tested on

`edit/test/script_a_spoken.txt` is script a with a deliberate flub ("three hundred ninety eight of them. redo."). read by a robot voice over a placeholder card, all 38 cue lines match (one fuzzy). after the 2026-10-08 script changes, a simulated read of the current doc matches 44 of 44 (public) and 64 of 64 (nerd), the retake gets cut, and 31 seconds of air removed from 9.4 minutes. the nerd cut was checked against a simulated full read of script b: 55 of 56 cues matched, and the last one is a fuzzy match that still lands.

### full-screen cards and the newer clips

| say this | you get |
|---|---|
| okay, now boxes are worth it (cold open) | myth vs math card |
| i ran the numbers on that too | selling clock animation |
| ten regular rares, two fancy-frame rares | god pack reveal animation |
| what if god packs had always been a thing | god packs through history animation |
| fifteen cards to twelve | collector cut animation |
| it comes down to one number wizards | foil break-even slider |
| so here's the verdict | recap card (three numbers) |
| i found a bug in my own model (nerd cut) | receipts card |
| sorting the box at fifteen seconds a card (nerd cut) | selling clock animation |

where an animation already shows a number on screen, the matching callout was dropped so they don't stack.

### per-recording fixes: `<recording>.edit.json`

put a file next to the video with the same name plus `.edit.json` to fix one take without touching the script:

```json
{"phrases": {"tag_p4": "so what's a god pack worth"},
 "cuts": [[331.9, 337.05, "misspoke a number"]]}
```

`phrases` swaps the line a cue listens for (use when you said it differently); `cuts` removes a stretch of the recording (seconds, in the original file's time). `plan` prints what it used.
