# Implementation Status

Last updated: 2026-08-16

## Completed stages

```text
Stage 0 — COMPLETE WITH KNOWN PROVENANCE LIMITATIONS (K015–K018)
Stage 1 — COMPLETE
Stage 2 — COMPLETE
Stage 3 — COMPLETE
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

- [ ] exact `spatial_transport` object-layout variant asserted: `1773/1772`, difficulty 3, `..._add_15`
- [ ] exact `goal_drawer` object-layout variant asserted: `1891/1890`, difficulty 2, `..._add_13`
- [ ] RTC only; horizons `20,25,30`; Native/+200 ms
- [ ] every new run uses `libero_episode_index:0`
- [ ] six-cell reset-fingerprint pairing passes for every new task/scene/seed
- [ ] reuse 48 completed Stage 3 goal-ID rows without new run IDs
- [ ] run 48 new spatial-ID rows
- [ ] run 96 new object-layout OOD rows
- [ ] exactly 144 new episodes
- [ ] two-task analysis = 192 unique rows after Stage 3 goal-ID reuse
- [ ] three-task object-layout synthesis = 288 unique rows after Stage 3 reuse
- [ ] report task-specific interactions before any pooled summary

Stage 3B is post-Stage-3 targeted replication; do not label it preregistered.

## Stage 4 — conditional

Frozen seeds if run:

```text
[22,23,24,25,26]
```

- [ ] only after Stage 2/3
- [x] fail-closed official VLASH compatibility audit scaffold
- [x] reviewed pre-outcome candidate freeze and shared-ID manifest accounting
- [x] Stage 4 notebooks 01–03 stop on incomplete Stage 3 or failed compatibility
- [ ] official VLASH-trained π0.5/LIBERO checkpoint and semantic adapter validated
- [ ] at most 2 replicated prespecified OOD candidates selected after Stage 3
- [ ] matched smoke, rollout, validation, and analysis notebooks (blocked on gate)
- [ ] match 25 actions and Native/+200 if semantically fair
- [ ] maximum ~80 analysis episodes
- [ ] skip rather than approximate

## Exact next action

```text
Implement and freeze `STAGE_3B_OBJECT_LAYOUT_CROSS_TASK_REPLICATION.md`, audit the
144-new-episode manifest and Stage 3 control-reuse table, then execute Stage 3B
serially on one A100. Do not consume Stage 4 seeds `[22..26]`.
```
