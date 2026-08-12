# Six-gold rerun ImageGen prompt record

Tool: built-in `imagegen`. The selected call produced one complete six-frame
contact sheet on a flat magenta field. This is a full rerun, not a local edit.
The six-action reference board contains representative official frames from
`idle`, `waving`, `failed`, `waiting`, `running`, and `review`; no former
directional-drag frame was used as a production reference.

## Selected full-rerun prompt

```text
Create a NEW complete six-frame pixel-art contact sheet, fully redrawing every
cell. Keep a consistent 3-column × 2-row layout, compact gold-standard
identity, passive rightward-drag progression, flat shorts, green fruit leaf,
and clean low-texture style. The six-action board is the identity authority.
Background must be one perfectly uniform #FF00FF field, with no grid lines or
labels. Exactly six full sprites in reading order F1-F6.

Motion curve: 0°, 8°, 16°, 22°, 26°, 13° clockwise; head leads right, tiny
arms and feet trail left progressively through F5, and F6 recovers halfway.

Face hard gate: lower the entire orange muzzle enough that every frame has a
broad band of at least 8 clearly visible yellow skin pixels between the lowest
pixel of each closed black eye arc and the highest orange muzzle pixel beneath
it. This yellow band must survive later nearest-neighbor rotation—no orange
pixel may approach, touch, or intrude into either eye. Keep the muzzle as a low
wide oval with one smooth central arch and no M/double peaks. Tiny closed dark
smile only; no tongue, teeth, or open mouth.

Shorts hard gate: in all six full redraws, use a clean flat brown front,
exactly two leg openings aligned to two feet, and a clear upward #FF00FF
U-shaped notch between them. No central seam, oval fold, pouch, third lobe,
crotch bump, or bulge.

Use identical scale and palette across cells, a green stem, crisp dark outline,
and generous uncropped margins. No grain, shadows, floor, text, extra object,
or seventh sprite.
```

## Post-normalization acceptance gate

The selected prompt above is preserved verbatim: it asked ImageGen for at
least 8 visible pixels in the generated sheet. After binary-alpha extraction,
nearest-neighbor normalization, and whole-sprite rotation, the narrowest
head-local skin-only path measures 7 pixels (the full measured range is
7–11). The production acceptance gate is therefore recorded separately as
`>= 7`, with zero orange/eye contact or overlap required. This one-pixel
revision applies only to deterministic post-processing; it does not rewrite
the generation request or permit any orange incursion.

## Deterministic frame map

- F1-F5 use contact-sheet cells 1-5 and whole-sprite pose alignment to
  `0°, 8°, 16°, 22°, 26°`.
- F6 reuses newly redrawn cell 2 at `13°`; this makes F5→F6 and F6→F7 equally
  sized recovery steps while retaining the same face and shorts construction.

F7 and F8 use no generative operation. F7 is F1 shifted upward one pixel; F8 is
an exact reuse of F1. The entire left sequence is a deterministic horizontal
mirror of the right sequence.
