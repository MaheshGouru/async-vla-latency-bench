# Implementation Status

Last updated: 2026-08-22

## Completed stages

```text
Latency Calibration and Instrumentation — COMPLETE WITH KNOWN PROVENANCE LIMITATIONS (K015–K018)
Exploratory OOD–Delay Screening — COMPLETE
Confirmatory Horizon–Delay Operating Envelope — COMPLETE
Held-Out OOD–Delay Horizon Confirmation — COMPLETE
Held-Out Object-Layout Cross-Task Replication — COMPLETE
Initialization-State Audit — COMPLETE, FAILED CLOSED
Object-Layout Generalization — COMPLETE
Multi-Stage Task Generalization — COMPLETE
Cross-Policy OpenVLA-OFT Diagnostic — COMPLETE (PRELIMINARY NATIVE-8 DIAGNOSTIC)
OpenVLA-OFT Temporal-Coverage Calibration — ACTIVE NEXT
```

The completed Latency Calibration and Instrumentation and Exploratory OOD–Delay Screening specifications/results are frozen and must not be
retroactively edited.

Verified Exploratory OOD–Delay Screening result archive:

```text
/Users/tejasrikurapati/Downloads/stage1_results.tar.gz
SHA-256 10a615ebaee14f6e604e32bac751ee4ae33400b8fb7aee5f0a10bd9cc5869441
480/480 results; missing=0; invalid=0
```

## Confirmatory Horizon–Delay Operating Envelope — complete

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
- [x] validate Confirmatory Horizon–Delay Operating Envelope initialization pairing across all horizon/delay cells
- [x] record reset-state fingerprints
- [x] 360 RTC episodes; missing=0; invalid=0
- [x] local success surfaces
- [x] retain Exploratory OOD–Delay Screening at 25/+200; do not re-optimize it

Verified archive: `stage2_results.tar.gz`, SHA-256
`8e2d6a572a210913f02302907380c8e1af5c98dfb41edd8ac5e1d52d06b88d44`.

## Held-Out OOD–Delay Horizon Confirmation — complete

Frozen held-out seeds:

```text
[14,15,16,17,18,19,20,21]
```

- [x] horizons frozen before Confirmatory Horizon–Delay Operating Envelope: `20,25,30`
- [x] implementation guard prevents Confirmatory Horizon–Delay Operating Envelope from changing Held-Out OOD–Delay Horizon Confirmation horizons
- [x] object layout × long task encoded
- [x] robot initial state × goal task encoded
- [x] lighting × goal task encoded
- [x] sensor noise × goal task labeled post-hoc replication
- [x] Native/+200 ms encoded
- [x] same 8 seeds in every condition
- [x] exact Exploratory OOD–Delay Screening variant identities asserted
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


## Held-Out Object-Layout Cross-Task Replication — targeted cross-task object-layout replication

Frozen seeds:

```text
[14,15,16,17,18,19,20,21]
```

- [x] exact `spatial_transport` object-layout variant asserted: `1773/1772`, difficulty 3, `..._add_15`
- [x] exact `goal_drawer` object-layout variant asserted: `1891/1890`, difficulty 2, `..._add_13`
- [x] RTC only; horizons `20,25,30`; Native/+200 ms
- [x] every new run uses `libero_episode_index:0`
- [x] six-cell reset-fingerprint pairing passes for every new task/scene/seed
- [x] reuse 48 completed Held-Out OOD–Delay Horizon Confirmation goal-ID rows without new run IDs
- [x] run 48 new spatial-ID rows
- [x] run 96 new object-layout OOD rows
- [x] exactly 144 new episodes
- [x] two-task analysis = 192 unique rows after Held-Out OOD–Delay Horizon Confirmation goal-ID reuse
- [x] three-task object-layout synthesis = 288 unique rows after Held-Out OOD–Delay Horizon Confirmation reuse
- [x] report task-specific interactions before any pooled summary

Held-Out Object-Layout Cross-Task Replication is COMPLETE. It remains post-Held-Out OOD–Delay Horizon Confirmation targeted replication; do not relabel it preregistered.


## Initialization-State Audit — initialization diversity/determinism audit — COMPLETE, FAILED CLOSED

Initialization-State Audit executed the frozen reset-only audit over initialization indices `0..7`.

Observed OOD benchmark behavior:

```text
goal_drawer/object_layout:       indices 1..7 resolve to 0; 1 distinct OOD initialization
long_stove_moka/object_layout:    indices 1..7 resolve to 0; 1 distinct OOD initialization
spatial_transport/object_layout:  indices 1..7 resolve to 0; 1 distinct OOD initialization
```

