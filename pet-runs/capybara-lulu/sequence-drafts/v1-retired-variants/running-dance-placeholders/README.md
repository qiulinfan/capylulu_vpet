# Retired running dance placeholders

Status: archived V1 history; excluded from releases and never installable.

The former `running-right`, `running-left`, and generic `running` rows all came
from the same front-facing dance sequence. Left and right were only different
orders of repeated poses, so neither communicated drag direction and each
eight-frame GIF contained only four unique visual poses. The result looked like
Lulu was dancing or skating while the window moved.

Contents:

- `frames/`: the exact three superseded formal frame directories;
- `qa/`: the three superseded action GIFs;
- `package-snapshot/spritesheet-before.png`: the complete formal atlas before
  the directional-drag revision.
- `contracts/`: the superseded root prompts that described left/right
  locomotion and generic in-place running, plus the pre-revision generation-job
  manifest.

The formal V1 package now uses a selected eight-pose rightward drag mother
sequence and its exact mirror for leftward drag. The runtime-required generic
`running` row remains in its fixed atlas position, but its six cells are exact
copies of `review`/focused listening; there is no independent generic-running
artwork.

The old `running-04` and `running-05` were lineage donors for the approved
waving action. Stable copies now live as `gold-normal-stand.png` and
`gold-open-face.png` under
`sequence-drafts/v1-action-work/waving-success-windup/`, so the waving
validation no longer depends on the retired generic-running row.
