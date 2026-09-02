# Completed Results Ledger

This file is the authoritative concise record of completed empirical results after Stage 1. It does not replace the frozen conduct specifications.

## Stage 1 — broad OOD × delay screen — COMPLETE

Frozen analysis configuration:

```text
policy = lerobot/pi05_libero_finetuned
n_action_steps = 25
methods = Naive async, RTC
delay = Native, Native + 200 ms
seeds = 0,1,2,3,4
3 tasks × 7 OOD families
480 analysis episodes
```

Aggregate success:

| scene | Native | +200 ms | delay change |
|---|---:|---:|---:|
| ID | 60.0% | 56.7% | -3.3 pp |
| OOD | 60.0% | 58.1% | -1.9 pp |

Pooled interaction:

```text
I = [S(OOD,+200)-S(OOD,Native)] - [S(ID,+200)-S(ID,Native)]
  ≈ +1.4 pp
```

Decision: **do not claim broad OOD amplification of delay sensitivity.** Stage 1 is a broad exploratory screen. Localized negative RTC interactions motivated held-out follow-up, especially long-task × object layout.

Selected RTC family-level Stage-1 interactions included:

```text
object layout       -13.3 pp
lighting             -6.7 pp
robot initial state  -6.7 pp
sensor noise         -6.7 pp   (secondary/post-hoc follow-up only)
```

The full Stage-1 screen, including null/positive cells, must remain reported.

---

## Stage 2 — RTC local operating-point sensitivity — COMPLETE

Frozen design:

```text
RTC only
ID only
n_action_steps = 10,15,20,25,30,35
added_delay_ms = 0,100,200,300
seeds = 5,6,7,8,9
3 tasks
360/360 episodes valid
```

Pooled success over the three tasks (15 trials/cell):

| n_action_steps | Native | +100 | +200 | +300 |
|---:|---:|---:|---:|---:|
| 10 | 14/15 | 13/15 | 6/15 | 5/15 |
| 15 | 14/15 | 15/15 | 15/15 | 12/15 |
| 20 | 14/15 | 14/15 | 14/15 | 13/15 |
| 25 | 15/15 | 15/15 | 14/15 | 13/15 |
| 30 | 15/15 | 15/15 | 14/15 | 15/15 |
| 35 | 15/15 | 13/15 | 14/15 | 15/15 |

At the Stage-1 delay of +200 ms:

```text
h=20: 14/15
h=25: 14/15
h=30: 14/15
h=10:  6/15
```

Queue-underrun/hold totals across 15 episodes per cell:

```text
h=10: Native 50, +100 519, +200 1385, +300 1765
h=15: Native 0,  +100 9,   +200 72,   +300 343
h=20: Native 0,  +100 0,   +200 0,    +300 3
h=25: 0 at all tested delays
h=30: 0 at all tested delays
h=35: 0 at all tested delays
```

Decision: **retain the frozen Stage-1 operating point `n_action_steps=25, +200 ms`.** It lies in a broad local high-success region rather than at an isolated optimum. The robust short-coverage failure is at 10 actions by +200 ms, and is accompanied by severe queue underruns.

RTC causal delay-estimation mismatch is treated as an implementation/provenance diagnostic, not an explanation for the h=10 failure; aggregate error is not uniquely elevated at h=10.

---

## Stage 3 — held-out OOD × horizon confirmation — COMPLETE

Frozen design:

```text
RTC only
horizons = 20,25,30
delays = Native,+200 ms
held-out seeds = 14..21
240 primary episodes
48 separately labeled post-hoc sensor-noise episodes
288/288 total episodes valid
```

At `n_action_steps=25`:

