# CapyLulu VPet

Animation-first asset workspace for the healing pixel-style character `水豚噜噜`.

## Current production stage

Each action is tuned and accepted as an independent looping GIF before any
whole-pet atlas is assembled. The active action contract is
`pet-runs/capybara-lulu/official-frames-v1-manifest.json`; its frame sources
remain normalized `192x208` transparent PNGs under
`pet-runs/capybara-lulu/official-frames-v1/`.

The current eight actions are:

1. `idle`
2. `running-right`
3. `running-left`
4. `waving` — approved gold action
5. `failed` — reversible prone-to-side sleeping roll candidate
6. `waiting` — approved gold action
7. `running`
8. `review`

`jumping` was retired because its cheer overlapped `waving`. Its former source
frames are preserved only as draft lineage under
`pet-runs/capybara-lulu/sequence-drafts/v1-retired-variants/jumping-overlaps-waving/`.

## Build and inspect the action GIFs

```bash
uv run --frozen python tools/build_action_gifs.py
```

The compatibility entry point below performs the same action-only build:

```bash
uv run --frozen python tools/build_vpet_v1.py
```

Both commands write only the independent previews and their validation report:

- `pet-runs/capybara-lulu/qa/action-gifs/*.gif`
- `pet-runs/capybara-lulu/qa/action-gifs/validation.json`

They intentionally do not rebuild a spritesheet. `waiting` and `waving` are
hash-locked so an unrelated animation edit cannot silently change either gold
action.

## Whole-pet package

`pet-runs/capybara-lulu/final/` is the last assembled V1 snapshot. It may lag
behind the active action GIFs during animation review and is not the acceptance
source for the current stage. A new spritesheet and pet package will be built
only after every small animation has been reviewed.

Experimental and historical assets remain under
`pet-runs/capybara-lulu/sequence-drafts/` and are excluded from the active
action set.
