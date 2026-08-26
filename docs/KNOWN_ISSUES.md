# Known Issues

| ID | Area | Issue | Impact | Mitigation |
|---|---|---|---|---|
| K001 | Statistics | Stage 1 has 5 seeds per cell | per-cell rates remain noisy and the screen covers many comparisons | label Stage 1 exploratory; report raw counts/uncertainty; confirm selected effects on new held-out seeds |
| K002 | Taxonomy | task-demand groups are introduced by this study | cannot present them as canonical literature categories | state this explicitly |
| K003 | Taxonomy | perturbation-mechanism groups are introduced by this study | mechanism labels may be debatable | preserve official LIBERO-Plus category alongside internal group |
| K004 | Coverage | one OOD variant per task × family cannot represent the full perturbation family | limits family-level generalization | deterministic selection; state limitation; optionally add variants only after main result |
| K005 | OOD difficulty | a chosen moderate variant may still produce a floor | interaction becomes uninterpretable | require OOD-low viability and report floor cells |
| K006 | Model scope | one π0.5 checkpoint | limits cross-model generality | frame as controlled case study, not universal ranking |
| K007 | Environment | LIBERO-Plus replaces/conflicts with vanilla LIBERO namespace | can contaminate ID setup | separate pinned environments |
| K008 | Latency calibration | revised `d*` was chosen from six seeds per calibration cell over 0–400 ms | operating-point selection remains based on a small ID-only calibration | report the full observed curve and freeze `d*` before OOD |
| K009 | Method fairness | Naive async and RTC may differ in policy-call/queue semantics | interaction could reflect implementation mismatch | validate request schedule, horizon, checkpoint, action representation |
| K010 | Freshness metrics | action-age aggregation can be contaminated by holds/startup | misleading mechanism analysis | separate holds/underruns and inspect action-level traces |
| K011 | Runtime drift | native latency may drift across runs/GPU state | changes effective delay | log request latency per request and GPU/environment metadata |
| K012 | Naming | `StaleBench` collides with an unrelated benchmark name | submission ambiguity | use the new descriptive working title unless renamed again |
| K013 | Semantic grounding | mechanism group contains one perturbation family only | mechanism-level comparison is unbalanced | treat group-level result as descriptive |
| K014 | Simulation | no hardware validation | deployment conclusions limited | state simulation-only scope; make no safety claims |
| K015 | Stage 0 protocol revision | Stage 0 used `n_action_steps=25`, six seeds, and 0–400 ms after the original 10-action design performed poorly | the horizon and delay grid are post-pretest revisions, limiting claims of strict preregistration | accepted by D016 using ID-only evidence; disclose the revision and freeze it before OOD |
| K016 | Stage 0 provenance | downloaded episode summary omits repository SHA, checkpoint revision, and environment fingerprint required by the canonical logging specification | full reproducibility and provenance validation are not possible from the bundle | add required identity fields and a validator gate before the compliant rerun |
| K017 | Stage 0 validation | 23 executed hold/underrun actions in seven downloaded episodes have null chunk and source-observation IDs while every episode is marked `ok` | canonical provenance invariants are violated and invalid runs entered aggregation | define provenance for holds or revise the schema explicitly, then make the validator reject invariant violations before aggregation |
| K018 | Stage 1 ID reuse | 24 seed-0/1 ID controls are reused from Stage 0 without immutable runtime identity metadata | exact equivalence to new Stage 1 rows cannot be proven | preserve explicit source labels, report the limitation, and never present the reuse as revision-verified |

| K019 | Horizon semantics | `n_action_steps` may not equal RTC paper execution horizon `s` | incorrect theoretical interpretation | audit adapter; use “configured action coverage” until proven |
| K020 | Stage 1 null | broad OOD×delay interaction is near zero | original headline hypothesis unsupported | report null; test horizon-dependent boundary |
| K021 | Horizon selection | 25 actions was chosen after ID-only 10-action failure | can appear tuned | disclose the revision and characterize the 10–35 local sensitivity surface without re-optimizing Stage 1 |
| K022 | Multiple follow-ups | localized cells follow a broad screen | selective-inference risk | preserve tied families; label sensor noise post-hoc |

| K025 | Missing same-seed Native baselines | Stage 2 originally omitted Native for horizons not present in completed Stage 0/1 | horizon main effects could be confused with added-delay sensitivity | include Native at every Stage 2 horizon using seeds 5..9 |
| K026 | Adaptive Stage 3 horizon choice | choosing lower/transition horizons after seeing Stage 2 could add analyst discretion | OOD follow-up may look post-hoc optimized | freeze Stage 3 horizons at 20,25,30 before Stage 2 |

| K027 | Episode identity | seed equality may not guarantee identical simulator reset | paired comparisons can be invalid | record initialization ID or reset-state fingerprint and assert matching |
| K028 | OOD variant drift | future follow-up could accidentally choose another variant from same family | changes the tested condition | freeze Stage 1 classification ID, API index, exact variant name, and difficulty |
| K029 | Stage 3B selection | cross-task object-layout follow-up is motivated by the observed Stage 3 long-task result | cannot be presented as preregistered family-level confirmation | label Stage 3B targeted/post-Stage-3; freeze its matrix before execution; report all two-task outcomes |
| K032 | Spatial control reuse unavailable | Stage 3 has no `spatial_transport` ID controls | borrowing Stage 1/2 controls would break same-seed Stage 3B matching | run 48 new spatial ID controls on seeds 14..21 |
| K034 | Initialization identity | benchmark episode indices may alias or fail to expose distinct reset states | nominally using indices 0..7 would not guarantee true initialization diversity | mandatory reset-only audit; require eight deterministic distinct fingerprints per task/scene and stop if it fails |

## Issue template

```text
KXXX | Area | Issue | Impact | Mitigation
```

## Current active follow-up

Stage 5 is canceled. Stage 3 New is the active final experiment.

```text
K040 | Interaction precision | Stage 3/3B use only eight rollout seeds per cell | 0.125 cell granularity and very wide interaction uncertainty can make apparent heterogeneity indistinguishable from rollout noise | rerun the complete unique Stage 3/3B matrix with 128 fresh seeds/cell
K041 | Multiple candidate interactions | Stage 3 New reports 6 candidates × 3 horizons | per-cell significance fishing could recreate the original selection problem | report all effects/CIs; h=25 is frozen primary operating point; use direct cross-task interaction contrasts and preserve post-hoc labels
K042 | Shared ID controls | four goal-drawer OOD candidates share the same ID base task | copying ID rows could be mistaken for independent policy rollouts | execute one physical ID episode per task×horizon×delay×seed and reuse by reference in candidate-level analysis
K043 | Compute interruption | Stage 3 New requires 6,912 fresh physical episodes | partial completion could tempt outcome-dependent matrix reduction | deterministic manifest + resume; never choose a favorable subset after interim outcomes
K044 | Prior low-n narrative | current paper language says interactions are sparse/heterogeneous | high-n rerun may contradict it | precommit to revising the narrative in either direction based on Stage 3 New
```
