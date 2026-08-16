# Experiment Matrix — After Completed Stage 1

## Seed allocation

```text
Stage 1 completed exploratory:  [0,1,2,3,4]
Stage 2 local sensitivity:      [5,6,7,8,9]
Stage 0 additional ID seeds:    [10,11,12,13]  (already completed)
Stage 3 held-out confirmation:  [14,15,16,17,18,19,20,21]
Stage 4 conditional VLASH:      [22,23,24,25,26]
```

Seed sets are fixed and disjoint across new stages.

## Stage 2 — required

```text
RTC
n_action_steps = 10,15,20,25,30,35
delay = Native,100,200,300 ms
3 ID tasks
5 seeds = 5..9

6 × 4 × 3 × 5 = 360 episodes
```

Purpose: defend the already-used 25/+200 operating point against local
configuration sensitivity.

## Stage 3 — required after Stage 2

```text
RTC
frozen horizons = 20,25,30
    20 = -5 around Stage 1
    25 = Stage 1 reference
    30 = +5 around Stage 1

delay = Native,+200 ms
8 held-out seeds = 14..21
```

Primary OOD candidates:
- object layout;
- robot initial state;
- lighting.

Post-hoc:
- sensor noise.

Maximum with post-hoc sensor noise: **288 episodes**.
Without sensor noise: **240 episodes**.

## Stage 4 — conditional

```text
RTC vs VLASH
n_action_steps = 25
Native/+200 ms
up to 2 replicated OOD candidates
5 new seeds = 22..26
```

Maximum core: **80 analysis episodes**.
