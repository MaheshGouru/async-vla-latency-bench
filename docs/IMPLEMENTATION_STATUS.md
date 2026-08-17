# Implementation Status

Last updated: 2026-08-16

## Completed stages

```text
Stage 0 — COMPLETE WITH KNOWN PROVENANCE LIMITATIONS (K015–K018)
Stage 1 — COMPLETE
Stage 2 — COMPLETE
Stage 3 — COMPLETE
Stage 3B — COMPLETE
```

The completed Stage 0 and Stage 1 specifications/results are frozen and must not be
retroactively edited.

Verified Stage 1 result archive:

```text
/Users/tejasrikurapati/Downloads/stage1_results.tar.gz
SHA-256 10a615ebaee14f6e604e32bac751ee4ae33400b8fb7aee5f0a10bd9cc5869441
480/480 results; missing=0; invalid=0
```

## Stage 2 — complete

Spec:

```text
STAGE_2_LOCAL_OPERATING_POINT_SENSITIVITY.md
```

Frozen seeds:

```text
[5,6,7,8,9]
```

- [x] audit RTC `n_action_steps` semantics
- [x] horizons = 10,15,20,25,30,35
- [x] delays = Native,100,200,300 ms
- [x] all 3 ID tasks
- [x] same 5 seeds in every condition
- [x] validate Stage 2 initialization pairing across all horizon/delay cells
- [x] record reset-state fingerprints
- [x] 360 RTC episodes; missing=0; invalid=0
- [x] local success surfaces
- [x] retain Stage 1 at 25/+200; do not re-optimize it

Verified archive: `stage2_results.tar.gz`, SHA-256
`8e2d6a572a210913f02302907380c8e1af5c98dfb41edd8ac5e1d52d06b88d44`.

## Stage 3 — complete

Frozen held-out seeds:

```text
[14,15,16,17,18,19,20,21]
```

- [x] horizons frozen before Stage 2: `20,25,30`
- [x] implementation guard prevents Stage 2 from changing Stage 3 horizons
- [x] object layout × long task encoded
- [x] robot initial state × goal task encoded
- [x] lighting × goal task encoded
- [x] sensor noise × goal task labeled post-hoc replication
- [x] Native/+200 ms encoded
- [x] same 8 seeds in every condition
- [x] exact Stage 1 variant identities asserted
- [x] pre-dispatch horizon/delay pairing validator implemented
- [x] isolated seed-999 end-to-end smoke workflow (no analysis seed used)
- [x] versioned canonical MuJoCo reset fingerprint excludes sim time and unstable serialization
- [x] repeated-reset fingerprint audit persisted for all 48 pairing identities
- [x] notebooks 01–03 persist preflight, pairing, and smoke provenance artifacts
- [x] resume validates JSON/Parquet triplets and reruns corrupted episodes
- [x] primary accounting deduplicates the 96 shared ID episodes by `run_id`
- [x] paired bootstrap resamples the eight complete seed clusters
- [x] post-hoc sensor noise excluded from the prespecified aggregate figure/table
- [x] 240 episodes primary, 288 including sensor noise


## Stage 3B — targeted cross-task object-layout replication

Frozen seeds:

```text
[14,15,16,17,18,19,20,21]
```

- [x] exact `spatial_transport` object-layout variant asserted: `1773/1772`, difficulty 3, `..._add_15`
- [x] exact `goal_drawer` object-layout variant asserted: `1891/1890`, difficulty 2, `..._add_13`
- [x] RTC only; horizons `20,25,30`; Native/+200 ms
- [x] every new run uses `libero_episode_index:0`
- [x] six-cell reset-fingerprint pairing passes for every new task/scene/seed
- [x] reuse 48 completed Stage 3 goal-ID rows without new run IDs
- [x] run 48 new spatial-ID rows
- [x] run 96 new object-layout OOD rows
- [x] exactly 144 new episodes
- [x] two-task analysis = 192 unique rows after Stage 3 goal-ID reuse
- [x] three-task object-layout synthesis = 288 unique rows after Stage 3 reuse
- [x] report task-specific interactions before any pooled summary

Stage 3B is COMPLETE. It remains post-Stage-3 targeted replication; do not relabel it preregistered.


