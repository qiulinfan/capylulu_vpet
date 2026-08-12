# Round-body regeneration ImageGen prompts

Tool: built-in `imagegen`. Each call produced exactly one pose on a flat
magenta field. F1 was the identity reference in every call; prior drag frames
were pose-direction references only.

## Shared identity and rendering contract

```text
Create exactly one isolated frame for Lulu's platform-neutral pixel-sprite
animation master. Image 1 is absolute for Lulu's wide rounded face, full orange
muzzle, head-to-body ratio, round belly, broad hips, shorts width, tiny limbs,
fruit, total visual mass, palette, dark outline, scale, and detail.

An invisible pointer carries Lulu toward screen-right. Lulu remains
front-facing; the head leads right while both tiny arms and feet passively trail
left. Treat the plump head-and-torso mass as one rigid volume that may rotate but
must never stretch, squash, taper, narrow, lengthen, enlarge its head, shrink its
belly, or change thickness. This is carried inertia, not running, kicking,
skating, flying, dancing, or bracing.

Use the same yellow, orange, brown, green, white, and dark-outline appearance as
Image 1. No hue shift, desaturation, lighting change, gradient, glow, or
recoloring. Keep crisp low-resolution pixel-art-adjacent stepped edges.

Place one complete uncropped Lulu on a perfectly flat uniform #FF00FF field
with generous padding. No grid, label, floor, shadow, reflection, motion lines,
text, watermark, extra object, second pose, or #FF00FF inside Lulu.
```

## Per-frame motion requests

- F2: early lag, about 10 degrees from neutral toward F3.
- F3: medium lag, about 20 degrees; F1 controls identity and the old F3 controls
  direction only.
- F4: deeper lag halfway between approved F3 and F5.
- F5: maximum passive lag, about 30 degrees, without increasing body length or
  reducing thickness.
- F6: recovery toward upright, about 15 degrees, while arms and feet still
  softly trail left.

The generated calls requested open eyes only to make automated eye-region
detection reliable. The deterministic build then replaces both eye regions in
every frame with the approved closed-eye gold shape without regenerating the
body.
