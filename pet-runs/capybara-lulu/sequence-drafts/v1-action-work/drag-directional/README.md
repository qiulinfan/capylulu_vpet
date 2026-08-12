# Directional drag action work

Status: selected animation-master action lineage. This directory preserves
source and rejected-variant history; active normalized frames live under
`official-frames-v1/`.

## Semantics

`running-right` and `running-left` describe Lulu being carried horizontally.
They are interaction reactions, not autonomous locomotion. The selected
rightward mother sequence therefore keeps
Lulu front-facing while the head leads toward screen-right and the torso,
arms, feet, and fruit follow with soft inertia. The leftward sequence is an
exact horizontal pixel mirror, preventing a second generation from changing
the face, size, or rhythm.

The storyboard was informed by these Xiaohongshu desktop-pet examples:

- <https://www.xiaohongshu.com/explore/6a01ab500000000038023646>: natural
  movement comes from the center of mass and body follow-through, not merely
  alternating feet.
- <https://www.xiaohongshu.com/explore/6a59e08a0000000011017fd8>: drag direction
  and speed read as an interaction; the character visibly trails the pointer.
- <https://www.xiaohongshu.com/explore/6a79b4350000000033018b37>: drag, idle,
  click, and walking actions should share one coherent character language.

## Superseded whole-sheet lineage

- `right-drag-source-magenta.png`: initial eight-pose mother sequence. Its
  normalized eye spacing was only about 47.7 px and it was rejected.
- `right-drag-face-corrected-magenta.png`: targeted face correction. Eye
  spacing was fixed, but the edit introduced a visibly varied magenta field.
- `right-drag-final-magenta.png`: background cleanup for the first corrected
  candidate. Final visual review rejected this branch because frames 2-7 read
  as a repeated side kick with braced fists, not passive drag inertia.
- `right-drag-motion-v2-magenta.png`: motion correction with loose trailing
  arms, airborne feet, and a progressive lean-and-recovery arc.
- `right-drag-motion-v3-face-final-magenta.png`: identity correction on the
  improved body motion. It retained the motion but the eyes remained too close.
- `right-drag-motion-v4-selected-magenta.png`: the last whole-sheet candidate.
  It improved eye spacing but was later rejected for thinness, always-open
  eyes, and per-cell identity/scale drift.
- `right-drag-motion-v4-selected-alpha-hard.png`: hard-alpha form of that
  rejected strip.
  The matte preserves yellow, orange, green, white, and black subject pixels
  while removing the magenta field.
- `preview-motion-v4/right/`: deterministic 192x208 normalization of the old
  strip.
- `preview-motion-v4/left/`: exact horizontal mirrors of those old frames.
- `right-drag-motion-v4-preview.gif`, `left-drag-motion-v4-preview.gif`, and
  `drag-motion-v4-contact-sheet.png`: retained QA for the rejected branch.

The six-pass prompt record for this retired branch remains in `prompts.md`.

## Superseded single-frame lineage

The earlier selected work is under `single-frame-pipeline/`. It follows a strict
production order: approve one neutral gold sprite; author each keyframe as one
image; author each in-between as one image; remove backgrounds and normalize
approved frames individually; derive the left sequence by exact mirror; and
only then assemble the eight PNGs into a strip and runtime GIF.

`single-frame-pipeline/assembled-v4/right/` and `left/` contain those superseded
frame sequences. Frame 7 is a short synchronized two-eye blink built from the
gold body, mouth, and silhouette rather than a separately regenerated
character. They were retired after visual review found pose-dependent body
stretching/thinning, visible color drift, and too many open-eye frames.

## Selected round-body regeneration

`roundbody-regeneration-v1/` preserves F1's body, face geometry, palette, and
outline; regenerates F2-F6 one isolated pose at a time; and applies deterministic
shape, palette, eye, mirror, and loop constraints. Every frame keeps both eyes
closed. Generated frames target the same effective visual mass, use uniform
scaling only, and share one palette derived from F1. F7 is a one-pixel recovery
bob, F8 returns exactly to the closed-eye F1, and the left sequence is an exact
pixel mirror.

Timing remains `120 ms` for frames 1-7 and `220 ms` for frame 8.
The exact frame map, deterministic build command, rejected intermediates, and
ImageGen invariants are documented in the regeneration's `README.md` and
validated by its `build.py`.
