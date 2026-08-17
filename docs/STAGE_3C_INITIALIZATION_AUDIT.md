# Stage 3C — Initialization Diversity and Determinism Audit

## 0. Status and purpose

validation stage. It does **not** run the policy and does **not** produce success
rates.

Stages 3 and 3B used `libero_episode_index:0`, so their rollout seeds quantify
policy/rollout stochasticity at one benchmark reset. Stage 3C establishes whether

Stage 3C asks:

> Do initialization indices `{0..7}` correspond to eight reproducible and distinct
> simulator reset states for the ID task and its exact frozen object-layout OOD
> variant?

Stage 0 and Stage 1 files remain unchanged. Stage 3B is already completed and is
not rerun or relabeled.

## 1. Task/scene scope

Audit all three object-layout task pairs, regardless of which effects later survive

```text
spatial_transport
goal_drawer
long_stove_moka
```

For each task audit two scene conditions:

```text
ID  = standard LIBERO base task
OOD = exact frozen Stage 1 object-layout variant
```

Exact OOD identities:

| Task | `classification_id` | `api_task_index` | `difficulty_level` | Exact `variant_name` |
|---|---:|---:|---:|---|
| `spatial_transport` | `1773` | `1772` | `3` | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15` |
| `goal_drawer` | `1891` | `1890` | `2` | `open_the_middle_drawer_of_the_cabinet_add_13` |
| `long_stove_moka` | `1941` | `1940` | `2` | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25` |

Before resetting, assert literal equality of task, suite, base task id, perturbation
key, classification id, API index, difficulty, and exact variant name against the
frozen Stage 1 variant artifact. Do not resolve a new variant.

## 2. Initialization indices

Audit exactly:

```text
INITIALIZATION_INDICES = [0,1,2,3,4,5,6,7]
```

Do not choose indices based on success outcomes; Stage 3C has no policy outcomes.
Do not silently wrap, clamp, modulo, or fall back to index 0.

For every reset, log both:

```text
requested_initialization_index
resolved_initialization_index_or_id
```

and assert the requested index is the one actually resolved by the benchmark.

### 2.1 Seed/RNG semantics for Stage 3C

Stage 3C has **no policy/rollout seeds** because no policy inference is executed.
`initialization_index` is the scientific reset-state axis. If the environment
constructor requires an RNG seed, use exactly:

```text
STAGE3C_ENV_CONSTRUCTION_SEED = 0
```

for every task, scene, initialization index, and repeat. The constructor seed must
not vary by task, scene, index, or repeat. Record it in every audit row. If changing
only the repeat number changes the scientifically relevant reset fingerprint under
this fixed constructor seed, the determinism gate fails. Do not search for another
constructor seed that makes the audit pass.

## 3. Repeated-reset determinism protocol

For each fixed:

```text
(task_key, scene_condition, exact_variant_identity, initialization_index)
```

perform exactly **3 independent environment constructions/resets** from a clean
reset path. No policy inference or action stepping is allowed before fingerprinting.

Total reset-only audit operations:

```text
3 tasks
× 2 scene conditions (ID, object-layout OOD)
× 8 initialization indices
× 3 repeated resets
= 144 reset/fingerprint operations
```

Use the same canonical MuJoCo reset-state fingerprint implementation validated in
Stage 3. It must exclude simulator time and unstable serialization while including
scientifically relevant reset state.

### 3.1 Within-index determinism gate

For every task/scene/index:

```text
number of repeated resets = 3
number of unique fingerprints = 1
```

Any task/scene/index with more than one fingerprint fails Stage 3C.

### 3.2 Across-index distinctness gate

For each fixed task/scene, the eight certified fingerprints for indices `0..7`
must contain:

```text
8 unique fingerprints
```

If two requested indices resolve to the same scientifically relevant reset state,
Stage 3C fails for that task/scene. Do not replace an index with 8, 9, or another
index after seeing the audit.

### 3.3 ID ↔ OOD fingerprints

Do **not** require the ID and object-layout OOD fingerprints at the same index to
be equal. Object layout intentionally changes scene geometry. Pairing is by the
benchmark initialization index and all non-treatment runtime factors, not by
identical geometry.

## 4. Stage 3C output artifact

Write:

```text
stage3c_initialization_audit.csv
stage3c_validated_initializations.csv
stage3c_initialization_audit.json
```

`stage3c_initialization_audit.csv` must contain one row per reset operation (144
rows if all complete) with at least:

```text
task_key
scene_condition
variant_name_or_id
requested_initialization_index
resolved_initialization_index_or_id
repeat_id
initial_state_fingerprint
fingerprint_schema_version
libero_git_sha
libero_plus_git_sha
benchmark_repo_sha
env_construction_seed
```

`stage3c_validated_initializations.csv` must contain one certified row per
`task × scene × initialization_index` (48 rows) and may be written only if every
required gate passes.

Record SHA-256 hashes for the Stage 3C spec and both CSV artifacts.

## 6. What Stage 3C does not establish

Stage 3C establishes only that the initialization axis is usable and reproducible.
It does not establish robustness, an OOD × delay interaction, or generalization.

## Executed outcome — 2026-08-16

The audit completed and failed closed exactly as intended. For all three frozen OOD object-layout variants, requested initialization indices `1..7` resolved to initialization `0`. Each OOD variant therefore exposes only **one distinct initialization state**, not eight.

```text
audit operations = 144
validated rows = 0
validation errors = 27
status = failed_closed
```

Archive provenance:

```text
stage3c_results.tar.gz
SHA-256 f38bde65fe1d87ecb90a9dbe53ef42a6eef361938317308dc8b5803f65455413
```

Scientific interpretation: cross-initialization robustness cannot be evaluated for these frozen OOD variants through the benchmark's nominal initialization-index interface. Do not substitute indices and do not treat rollout seeds as initialization diversity.