## Stage 3C — initialization diversity/determinism audit — COMPLETE, FAILED CLOSED

Stage 3C executed the frozen reset-only audit over initialization indices `0..7`.

Observed OOD benchmark behavior:

```text
goal_drawer/object_layout:       indices 1..7 resolve to 0; 1 distinct OOD initialization
long_stove_moka/object_layout:    indices 1..7 resolve to 0; 1 distinct OOD initialization
spatial_transport/object_layout:  indices 1..7 resolve to 0; 1 distinct OOD initialization
```

The audit correctly failed the required eight-distinct-initialization gate. This is a benchmark capability limitation, not an implementation failure. No rollout-based initialization-diversity experiment should be dispatched for these frozen OOD variants.

Preserved Stage 3C archive:

```text
stage3c_results.tar.gz
SHA-256 f38bde65fe1d87ecb90a9dbe53ef42a6eef361938317308dc8b5803f65455413
```


## Completed-results integration

Authoritative concise numerical record: `COMPLETED_RESULTS_LEDGER.md`.

- Stage 2: 360/360 valid; at +200 ms, h20/h25/h30 each achieve 14/15 pooled success while h10 is 6/15; severe queue underruns are confined to short coverage.
- Stage 3: 288/288 valid; long-task × object-layout is the only prespecified candidate with a negative interaction at all three frozen horizons.
- Stage 3B: complete. `spatial_transport` has I=0 at all three horizons; `goal_drawer` is non-negative; `long_stove_moka` remains negative at all three horizons.
- Stage 3C: complete, failed closed because all three OOD variants expose one distinct initialization.

## Active next experiments

See `POST_STAGE3C_NEXT_EXPERIMENTS.md`.

1. **Experiment A — required next:** `long_stove_moka` only, 3 new deterministic object-layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `[22..29]`, `libero_episode_index=0`, **64 new episodes**.
2. **Experiment B — conditional:** only if Experiment A passes its frozen gate; one additional `libero_10` multi-stage task, 3 object-layout variants, RTC, `n_action_steps=25`, Native/+200 ms, seeds `[30..37]`, `libero_episode_index=0`, **64 new episodes**.

Do not reinterpret rollout seeds as environment-initialization diversity.


## Final pre-dispatch repository audit (2026-08-17)

**Experiment A is implemented and run-ready, but has not yet been executed.** The implementation includes:

- a dedicated deterministic frozen-variant resolver and hashed CSV;
- the exact 64-row physical manifest with 16 shared ID controls and 48 OOD episodes;
- an explicit `experiment_a` provenance label and explicit requested/resolved initialization index 0;
- initialization-pairing audit, seed-999 smoke manifest, resumable single-GPU runner, and fail-closed validation;
- per-variant four-cell summaries and paired-seed bootstrap interactions;
- a machine-enforced Experiment-B gate that requires both the frozen scientific criteria and a complete passing validation record.

Experiment B remains blocked until completed Experiment-A results satisfy that frozen gate.

## Experiment B implementation status (2026-08-17)

**Experiment B is implemented and conditionally run-ready, but has not been executed.** Its code does not authorize dispatch by itself. Variant resolution, manifest creation, seed-999 smoke creation, rollout dispatch, validation, and analysis all require the hashed passing `experiment_a_to_b_v1` gate.

Implemented safeguards and workflow:

- exact frozen `libero_10` task 0 name assertion;
- deterministic three-variant object-layout resolver and immutable hashed CSV;
- exact 64-row matrix with 16 physically unique shared ID controls and 48 OOD episodes;
- RTC horizon 25, Native/+200 ms, seeds 30–37, and explicit requested/resolved initialization index 0;
- 8-episode seed-999 smoke outside the analysis seed set;
- detached, resumable, serial ID-then-OOD single-A100 notebooks under `notebooks/experiment_b_jupyter/`;
- fail-closed artifact/provenance validation and paired-seed per-variant interaction analysis;
- unique 64-row episode-accounting output so shared ID controls cannot be pooled three times.

Do not run Experiment B unless Experiment A notebook 05 produces a passing gate with `experiment_b_dispatch=true`.

No superseded follow-up work is part of the active experiment plan.