The audit correctly failed the required eight-distinct-initialization gate. This is a benchmark capability limitation, not an implementation failure. No rollout-based initialization-diversity experiment should be dispatched for these frozen OOD variants.

Preserved Initialization-State Audit archive:

```text
stage3c_results.tar.gz
SHA-256 f38bde65fe1d87ecb90a9dbe53ef42a6eef361938317308dc8b5803f65455413
```


## Completed-results integration

Authoritative concise numerical record: `COMPLETED_RESULTS_LEDGER.md`.

- Confirmatory Horizon–Delay Operating Envelope: 360/360 valid; at +200 ms, h20/h25/h30 each achieve 14/15 pooled success while h10 is 6/15; severe queue underruns are confined to short coverage.
- Held-Out OOD–Delay Horizon Confirmation: 288/288 valid; long-task × object-layout is the only prespecified candidate with a negative interaction at all three frozen horizons.
- Held-Out Object-Layout Cross-Task Replication: complete. `spatial_transport` has I=0 at all three horizons; `goal_drawer` is non-negative; `long_stove_moka` remains negative at all three horizons.
- Initialization-State Audit: complete, failed closed because all three OOD variants expose one distinct initialization.

## Object-Layout Generalization — COMPLETE

Frozen analysis matrix:

```text
task = long_stove_moka
3 new object-layout variants
RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = 22..29
libero_episode_index = 0
64/64 analysis episodes valid
```

Observed interactions:

```text
c1950 / level3_sample1: I = -0.375
c1953 / level4_sample2: I = +0.125
c1955 / level4_sample4: I = -0.125
mean I = -0.125
negative in 2/3 new variants
```

The frozen Object-Layout Generalization gate passed.

## Multi-Stage Task Generalization — COMPLETE

Frozen analysis matrix:

```text
task = LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket
3 deterministic object-layout variants
RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = 30..37
libero_episode_index = 0
64 analysis episodes
```

Observed interactions:

```text
I = -0.375, +0.250, +0.625
negative in 1/3 variants
mean I = +0.167
```

Decision: the negative `long_stove_moka` object-layout × delay pattern does not generalize consistently to the second multi-stage task.

## Cross-Policy OpenVLA-OFT Diagnostic — second-policy OpenVLA-OFT replication — COMPLETE

Completed 64-row analysis matrix at native/default coverage 8.

```text
spatial_transport: ID Native 8/8; ID +200 6/8; OOD Native 8/8; OOD +200 8/8; I=+0.250 [0.000,0.500]
long_stove_moka:   ID Native 1/8; ID +200 0/8; OOD Native 0/8; OOD +200 0/8; I=+0.125 [0.000,0.375]
```

The long task is floor-limited. Added latency also produced substantial queue starvation under the 8-action horizon. Cross-Policy OpenVLA-OFT Diagnostic is therefore retained as a completed native-stack preliminary diagnostic, not the final calibrated cross-policy experiment.

## OpenVLA-OFT Temporal-Coverage Calibration — CANCELED BEFORE EXECUTION

No further OpenVLA policy runs are planned.

The OpenVLA-OFT Temporal-Coverage Calibration protocol is retained for provenance only and must not be dispatched.

## High-Power OOD–Delay Replication — ACTIVE FINAL EXPERIMENT

Authoritative spec:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

Frozen matrix:

```text
policy = π0.5
method = RTC
candidate pairs = 6 exact frozen Held-Out OOD–Delay Horizon Confirmation / Held-Out Object-Layout Cross-Task Replication task × perturbation pairs
include Held-Out OOD–Delay Horizon Confirmation post-hoc goal_drawer × sensor_noise = yes
horizons = 20,25,30
delay = Native,+200 ms
seeds = 46..109
fresh seeds = 64
libero_episode_index = 0
shared ID controls = yes
new physical episodes = 3,456
```

Primary dataset must contain only the new seed block. Do not pool old Held-Out OOD–Delay Horizon Confirmation /
Held-Out Object-Layout Cross-Task Replication rows into the primary high-power estimates.

Implementation priority:

```text
1. manifest generator with exact six-candidate freeze
2. deterministic resumable runner
3. shared-ID execution without duplicate physical rows
4. per-seed six-cell reset-pairing audit
5. 64-seed clustered bootstrap analysis
6. low-n versus high-n comparison figure
```
