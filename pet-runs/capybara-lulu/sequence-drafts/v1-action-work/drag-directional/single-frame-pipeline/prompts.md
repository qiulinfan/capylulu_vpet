# Selected single-frame ImageGen contracts

The built-in ImageGen tool was used only for one isolated sprite at a time.
The text below records the final production contracts; targeted correction
passes repeated the same invariants while naming the single defect to fix.

## Canonical neutral open-eye gold

References: the formal V1 closed-eye neutral body gold and the formal V1
open-eye face gold.

```text
Create exactly one isolated neutral full-body Lulu sprite, not an animation
sheet. Retain the closed-eye neutral reference's complete round body, hips,
belly, arms, legs, fruit, palette, outline, and scale; use the open-eye gold's
exact wide rounded head, full muzzle, equally sized eyes, spacing, centered
gaze, and friendly open smile. Preserve the original hard-edged low-resolution
pixel-art construction. Do not narrow, flatten, lengthen, resize, side-face, or
redesign Lulu. Put the one uncropped sprite on a flat uniform #FF00FF field.
No grid, second pose, label, floor, shadow, text, watermark, or extra object.
```

## F3 action keyframe — 50% lag

References: the canonical gold and the approved passive-drag storyboard.

```text
Create exactly one full-body frame of the same gold Lulu at about 50% passive
lag while the pointer carries the pet toward screen-right. The head leads
right; the full round torso, hips, both arms, both dangling feet, and fruit lag
left. This is not running: no push-off, kick, skating, dance, or alternating
running arms. Keep the exact gold face, body fullness, scale, palette, outline,
orange shorts, and front-facing identity. Both eyes are equally open. Use one
flat #FF00FF background and no sheet, grid, label, effects, or extra object.
```

## F5 action keyframe — maximum lag

References: the corrected F3 keyframe and canonical gold.

```text
Create exactly one maximum passive-lag keyframe later in the same rightward
drag. Increase the elastic lean and trailing distance from F3; let both feet
briefly dangle airborne and keep both small arms trailing without bracing.
Preserve the gold's wide rounded head, full muzzle, plump belly and hips, exact
scale, face, eye construction, smile, attached fruit, shorts, palette, and
pixel outline. Do not make Lulu thin, small, long, side-facing, running,
kicking, or dancing. One isolated sprite on flat #FF00FF only.
```

## F2 and F4 individual in-betweens

References: their two neighboring approved frames.

```text
Create exactly one isolated in-between pose halfway between the two supplied
neighbor frames. Preserve the same gold identity, full body volume, face,
scale, palette, outline, attached fruit, and passive rightward-drag causality.
Interpolate the lean and dangling limbs without inventing a new action or
expression. Both eyes stay equally open. One sprite on flat #FF00FF; no sheet,
grid, label, floor, shadow, text, watermark, or extra object.
```

## F6 individual recovery in-between

References: the approved F5 maximum-lag keyframe and canonical neutral gold.

```text
Create exactly ONE isolated full-body pixel-art sprite frame, not a sprite
sheet and not multiple poses. Make a true recovery in-between, approximately
halfway from F5's maximum rightward-drag lag toward the neutral gold. Lulu must
still lean and trail toward screen-left, but clearly less than F5. The head
leads right; the full rounded torso, hips, both nubby arms, dangling feet, and
attached fruit recover elastically. No running, kicking, skating, or dancing.

Preserve the gold's plump round body, full wide hips and belly, rounded wide
head, large full orange muzzle, friendly centered open-eyed face, matched eye
size and spacing, gaze, orange shorts, attached fruit, palette, outline, and
crisp stepped pixel art. Do not make Lulu thinner, smaller, taller, narrower,
big-headed, side-facing, or three-quarter facing. Put the one uncropped sprite
on one flat uniform #FF00FF field. No second pose, grid, labels, floor, shadow,
gradient, text, watermark, effects, or extra object.
```

F7 and F8 use no generative interpolation. F7 deterministically keeps the open
gold's entire body and mouth while applying both closed-eye regions together
from the approved V1 closed-eye gold. F8 is the open gold shifted upward one
pixel for loop closure.
