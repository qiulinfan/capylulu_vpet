# Failed roll transition

This draft adds two reversible in-between poses between the approved prone-sleep
and side-sleep frames. The accepted logical motion is:

`prone -> transition 1 -> transition 2 -> side -> transition 2 -> transition 1 -> prone`

The side pose is held for `360ms`; each generated transition is shown for
`120ms`. Reusing the exact same two PNGs in reverse prevents a second,
independently generated return motion from drifting.

## Generation provenance

- Execution: built-in `imagegen` image edit
- Workflow: `sprite-pipeline` from `game-studio@openai-curated`
- Plugin version: `3fdeeb49`
- Identity/style anchors: `failed-05.png`, `failed-06.png`, and `failed-04.png`
- Raw generated strip: `imagegen-two-inbetweens-magenta.png`
- Transparent strip: `imagegen-two-inbetweens-alpha.png`

The exact image-edit prompt was:

```text
Use case: precise-object-edit
Asset type: two reversible in-between frames for a 192x208 pixel-pet sleeping animation
Input images: Image 1 is the exact prone-sleep start pose; Image 2 is the exact side-sleep endpoint; Image 3 is an additional exact style and identity anchor.
Primary request: create exactly two distinct intermediate full-body poses arranged left-to-right in one horizontal strip. They must connect Image 1 to Image 2 as a natural continuous roll: left pose is about one-third turned from prone sleep, right pose is about two-thirds turned toward side sleep. These are genuine in-betweens, not copies of either endpoint.
Subject invariants: preserve the exact same individual yellow-orange capybara Lulu, body proportions, oversized orange muzzle, closed eyes, tiny ears, orange fruit and green stem, outline weight, warm palette, flat shading, shorts/body markings, and small yellow Z sleep marks. Keep Lulu asleep throughout. Only interpolate the body, head, muzzle, fruit, paws, and torso rotation needed for the roll.
Style: match the references' low-resolution pixel-art-adjacent sprite exactly: chunky silhouette, crisp hard 1–2 px dark outline at final sprite scale, visible stepped edges, limited colors, flat cel shading, no gradients, no painterly texture, no 3D rendering, no antialias-heavy polish.
Layout: exactly two equal invisible slots left-to-right; one complete centered pose per slot; generous padding; no overlap and no cropping; consistent ground baseline; no grid, borders, labels, or frame numbers.
Scene/backdrop: perfectly flat solid #FF00FF chroma-key background for local removal; one uniform color, no shadows, gradients, texture, floor plane, or lighting variation. Do not use #FF00FF anywhere in Lulu.
Constraints: no new props, no new expressions, no awake eyes, no extra limbs, no motion lines, no blur, no detached particles except the existing small Z sleep marks, no text other than those Z marks, no watermark.
```

## Normalization and review

The Game Studio normalizer processed both strip slots together with one shared
scale into `176x176` square frames. `normalize.py` then placed both unchanged
square results at offset `(8, 24)` inside the pet's `192x208` canvas, yielding a
shared bottom-center anchor at `x=96`, ground `y=200`, and binary alpha.

Review assets:

- `four-pose-preview.png` — prone, both transitions, and side sleep
- `failed-12-frame-preview.png` — the complete active sequence in playback order
- `failed-roll-preview.gif` — isolated reversible roll
- `failed-full-candidate.gif` — full twelve-frame failed loop
- `preview-validation.json` — durations and adjacent-frame RMSE diagnostics
