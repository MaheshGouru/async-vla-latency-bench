# Stage 4 — Conditional VLASH Matched Subset

## 0. Status

**Optional. Run only after Stages 2 and 3.**

VLASH is useful only if the official implementation can be matched fairly to the
π0.5/LIBERO setup. Do not approximate it.

## 1. Frozen Stage 4 seeds

If the compatibility gate passes, use exactly:

```text
SEEDS = [22, 23, 24, 25, 26]
```

These are disjoint from:

```text
Stage 1: [0,1,2,3,4]
Stage 2: [5,6,7,8,9]
revised Stage 0 extra seeds: [10,11,12,13]
Stage 3: [14,15,16,17,18,19,20,21]
```

Use the same five Stage 4 seeds for every matched method/scene/delay condition.

## 2. Compatibility gate

Verify:

```text
official repository + commit
exact π0.5 compatibility
training/fine-tuning requirements
LIBERO observation/action semantics
control frequency
normalization
prediction/execution semantics
latency semantics
provenance hooks
```

Stop if:
- only an approximate VLASH reimplementation is feasible;
- checkpoint/training assumptions cannot be matched;
- action/control semantics are incomparable;
- integration threatens the paper deadline.

## 2A. Episode matching requirement

If Stage 4 runs, it must reuse the exact `classification_id`, `api_task_index`, and
`variant_name` carried from Stage 1 into Stage 3.

For each selected condition, RTC and VLASH must share:

```text
task
variant
seed
scene
delay
initialization identity
```

Only execution method may differ.

If the official VLASH stack cannot preserve these episode semantics, fail the
compatibility gate.

## 3. Candidate selection

Run at most two **prespecified Stage 3 candidates that replicate**.

Do not promote post-hoc sensor noise solely to fill the quota.

Freeze candidate selection before VLASH outcomes.

## 4. Matched configuration

Use the original Stage 1 reference configuration whenever VLASH permits a fair
match:

```text
n_action_steps = 25
delay ∈ {Native, Native +200 ms}
methods = {RTC, VLASH}
seeds = [22,23,24,25,26]
```

If a fair 25-action match is impossible, stop and document the incompatibility
instead of choosing a favorable replacement.

## 5. Maximum core matrix

For two candidates:

```text
2 candidates
× 2 scenes
× 2 delays
× 2 methods
× 5 seeds
= 80 analysis episodes
```

Matching ID controls may be shared when candidates use the same base task.

## 6. Main question

> Does a second modern asynchronous alignment strategy reproduce or alter the
> localized OOD-under-delay phenomenon observed with RTC?

VLASH is external validation, not a new headline benchmark.

## 7. Kill rule

Skip Stage 4 if Stages 2/3 are incomplete or if a validated matched rollout cannot
be obtained within one working day.