| condition | ID Native -> +200 | OOD Native -> +200 | interaction I_25 |
|---|---|---|---:|
| long_stove_moka × object layout | 7/8 -> 8/8 | 3/8 -> 2/8 | **-0.25** |
| goal_drawer × robot initial state | 7/8 -> 6/8 | 8/8 -> 8/8 | +0.125 |
| goal_drawer × lighting | 7/8 -> 6/8 | 5/8 -> 6/8 | +0.25 |
| goal_drawer × sensor noise | 7/8 -> 6/8 | 8/8 -> 8/8 | +0.125 (post-hoc) |

For `long_stove_moka × object_layout`, the interaction has the same negative direction throughout the frozen neighborhood:

```text
h=20: I = -0.125; OOD 3/8 -> 2/8
h=25: I = -0.250; OOD 3/8 -> 2/8
h=30: I = -0.125; OOD 4/8 -> 3/8
```

Primary aggregate accounting, with shared ID rows deduplicated:

| horizon | ID Native | ID +200 | prespecified OOD Native | prespecified OOD +200 |
|---:|---:|---:|---:|---:|
| 20 | 14/16 | 13/16 | 16/24 | 14/24 |
| 25 | 14/16 | 14/16 | 16/24 | 16/24 |
| 30 | 15/16 | 15/16 | 16/24 | 16/24 |

Decision: most Stage-1 localized negative interactions **do not replicate** on held-out rollouts. Object layout on the long multi-stage task is the surviving directionally consistent candidate, but most of its performance loss is an OOD main effect; the additional +200-ms penalty is modest (one extra failure of eight per horizon).

---

## Stage 3B — targeted cross-task object-layout replication — COMPLETE

Frozen conduct:

```text
new OOD tasks = spatial_transport, goal_drawer
perturbation = exact frozen Stage-1 object-layout variant
RTC only
horizons = 20,25,30
delays = Native,+200 ms
seeds = 14..21
libero_episode_index = 0
144 new episodes
288 unique rows in final three-task object-layout analysis after Stage-3 reuse
```

Completed interactions:

| task | task-demand type | h=20 | h=25 | h=30 |
|---|---|---:|---:|---:|
| `spatial_transport` | single-stage transport | 0.000 | 0.000 | 0.000 |
| `goal_drawer` | articulated/contact-rich | +0.125 | +0.125 | 0.000 |
| `long_stove_moka` | multi-stage/sequential | -0.125 | -0.250 | -0.125 |

Raw four-cell results:

```text
spatial_transport:
  h20  ID 8/8->8/8; OOD 8/8->8/8
  h25  ID 8/8->8/8; OOD 8/8->8/8
  h30  ID 8/8->8/8; OOD 8/8->8/8

goal_drawer:
  h20  ID 6/8->5/8; OOD 8/8->8/8
  h25  ID 7/8->6/8; OOD 8/8->8/8
  h30  ID 7/8->7/8; OOD 8/8->8/8

long_stove_moka:
  h20  ID 8/8->8/8; OOD 3/8->2/8
  h25  ID 7/8->8/8; OOD 3/8->2/8
  h30  ID 8/8->8/8; OOD 4/8->3/8
```

Decision: **object layout is not a task-general family-level vulnerability in the evaluated set.** The interaction is absent on spatial transport, non-negative on goal drawer, and consistently negative only on the multi-stage stove/moka task. The active follow-up therefore tests layout-variant generalization *within* `long_stove_moka`, followed conditionally by a different multi-stage task.

Archive:

```text
stage3b_results.tar.gz
SHA-256 d4ab1b7ad75fec70ca7a6d48a6e3f11458bab84f0ee5c59daa96c19bb50a50c2
```

---

## Stage 3C — initialization diversity/determinism audit — COMPLETE, FAILED CLOSED

Frozen audit:

```text
3 tasks × {ID, exact object-layout OOD}
requested initialization indices = 0..7
3 clean reset repetitions per requested index
144 reset/fingerprint operations
no policy rollouts
```

Observed OOD behavior for all three frozen object-layout variants:

```text
goal_drawer:       requested indices 1..7 resolved to 0
long_stove_moka:   requested indices 1..7 resolved to 0
spatial_transport: requested indices 1..7 resolved to 0
```

