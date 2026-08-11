# Waving success wind-up work files

Status: draft lineage for one approved V1 action revision; not installable and
not a release input by itself.

The goal was a runtime-compatible four-frame "yay, success!" action:

1. normal V1 standing pose;
2. an early weight shift with both arms starting to rise and one foot just
   leaving the ground;
3. the former open-eye kick-and-wave peak;
4. the former closed-eye held cheer.

`imagegen-rejected-near-endpoint.png` was rejected because the limbs were
already too close to the peak and the generated face drifted from V1.
`imagegen-selected-early-anticipation-magenta.png` supplied only the early
limb/body pose. `anticipation-body-alpha.png` is the normalized transparent
candidate from which only the body and limbs were used.
`anticipation-gold-face-preview.png` replaces the generated head and face with
the exact upper-head pixels from formal V1 `running/running-05.png` and reduces
the final alpha edge to the same binary hard edge as V1. This preview is the
lineage source for formal `waving-02.png`.

The formal action remains four frames because the Codex V1 pet runtime reads
exactly four cells from atlas row 3.
