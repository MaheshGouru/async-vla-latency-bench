# Stage 4 — conditional official VLASH validation

Stage 4 is optional and fail-closed. Run these notebooks in order only after the
complete Stage 3 validator and analysis pass.

1. `01_official_vlash_compatibility_gate.ipynb` records the pinned official
   repository/checkpoint audit. A package import alone is not a pass.
2. `02_review_and_freeze_candidates.ipynb` reads complete Stage 3 results and
   freezes one or two reviewed prespecified candidates before VLASH outcomes.
3. `03_freeze_matched_manifest.ipynb` creates the unique physical episode
   manifest, sharing ID controls by base task.

The rollout, smoke, analysis, and export notebooks remain intentionally absent
until the official VLASH π0.5/LIBERO compatibility gate passes. Do not replace
VLASH with a home-grown asynchronous approximation.

