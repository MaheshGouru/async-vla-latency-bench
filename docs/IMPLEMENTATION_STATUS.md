# Implementation Status

Last updated: 2026-08-16

## Completed stages

```text
Stage 0 — COMPLETE WITH KNOWN PROVENANCE LIMITATIONS (K015–K018)
Stage 1 — COMPLETE
```

The completed Stage 0 and Stage 1 specifications/results are frozen and must not be
retroactively edited.

Verified Stage 1 result archive:

```text
/Users/tejasrikurapati/Downloads/stage1_results.tar.gz
SHA-256 10a615ebaee14f6e604e32bac751ee4ae33400b8fb7aee5f0a10bd9cc5869441
480/480 results; missing=0; invalid=0
```

## Stage 2 — next / required

Spec:

```text
STAGE_2_LOCAL_OPERATING_POINT_SENSITIVITY.md
```

Frozen seeds:

```text
[5,6,7,8,9]
```

- [ ] audit RTC `n_action_steps` semantics
- [ ] horizons = 10,15,20,25,30,35
- [ ] delays = Native,100,200,300 ms
- [ ] all 3 ID tasks
- [ ] same 5 seeds in every condition
- [ ] 360 RTC episodes
- [ ] local success surfaces
- [ ] classify 25/+200 as stable/sensitive/under-covered
- [ ] do not re-optimize Stage 1

## Stage 3 — required after Stage 2

Frozen held-out seeds:

```text
[14,15,16,17,18,19,20,21]
```

- [x] horizons frozen before Stage 2: `20,25,30`
- [ ] do not change Stage 3 horizons after viewing Stage 2
- [ ] object layout × long task
- [ ] robot initial state × goal task
- [ ] lighting × goal task
- [ ] sensor noise × goal task only as post-hoc replication
- [ ] Native/+200 ms
- [ ] same 8 seeds in every condition
- [ ] 240 episodes primary, 288 including sensor noise

## Stage 4 — conditional

Frozen seeds if run:

```text
[22,23,24,25,26]
```

- [ ] only after Stage 2/3
- [ ] official VLASH compatibility gate
- [ ] at most 2 replicated prespecified OOD candidates
- [ ] match 25 actions and Native/+200 if semantically fair
- [ ] maximum ~80 analysis episodes
- [ ] skip rather than approximate

## Exact next action

```text
Audit how `n_action_steps` maps into RTC execution semantics, then generate the
360-row Stage 2 manifest using seeds [5,6,7,8,9].
```
