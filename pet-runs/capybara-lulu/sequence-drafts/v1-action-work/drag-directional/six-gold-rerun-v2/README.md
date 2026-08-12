# Six-gold directional rerun v2

Status: active candidate source lineage for `running-right` and `running-left`.

This lineage discards the earlier directional frames as production inputs.
F1-F6 were redrawn together as one complete six-frame contact sheet with the
built-in ImageGen tool, using the six non-directional actions (`idle`,
`waving`, `failed`, `waiting`, `running`, and `review`) as the shared gold
identity authority. The prior drag sequence was not supplied as a pose or pixel
reference, and no local repair was applied to any old frame.

The production contract specifically fixes three visual failures:

- the orange muzzle stays separated from both closed eyes and has one smooth
  central upper arch rather than an M-shaped edge that rises into the eyes;
- the mouth is the small closed smile used by the majority of the six gold
  actions, with no orange/tongue cavity or white teeth; and
- the shorts have a flat front and two leg openings separated by an upward
  background gap, with no center seam, pouch, third lobe, or crotch bulge.

`sources/` keeps the selected flat-magenta contact sheet. `alpha/` keeps the
result of the imagegen Skill's chroma-key helper. `build.py` extracts all six
cells, uses one uniform scale and whole-sprite rotation per frame, and applies a
hue-stratified 128-color palette learned from every official PNG in the six
gold actions. Green, neutral, dark, and warm colors receive explicit palette
quotas so the fruit leaf cannot turn brown. The final motion angles are
`0°, 8°, 16°, 22°, 26°, 13°`; the recovery reuses the newly redrawn early-lag
silhouette at `13°` to balance both sides of the recovery. F7 is an exact
one-pixel upward translation of F1, F8 reuses F1 byte-for-byte, and every
leftward frame is an exact horizontal mirror.

The normal build remains lineage-only. After a human visual review has been
recorded with exact frame/contact/preview hashes, run `promote.py`; it rejects
stale review evidence, stages all 16 PNGs, installs them into the two official
action directories, and rebuilds the complete eight-action review gallery.

Timing remains `120 ms` for F1-F7 and `220 ms` for F8.

Rebuild with:

```bash
uv run --frozen python pet-runs/capybara-lulu/sequence-drafts/v1-action-work/drag-directional/six-gold-rerun-v2/build.py
```

`validation.json` records deterministic size, alpha-area, loop, palette,
rotation-invariant face geometry (at least 7 skin pixels between either eye and
the muzzle), motion-IoU, and mirror gates.
The original ImageGen prompt requested 8 pixels; `prompts.md` preserves that
request verbatim and separately records why the post-normalization gate is 7.
`test_face_geometry.py` proves that the detector accepts the six selected faces
and rejects synthetic orange-spill and M-shaped-muzzle controls.
`visual-review.json` records the independent per-frame review of the face,
mouth, and shorts geometry.
`asset-contract.json` states the requested visual and technical gates;
`production-receipt.json` binds the frozen implementation, validation, review,
promotion, and QA evidence while keeping runtime integration explicitly
`not_tested`.