Each OOD variant therefore exposes only **one distinct initialization state** through this interface. The eight-distinct-initialization gate failed by design.

Decision:

- initialization-generalization cannot be evaluated for these frozen OOD variants;
- do not substitute indices;
- do not reinterpret rollout seeds as environment-initialization diversity;
- this benchmark limitation does not invalidate Stages 1–3B.

Preserved archive:

```text
stage3c_results.tar.gz
SHA-256 f38bde65fe1d87ecb90a9dbe53ef42a6eef361938317308dc8b5803f65455413
```

---

## Experiment A — within-task object-layout variant generalization — COMPLETE

Frozen design:

```text
task = long_stove_moka
3 new deterministic object-layout variants
RTC
n_action_steps = 25
delay = Native,+200 ms
seeds = 22..29
libero_episode_index = 0
64/64 valid analysis episodes
```

Results:

| new layout variant | OOD Native | OOD +200 | ID Native | ID +200 | interaction I |
|---|---:|---:|---:|---:|---:|
| `c1950 / level3_sample1` | 6/8 | 3/8 | 6/8 | 6/8 | **-0.375** |
| `c1953 / level4_sample2` | 4/8 | 5/8 | 6/8 | 6/8 | +0.125 |
| `c1955 / level4_sample4` | 8/8 | 7/8 | 6/8 | 6/8 | **-0.125** |

```text
2/3 new variants negative
mean I = -0.125
```

Decision: the negative `long_stove_moka` interaction is not unique to the original `_add_25` layout, but is not universal across layouts.

---

## Experiment B — additional multi-stage task generalization — COMPLETE

Frozen design:

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

Completed interactions:

```text
I = -0.375, +0.250, +0.625
negative in 1/3 variants
mean I = +0.167
```

Decision: the negative object-layout × delay pattern does **not** generalize consistently to the second multi-stage task. Do not claim a monotonic atomic-turn effect or a general multi-stage vulnerability.

---

## Stage 4 — OpenVLA-OFT native-8 second-policy diagnostic — COMPLETE

```text
spatial_transport:
  ID Native 8/8
  ID +200  6/8
  OOD Native 8/8
  OOD +200 8/8
  I = +0.250; paired-bootstrap 95% CI [0.000,0.500]

long_stove_moka:
  ID Native 1/8
  ID +200  0/8
  OOD Native 0/8
  OOD +200 0/8
  I = +0.125; paired-bootstrap 95% CI [0.000,0.375]
```

Interpretation: the π0.5 negative long-task interaction did not transfer cleanly, but the OpenVLA long-task test is floor-limited. Native/default 8-action coverage also showed substantial queue starvation under +200 ms.

---

## Active next experiment — Stage 5 OpenVLA-OFT temporal-coverage calibration

First determine whether the checkpoint legitimately exposes more than 8 future actions from one inference. If it does, run ID-only calibration and freeze a locally stable coverage before any OOD rerun. If 8 is the native maximum, do not fabricate a longer horizon; retain Stage 4 as the native-horizon diagnostic.

---

## Stage 3 New — high-power replication — ACTIVE

This is a prospective experiment and therefore has no result rows yet.

Purpose:

> Re-estimate the complete unique Stage 3 / Stage 3B interaction matrix at high
> replication to determine whether the earlier sparse/heterogeneous pattern is
> reproducible rather than a consequence of `n=8` rollout noise.

Frozen design:

```text
π0.5 + RTC
6 unique task × perturbation pairs
horizons = 20,25,30
delay = Native,+200 ms
seeds = 46..81
n = 36 fresh seeds per unique cell
old Stage 3/3B rows excluded from primary analysis
shared ID controls across perturbations on the same task
physical episodes = 1,944
```

Do not add any Stage 3 New result to this ledger until the validation gates in
`STAGE_3_NEW_HIGH_POWER_REPLICATION.md` pass.
