# CapyLulu Animation Master

Platform-neutral animation workspace for the complete custom pet `水豚噜噜`.
The animation master is the authority in this repository: actions, frame
counts, timing, and loops are designed for Lulu first, without being limited by
Codex or any other downstream platform.

## Animation-master contract

Each action is tuned and accepted as an independent looping GIF before any
platform package or whole-pet atlas is assembled. The active contract is
`pet-runs/capybara-lulu/official-frames-v1-manifest.json`; its current frame
sources are normalized `192x208` transparent PNGs under
`pet-runs/capybara-lulu/official-frames-v1/`.

The `official-frames-v1` path is retained as lineage naming. Neither `v1` nor
the current `192x208` canvas is a Codex contract or a permanent platform limit.
Platform adapters are downstream derivatives: they may select, resample, or
retime approved master actions, but they must not redefine or constrain the
master.

The current nine actions are:

1. `idle` — approved gold sleeping action; exact master alias of `failed`
2. `running-right` — six-gold full-rerun candidate
3. `running-left` — exact-mirror six-gold full-rerun candidate
4. `waving` — approved gold action
5. `failed` — approved gold action with a reversible prone-to-side sleeping roll
6. `waiting` — approved gold action
7. `working` — approved gold ink-painting action with a completed page change
8. `running` — approved gold action
9. `review` — approved gold action

This nine-action set is the current milestone. The sofa-based `looking-around`
candidate remains under `sequence-drafts/new-state-candidates/looking-around/`
and is deliberately excluded until its motion is refined and approved.

`jumping` was retired because its cheer overlapped `waving`. Its former source
frames are preserved only as draft lineage under
`pet-runs/capybara-lulu/sequence-drafts/v1-retired-variants/jumping-overlaps-waving/`.

## Build and inspect the action GIFs

```bash
uv run --frozen python tools/build_action_gifs.py
```

Build the current Codex V1 adapter without installing it:

```bash
uv run --frozen python tools/build_vpet_v1.py
```

Build and install it into the local Codex custom-pet directory:

```bash
uv run --frozen python tools/build_vpet_v1.py --install
```

The action-only command writes the independent previews, a complete gallery,
and their validation report:

- `pet-runs/capybara-lulu/qa/action-gifs/*.gif`
- `pet-runs/capybara-lulu/qa/action-gifs/gallery.md`
- `pet-runs/capybara-lulu/qa/action-gifs/validation.json`

It intentionally does not rebuild a spritesheet. `idle`, `waving`, `failed`,
`waiting`, `working`, `running`, and `review` are hash-locked so an unrelated
animation edit cannot silently change any of the seven gold actions.

## Iteration review rule

Every animation iteration must rebuild and display every active GIF in
manifest `action_order`, even when only one action changed. The generated
`gallery.md` is the canonical full-review index; a review is incomplete if it
shows only the edited action.

## Codex adapter

`pet-runs/capybara-lulu/final/` is the current installable Codex V1 adapter.
It maps the complete animation master into Codex's fixed 8-column by 9-row,
`1536x1872` custom-pet spritesheet contract. The adapter uses the sleeping
`failed` artwork for both `idle` and `failed`, uses `waving` for Codex's required
hover/`jumping` row, and maps the approved `working` action to Codex's task-active
`running` row. The adapter isolates Lulu's orange/yellow-and-green silhouette
from the paper, ink dish, brush, and black ink, then normalizes every working
frame against the equal-weight medians of four approved, unobscured reference
actions: `running-right`, `running-left`, `waving`, and `review`. It combines
silhouette equivalent diameter with bounding-box geometric mean. A second
semantic-contour pass includes detached paws and limbs, then applies the closest
safe common target ratio that keeps Lulu and its dark outline inside Codex's
fixed cell across the complete loop. The resulting per-frame scales are about
`1.12x`–`1.21x`; their variation compensates for source-frame size drift, so the
measured output silhouette stays constant. Lulu, paper, ink dish, and brush are
still enlarged together; every other action remains pixel-identical.
The full measurement record is
`pet-runs/capybara-lulu/qa/working-scale-feature-report.json`. This adapter-only
normalization never changes any approved gold master frame.

The installed local package is `~/.codex/pets/capybara-lulu/`. Its app-facing
identity is `custom:capybara-lulu`.

Experimental and historical assets remain under
`pet-runs/capybara-lulu/sequence-drafts/` and are excluded from the active
action set.
