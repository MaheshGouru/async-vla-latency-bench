# Known Issues

| ID | Area | Issue | Impact | Mitigation |
|---|---|---|---|---|
| K001 | Statistics | Exploratory OOD–Delay Screening has 5 seeds per cell | per-cell rates remain noisy and the screen covers many comparisons | label Exploratory OOD–Delay Screening exploratory; report raw counts/uncertainty; confirm selected effects on new held-out seeds |
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
| K015 | Latency Calibration and Instrumentation protocol revision | Latency Calibration and Instrumentation used `n_action_steps=25`, six seeds, and 0–400 ms after the original 10-action design performed poorly | the horizon and delay grid are post-pretest revisions, limiting claims of strict preregistration | accepted by D016 using ID-only evidence; disclose the revision and freeze it before OOD |
| K016 | Latency Calibration and Instrumentation provenance | downloaded episode summary omits repository SHA, checkpoint revision, and environment fingerprint required by the canonical logging specification | full reproducibility and provenance validation are not possible from the bundle | add required identity fields and a validator gate before the compliant rerun |
| K017 | Latency Calibration and Instrumentation validation | 23 executed hold/underrun actions in seven downloaded episodes have null chunk and source-observation IDs while every episode is marked `ok` | canonical provenance invariants are violated and invalid runs entered aggregation | define provenance for holds or revise the schema explicitly, then make the validator reject invariant violations before aggregation |
| K018 | Exploratory OOD–Delay Screening ID reuse | 24 seed-0/1 ID controls are reused from Latency Calibration and Instrumentation without immutable runtime identity metadata | exact equivalence to new Exploratory OOD–Delay Screening rows cannot be proven | preserve explicit source labels, report the limitation, and never present the reuse as revision-verified |

| K019 | Horizon semantics | `n_action_steps` may not equal RTC paper execution horizon `s` | incorrect theoretical interpretation | audit adapter; use “configured action coverage” until proven |
| K020 | Exploratory OOD–Delay Screening null | broad OOD×delay interaction is near zero | original headline hypothesis unsupported | report null; test horizon-dependent boundary |
| K021 | Horizon selection | 25 actions was chosen after ID-only 10-action failure | can appear tuned | disclose the revision and characterize the 10–35 local sensitivity surface without re-optimizing Exploratory OOD–Delay Screening |
| K022 | Multiple follow-ups | localized cells follow a broad screen | selective-inference risk | preserve tied families; label sensor noise post-hoc |

| K025 | Missing same-seed Native baselines | Confirmatory Horizon–Delay Operating Envelope originally omitted Native for horizons not present in completed Latency Calibration and Instrumentation/1 | horizon main effects could be confused with added-delay sensitivity | include Native at every Confirmatory Horizon–Delay Operating Envelope horizon using seeds 5..9 |
| K026 | Adaptive Held-Out OOD–Delay Horizon Confirmation horizon choice | choosing lower/transition horizons after seeing Confirmatory Horizon–Delay Operating Envelope could add analyst discretion | OOD follow-up may look post-hoc optimized | freeze Held-Out OOD–Delay Horizon Confirmation horizons at 20,25,30 before Confirmatory Horizon–Delay Operating Envelope |

| K027 | Episode identity | seed equality may not guarantee identical simulator reset | paired comparisons can be invalid | record initialization ID or reset-state fingerprint and assert matching |
| K028 | OOD variant drift | future follow-up could accidentally choose another variant from same family | changes the tested condition | freeze Exploratory OOD–Delay Screening classification ID, API index, exact variant name, and difficulty |
| K029 | Held-Out Object-Layout Cross-Task Replication selection | cross-task object-layout follow-up is motivated by the observed Held-Out OOD–Delay Horizon Confirmation long-task result | cannot be presented as preregistered family-level confirmation | label it as post-Held-Out OOD–Delay Horizon Confirmation evidence; freeze its matrix before execution; report all two-task outcomes |
| K032 | Spatial control reuse unavailable | Held-Out OOD–Delay Horizon Confirmation has no `spatial_transport` ID controls | borrowing Exploratory OOD–Delay Screening/2 controls would break same-seed Held-Out Object-Layout Cross-Task Replication matching | run 48 new spatial ID controls on seeds 14..21 |
| K034 | Initialization identity | benchmark episode indices may alias or fail to expose distinct reset states | nominally using indices 0..7 would not guarantee true initialization diversity | mandatory reset-only audit; require eight deterministic distinct fingerprints per task/scene and stop if it fails |

## Issue template

```text
KXXX | Area | Issue | Impact | Mitigation
```

## Current active follow-up

OpenVLA-OFT Temporal-Coverage Calibration is canceled. High-Power OOD–Delay Replication is the active final experiment.

```text
K040 | Interaction precision | Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication use only eight rollout seeds per cell | 0.125 cell granularity and very wide interaction uncertainty can make apparent heterogeneity indistinguishable from rollout noise | rerun the complete unique Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication matrix with 64 fresh seeds/cell
K041 | Multiple candidate interactions | High-Power OOD–Delay Replication reports 6 candidates × 3 horizons | per-cell significance fishing could recreate the original selection problem | report all effects/CIs; h=25 is frozen primary operating point; use direct cross-task interaction contrasts and preserve post-hoc labels
K042 | Shared ID controls | four goal-drawer OOD candidates share the same ID base task | copying ID rows could be mistaken for independent policy rollouts | execute one physical ID episode per task×horizon×delay×seed and reuse by reference in candidate-level analysis
K043 | Compute interruption | High-Power OOD–Delay Replication requires 3,456 fresh physical episodes | partial completion could tempt outcome-dependent matrix reduction | deterministic manifest + resume; never choose a favorable subset after interim outcomes
K044 | Prior low-n narrative | current paper language says interactions are sparse/heterogeneous | high-n rerun may contradict it | precommit to revising the narrative in either direction based on High-Power OOD–Delay Replication
```
