# Single-frame directional-drag pipeline

Status: superseded directional-drag lineage. It was retired after visual review
found pose-dependent body stretching/thinning, color drift, and too many
open-eye frames. Active source work moved to `../roundbody-regeneration-v1/`.

## Production order

1. `gold/gold-neutral-open-192x208.png` fixes Lulu's identity, face, body
   fullness, palette, hard-alpha edge, and runtime scale.
2. `keyframes/` contains individually authored action keys. No generation call
   is asked to solve more than one pose.
3. `inbetweens/` contains individually authored frames between neighboring
   approved poses.
4. `assemble.py` performs only deterministic work: hard-magenta removal for
   the selected F6 source, per-frame normalization, the synchronized F7 blink,
   exact leftward mirroring, GIF QA, and final strip assembly.
5. `assembled-v4/right/` and `assembled-v4/left/` are the selected eight-frame
   sequences. `right-spritesheet-strip.png` is assembled from those PNGs; it is
   never an ImageGen output.

## Selected frame map

| Frame | Role | Selected source |
|---|---|---|
| F1 | neutral pickup / identity gold | `gold/gold-neutral-open-192x208.png` |
| F2 | early lag in-between | `inbetweens/f02/normalized-rotated-selected-192x208.png` |
| F3 | 50% lag keyframe | `keyframes/f03/normalized-corrected-192x208.png` |
| F4 | F3-to-F5 in-between | `inbetweens/f04/normalized-192x208.png` |
| F5 | maximum passive lag keyframe | `keyframes/f05/normalized-corrected-192x208.png` |
| F6 | recovery in-between | `inbetweens/f06/normalized-recovery-v2-192x208.png` |
| F7 | near-neutral synchronized blink | open gold body/mouth with both eye regions derived from the closed-eye V1 gold |
| F8 | loop settle | open gold shifted upward by one pixel |

All selected subjects are `190 px` tall. F7 changes both eyes together while
retaining the open gold's body, mouth, scale, and silhouette. The left sequence
is an exact horizontal pixel mirror of the right sequence. Runtime timing is
`120 ms` for F1-F7 and `220 ms` for F8.

Earlier whole-sheet attempts and assembled-v1 through assembled-v3 remain as
rejected drafts. They preserve useful motion exploration, but were superseded
because whole-sheet generation allowed face, body volume, and recovery timing
to drift between cells.

The selected ImageGen contracts are recorded in `prompts.md`. Rebuild the draft
assembly with:

```bash
uv run --frozen python pet-runs/capybara-lulu/sequence-drafts/v1-action-work/drag-directional/single-frame-pipeline/assemble.py
```
