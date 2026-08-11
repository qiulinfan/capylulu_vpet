# ImageGen prompt record

The built-in ImageGen tool was used for all six passes below. They document the
superseded whole-sheet branch; none of these sheets is a release input. The
selected gold-to-keyframe-to-in-between contracts are recorded separately in
`single-frame-pipeline/prompts.md`.

## 1. Rightward drag mother sequence

References: the approved V1 open-face donor now preserved as
`../waving-success-windup/gold-open-face.png`, plus formal `waving-01.png` and
`waving-02.png`.

```text
Use case: identity-preserve
Asset type: production pixel-art sprite animation source sheet for a Codex desktop pet
Primary request: create one horizontal strip of exactly 8 distinct full-body animation frames showing the same capybara Lulu being dragged by the user's pointer toward screen-right. This is not autonomous running. The mouse/window pulls Lulu right while the body, hips, arms, feet, and orange fruit lag toward screen-left with soft inertia.
Storyboard left to right: neutral-compatible pickup; mild inertial lag; stronger lag with one toe skimming; maximum soft lag with the feet briefly airborne; small elastic recovery; a second smaller lag; a second airborne trailing pose; and a near-neutral pose ready to loop.
Subject: the exact same front-facing Lulu from the references, with the orange fruit attached, yellow-orange body, orange muzzle, and orange shorts.
Style: preserve the exact original low-resolution hard-edged pixel-art style, palette, outline weight, proportions, facial construction, and friendly personality.
Face invariants: preserve the rounded gold head and muzzle, eye size and spacing, white sclera, black pupils and highlights, smile, and cheek geometry. Both eyes stay open together. No wink or blink.
Motion constraints: center-of-mass lag, a gentle 4-8 degree lean opposite travel, feet mostly dangling or airborne, and both arms trailing together. No running arms, forceful push-off, jogging, dancing, kicking, or skating.
Backdrop: one perfectly flat #FF00FF chroma-key field, one row, exactly eight evenly spaced cells, no grid or labels. No shadows, gradients, texture, floor, text, watermark, or extra objects.
```

## 2. Gold-face correction

References: the first generated sheet and the stable V1 donor
`../waving-success-windup/gold-open-face.png`.

```text
Use case: identity-preserve
Primary request: edit only the face in all eight frames to match the V1 gold. Preserve every body pose, limb position, fruit position, spacing, scale, background, and the single-row layout.
Correction: the candidate eyes are too close together. Increase horizontal eye spacing to match the gold (about 52 pixels after normalization rather than about 48), keep both eyes equally large and open, retain the gold eye rims, pupils and highlights, and match the wider rounded head, full orange muzzle, muzzle-to-head ratio, mouth size, and smile geometry.
Invariants: do not flatten, narrow, lengthen, side-profile, blink, wink, squint, redirect the gaze, or restyle the face. Keep each existing head tilt and inertia pose. No text, watermark, blur, or extra elements.
```

## 3. Background cleanup

Reference: the gold-face-corrected sheet.

```text
Use case: precise-object-edit
Primary request: change only the background. Replace every pixel outside the eight Lulu sprites with one perfectly flat, uniform #FF00FF chroma-key color.
Invariants: preserve the eight sprites exactly—the faces, eye spacing, expressions, body poses, fruit, limbs, colors, scale, spacing, order, and one-row layout must not change.
Background constraints: no gradient, bands, texture, lighting variation, shadows, floor, halo, reflection, grid, label, text, watermark, or extra object. Keep crisp hard-edged pixel art and do not use #FF00FF inside Lulu.
```

## 4. Passive-drag motion correction

References: the first corrected candidate, the V1 open-face donor, and the
runtime drag storyboard.

```text
Use case: identity-preserve animation correction
Primary request: redraw the eight rightward-drag poses so the motion unmistakably reads as Lulu being carried by the user's pointer, not running, dancing, skating, or kicking. Preserve the V1 face, fruit, palette, outline, proportions, one-row order, and flat #FF00FF background.
Motion arc left to right: near-neutral pickup; 25% lag; 50% lag; 75% lag; maximum lag; 65% recovery; 35% recovery; 10% near-neutral settle. During the middle poses the torso tilts opposite travel, both feet leave the ground or dangle without pushing off, and both arms hang and trail toward screen-left instead of bracing at the chest. Keep the head leading toward screen-right, with the hips and limbs following elastically. Make frame 8 flow naturally back into frame 1.
Face invariants: front-facing rounded V1 head and muzzle, both eyes open together, same gaze and smile, no wink, side profile, flattening, narrowing, or new expression.
Output constraints: exactly eight distinct full-body sprites, one horizontal row, even cell spacing, crisp hard-edged pixel art, no labels, grid, floor, shadow, text, watermark, blur, or extra object.
```

## 5. Gold-face lock on the improved motion

References: the motion-v2 sheet and stable V1 `gold-open-face.png`.

```text
Use case: identity-preserve
Primary request: edit only Lulu's face and head construction in all eight motion-v2 poses to match the V1 gold. Preserve every approved body pose, lean, arm and foot position, airborne gap, fruit position, spacing, order, scale, magenta background, and one-row layout.
Face correction: restore the wider rounded head, full orange muzzle, V1 muzzle-to-head ratio, symmetrical open eyes, black pupils and white highlights, and the friendly V1 smile. Keep the per-frame head tilt but do not let it become a three-quarter or side-profile face.
Invariants: no body redraw, no motion change, no wink, blink, squint, flattened face, narrowed eye spacing, redirected gaze, texture, blur, text, watermark, or extra object.
```

## 6. Numeric V1 eye-spacing correction (retired motion-v4 candidate)

References: the motion-v3 sheet and stable V1 `gold-open-face.png`.

```text
Use case: precise identity edit
Primary request: preserve the entire motion-v3 sheet and adjust only the horizontal placement and V1 construction of the two eyes in each frame. After normalization, move the eye centers outward from the current roughly 46-49 px spacing to the gold target of 51-52 px. Do not enlarge the eyes to fake the spacing.
Eye invariants: both eyes remain equally large, fully open, synchronized, front-facing, and centered in the rounded gold face; preserve the white rims, black pupils, highlights, gaze, smile, muzzle, head silhouette, and each existing head tilt.
Absolute invariants: do not change any body pixel, limb pose, airborne spacing, inertia arc, fruit, scale, frame order, one-row layout, or flat #FF00FF background. No blink, wink, squint, three-quarter face, text, watermark, grid, blur, shadow, or extra object.
```
