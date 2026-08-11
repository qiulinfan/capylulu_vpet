# CapyLulu VPet

Desktop pet asset workspace for the healing pixel-style character `水豚噜噜`.

Current assets live under `pet-runs/capybara-lulu/`, including:

- canonical base sprite and references
- draft sequence sheets
- normalized `192x208` sprite frames
- transparent and chroma-key preview exports
- one Codex-compatible formal V1 `8x9` atlas
- expansion work kept explicitly under `sequence-drafts/`

The current expanded normalized frames are in:

- `pet-runs/capybara-lulu/sequence-drafts/expanded-frames-v2-alpha-192x208/`
- `pet-runs/capybara-lulu/sequence-drafts/expanded-frames-v2-blue-192x208/`

The only installable pet package is V1:

- `pet-runs/capybara-lulu/final/pet.json`
- `pet-runs/capybara-lulu/final/spritesheet.webp`
- `pet-runs/capybara-lulu/final/spritesheet.png`

The V1 frames under `pet-runs/capybara-lulu/official-frames-v1/` are the
character-identity and runtime-scale gold standard.

Its nine formal states are declared in
`pet-runs/capybara-lulu/asset-scope.json`. Idle deliberately reuses the six
focused-listening `review` frames. The runtime-required generic `running` row
also reuses `review`; it has no independent running artwork. `running-right`
and `running-left` are directional pointer-drag reactions, not locomotion. The
selected authoring lineage locks one neutral gold sprite, creates individual
keyframes, fills individual in-betweens, and only then assembles the rightward
row; the leftward sequence is its exact mirror. Waving is a four-frame,
runtime-compatible success
celebration with a standing wind-up and synchronized two-eye blinking.

Rebuild the formal package and QA with:

```bash
uv run --frozen python tools/build_vpet_v1.py
```

Expansion assets are preserved but excluded from releases:

- `pet-runs/capybara-lulu/sequence-drafts/v2-coherent/` contains the V2 source,
  generated build, package preview, QA, and draft-only replay tool.
- `pet-runs/capybara-lulu/sequence-drafts/idle-sequence-experiment/` preserves
  the retired multi-action idle atlas and its QA.
- `pet-runs/capybara-lulu/sequence-drafts/v1-retired-variants/` preserves
  superseded formal-frame variants.

The V2 draft may be replayed in place with
`uv run --frozen python pet-runs/capybara-lulu/sequence-drafts/v2-coherent/build_draft.py`.
It writes only inside that draft directory and emits `pet.draft.json`, never an
installable `pet.json`.

QA artifacts:

- `pet-runs/capybara-lulu/final/validation.json`
- `pet-runs/capybara-lulu/qa/contact-sheet.png`
- `pet-runs/capybara-lulu/qa/action-gifs/`
