# Koi Ascending — Make the AI Judge Excited

[![make.fun](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/bounty/ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/intan151/makefun-ai-excited-01/rank.svg)](https://make.fun/bounty/ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/intan151/makefun-ai-excited-01/reward.svg)](https://make.fun/bounty/ai-excited-01)

A golden koi leaps up a glowing waterfall toward a full moon, its tail
dissolving into ribbons of light: the moment a koi becomes a dragon.
Drawn entirely by code — no image files, no network, no libraries beyond
the Python 3.13 standard library.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png (1024x1024 PNG, ~110 KB)
```

`main.py` is deterministic: two runs produce byte-identical PNGs. It draws
the scene with a small software renderer (gradient sky, moon, waterfall,
the koi, petals, splash) and encodes the PNG with `zlib` by hand.

Entry for [make.fun's "Make the AI judge excited" bounty](https://make.fun/bounty/ai-excited-01).
