# Directional drag action work

Status: selected V1 action lineage. This directory is excluded from releases;
the normalized frames under `official-frames-v1/` are the formal runtime input.

## Semantics

The Codex V1 runtime uses `running-right` and `running-left` only while the pet
window is being dragged horizontally. They are interaction reactions, not
autonomous locomotion. The selected rightward mother sequence therefore keeps
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

## Selected single-frame lineage

The selected work is under `single-frame-pipeline/`. It follows a strict
production order: approve one neutral gold sprite; author each keyframe as one
image; author each in-between as one image; remove backgrounds and normalize
approved frames individually; derive the left sequence by exact mirror; and
only then assemble the eight PNGs into a strip and runtime GIF.

`single-frame-pipeline/assembled-v4/right/` and `left/` contain the selected
frame sequences. Frame 7 is a short synchronized two-eye blink built from the
gold body, mouth, and silhouette rather than a separately regenerated
character. Runtime timing is `120 ms` for frames 1-7 and `220 ms` for frame 8.
The exact frame map, deterministic build command, rejected intermediates, and
selected single-frame ImageGen contracts are documented in the pipeline's
`README.md` and `prompts.md`.

`tools/build_vpet_v1.py` treats the approved formal PNGs as its release input.
It SHA-locks all eight rightward frames and validates the gold identity/scale,
synchronized blink, hard alpha, eight unique poses, exact left mirror, atlas
cells, and runtime GIF timing on every build. This draft directory is
provenance and is not required to assemble the formal package.
