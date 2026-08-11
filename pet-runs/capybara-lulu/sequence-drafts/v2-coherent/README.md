# Coherent V2 expansion draft

This directory preserves the merged V2 expansion and the later gold-alignment
pass as draft work. It is not an installable release and is not an input to the
formal V1 package.

- `sources/`: editable source sheets, including gold-aligned variants and
  draft-local copies of the V1 frames historically reused by this experiment.
- `build/`: derived normalized frames and animation-library frames.
- `package-preview/`: draft atlas preview; its manifest is `pet.draft.json`.
- `qa/`: draft-only contact sheets and animated previews.
- `build_draft.py`: deterministic replay tool restricted to this directory.

The original merged baseline remains recoverable from Git commit `ac604e3`.
