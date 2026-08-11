# Formal V1 `running-right`: rightward pointer drag

This runtime state is not autonomous locomotion. It appears while the user
drags Lulu's window toward screen-right.

Do not generate a sprite sheet directly. First establish one approved neutral
`192x208` gold sprite. Produce each action keyframe as its own image from that
gold, then produce each in-between as its own image from the two neighboring
poses. Remove the background and normalize each approved frame separately;
only then assemble exactly eight frames into the formal row.

Keep Lulu substantially front-facing and preserve the formal V1 gold identity:
rounded head, full rounded orange muzzle, gold body width and fullness, matched
eye size and spacing, friendly centered gaze, original palette, outline, 190 px
subject height, orange shorts, and attached fruit. Frames 1-6 and 8 keep both
eyes open together. Frame 7 is one short synchronized two-eye blink; neither
eye may wink independently.

Communicate the interaction through center-of-mass inertia. The head leads
toward screen-right while the torso, hips, both arms, feet, and fruit follow
softly toward screen-left. Use a neutral-compatible pickup, increasing lag,
one or two light toe skims, a brief airborne/trailing peak, elastic recovery,
and a near-neutral loop closure. Do not show jogging, forceful push-off,
alternating running arms, dancing, kicking, skating, speed lines, dust, floor
shadows, detached effects, text, or scenery.

Use a flat removable chroma-key background for each generated source. Each
source contains one isolated, uncropped sprite only—never multiple poses, a
grid, labels, or an atlas. The selected frame lineage, prompt record,
normalization, deterministic mirror, assembly, and QA live under
`sequence-drafts/v1-action-work/drag-directional/single-frame-pipeline/`.
