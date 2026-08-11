# Known Issues

| ID | Area | Issue | Impact | Mitigation |
|---|---|---|---|---|
| K001 | Statistics | Stage 1 has only 2 seeds per cell | per-cell rates are very noisy | label Stage 1 exploratory; confirm selected effects on new seeds |
| K002 | Taxonomy | task-demand groups are introduced by this study | cannot present them as canonical literature categories | state this explicitly |
| K003 | Taxonomy | perturbation-mechanism groups are introduced by this study | mechanism labels may be debatable | preserve official LIBERO-Plus category alongside internal group |
| K004 | Coverage | one OOD variant per task × family cannot represent the full perturbation family | limits family-level generalization | deterministic selection; state limitation; optionally add variants only after main result |
| K005 | OOD difficulty | a chosen moderate variant may still produce a floor | interaction becomes uninterpretable | require OOD-low viability and report floor cells |
| K006 | Model scope | one π0.5 checkpoint | limits cross-model generality | frame as controlled case study, not universal ranking |
| K007 | Environment | LIBERO-Plus replaces/conflicts with vanilla LIBERO namespace | can contaminate ID setup | separate pinned environments |
| K008 | Latency calibration | `d*` is chosen from six seeds per calibration cell (was two until 2026-08-11) | selected operating point is still an order statistic, so residual noise biases it low | use all six viable task × method cells; report full curve; freeze before OOD |
| K009 | Method fairness | Naive async and RTC may differ in policy-call/queue semantics | interaction could reflect implementation mismatch | validate request schedule, horizon, checkpoint, action representation |
| K010 | Freshness metrics | action-age aggregation can be contaminated by holds/startup | misleading mechanism analysis | separate holds/underruns and inspect action-level traces |
| K011 | Runtime drift | native latency may drift across runs/GPU state | changes effective delay | log request latency per request and GPU/environment metadata |
| K012 | Naming | `StaleBench` collides with an unrelated benchmark name | submission ambiguity | use the new descriptive working title unless renamed again |
| K013 | Semantic grounding | mechanism group contains one perturbation family only | mechanism-level comparison is unbalanced | treat group-level result as descriptive |
| K014 | Simulation | no hardware validation | deployment conclusions limited | state simulation-only scope; make no safety claims |

## Issue template

```text
KXXX | Area | Issue | Impact | Mitigation
```
