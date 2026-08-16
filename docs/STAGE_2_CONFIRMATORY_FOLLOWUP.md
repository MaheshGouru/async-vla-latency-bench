# Stage 2 — Confirmatory Follow-Up

## 0. Purpose

Stage 2 tests whether the strongest **predefined candidate OOD × delay interactions** from Stage 1 replicate on new seeds.

Do not call Stage 1 confirmatory. Do not select Stage 2 conditions informally.

## 1. Inputs

Required:

```text
selected_high_delay.json
stage1_resolved_variants.csv
stage1_episode_results.csv
stage1_table_four_cell.csv
stage1_table_perturbation_summary.csv
```

All Stage 0 and Stage 1 configuration must remain frozen.

The frozen action horizon is:

```text
policy.n_action_steps = 25
```

## 2. Candidate eligibility

A perturbation family is eligible only when:

```text
pooled OOD-low success >= 25%
```

and the task/method subset used for the candidate satisfies:

```text
ID-low success >= 50%
```

Do not select a family whose apparent interaction is driven entirely by floor performance.

## 3. Candidate ranking

Using **all Stage 1 exploratory results**:

1. Compute `I` for every task × perturbation × method.
2. Compute the predefined pooled perturbation-family `I`.
3. Rank eligible perturbation families from most negative to most positive `I`.
4. Select the **two most-negative eligible perturbation families**.
5. For each selected family, select the task-demand group with the most-negative task-level interaction.
6. If both selected families resolve to the same task group, keep both; do not force task diversity.
7. Freeze the selected `(task, perturbation family)` pairs before running new seeds.

Optional third candidate:

- only if its `I` is comparable to the second candidate;
- and it represents a different mechanism group;
- and compute/time remains.

## 4. Held-out seeds

Stage 1 used:

```text
0, 1, 2, 3, 4
```

Preferred Stage 2 held-out seeds:

```text
14, 15, 16, 17, 18, 19, 20, 21
```

Frozen target:

```text
8 new held-out seeds
```

Do not change the held-out set based on intermediate outcomes.

## 5. Conditions per selected candidate

For each selected task × perturbation pair:

```text
scene:
    ID
    OOD

delay:
    Native
    Native + d*

method:
    Naive async
    RTC
```

The OOD variant must be the exact Stage 1 frozen variant.

## 6. Reuse rules

Stage 2 OOD episodes are always new held-out seeds.

ID controls may be shared between selected perturbations on the same base task when all of these match:

```text
seed
task
method
delay
checkpoint
n_action_steps
environment fingerprint
camera configuration
normalization
```

## 7. Compute budget

With **8 new seeds**, per selected candidate:

```text
OOD:
2 delays × 2 methods × 8 seeds
= 32 new OOD episodes
```

ID controls per unique selected task:

```text
2 delays × 2 methods × 8 seeds
= 32 new ID episodes
```

For two selected candidates:

- if both use the same task: **96 new episodes**;
- if they use two different tasks: **128 new episodes**.

Do not reduce the confirmatory set after inspecting intermediate outcomes. If
resource constraints prevent completing all eight seeds, report Stage 2 as
incomplete rather than silently redefining the frozen design.

## 8. Primary confirmatory quantities

For each selected task × perturbation × method:

```text
I_heldout =
  [S_heldout(OOD, high) - S_heldout(OOD, low)]
  -
  [S_heldout(ID, high) - S_heldout(ID, low)]
```

Report:

```text
raw success counts
Wilson intervals for each success cell
I_heldout
bootstrap interval for I_heldout when feasible
paired seed differences
```

The most important question:

> Does the **direction and approximate magnitude** of the candidate Stage 1 interaction replicate on held-out seeds?

## 9. Exploratory versus confirmatory reporting

Report Stage 1 and Stage 2 separately.

Correct wording:

> “A complete low-budget screen identified candidate interactions using a frozen selection rule. We then evaluated those candidates on held-out seeds.”

Do not write:

> “We tested several conditions and report the ones that worked.”

For descriptive plots, Stage 1 + Stage 2 seeds may additionally be pooled, but clearly label the pooled estimate as **combined descriptive evidence**, not the held-out confirmatory test itself.

## 10. Method interaction

For each confirmed candidate compare:

```text
I_Naive
I_RTC
```

and:

```text
ΔI_method = I_RTC - I_Naive
```

Also report whether method ranking under `ID-high` differs from method ranking under `OOD-high`.

## 11. Statistical model

When episode count supports it, fit:

```text
logit P(success) =
    β0
  + β1 OOD
  + β2 HighDelay
  + β3 RTC
  + β4 OOD×HighDelay
  + β5 OOD×RTC
  + β6 HighDelay×RTC
  + β7 OOD×HighDelay×RTC
```

Interpret:

- `β4`: OOD × delay interaction under the reference execution method;
- `β7`: whether RTC changes that interaction.

Do not rely on p-values alone. Report raw counts and effect sizes.

## 12. Required outputs

```text
stage2_selection.json
stage2_manifest.csv
stage2_episode_results.csv
stage2_four_cell_results.csv
stage2_interactions.csv
stage2_method_comparison.csv

stage2_confirmatory_interaction.png
stage2_method_interaction.png

STAGE_2_OBSERVATIONS.md
```

## 13. Results gate

A candidate is considered replicated when:

1. the held-out interaction has the same qualitative direction as Stage 1;
2. the effect is not explained by ID-low or OOD-low floor;
3. raw cell counts support the claimed pattern;
4. no systematic simulator/configuration failure explains the result.

If the candidates do not replicate, report that result. Do not select a new candidate after seeing Stage 2 outcomes and call it confirmatory.
