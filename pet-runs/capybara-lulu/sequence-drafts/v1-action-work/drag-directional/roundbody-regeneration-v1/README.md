# Round-body directional regeneration v1

Status: superseded directional lineage. It was retired after visual review
found mouth/muzzle mixing, an orange muzzle edge entering the eye region, and a
pouch-like crotch shape. Active source work moved to
`../six-gold-rerun-v2/` as a full redraw from the six non-directional gold
actions.

This pass preserves the existing neutral F1 body, face geometry, palette, and
outline and regenerates only F2-F6 with the built-in ImageGen tool. Every
generation used F1 as the absolute identity, geometry, scale, and color
authority; older directional frames were used only as motion-direction
references.

The deterministic build then:

1. removes the flat magenta background with the built-in `imagegen` Skill's
   chroma-key helper;
2. applies one uniform scale per generated subject to target the same effective
   visual mass, never independent horizontal or vertical scaling;
3. maps every generated frame to one fixed 128-color palette derived from F1;
4. deterministically replaces only the two eye regions in every frame with the
   approved closed-eye gold shape, keeping the full drag reaction cute and
   relaxed;
5. uses a one-pixel upward recovery bob at F7, then reuses the same closed-eye
   F1 as F8 so the loop seam is pixel-identical and GIF encoders keep all eight
   frames; and
6. derives every leftward frame by exact horizontal pixel mirroring.

The exact prompt set is recorded in `prompts.md`. The five ImageGen prompts
share these invariants: keep Lulu front-facing and
plump; rotate one rigid head-and-torso volume; never stretch, squash, taper,
narrow, lengthen, enlarge the head, or shrink the belly; preserve F1's palette;
and treat the old frames as pose guides only.

Build the normalized frames and previews with:

```bash
uv run --frozen python pet-runs/capybara-lulu/sequence-drafts/v1-action-work/drag-directional/roundbody-regeneration-v1/build.py
```
