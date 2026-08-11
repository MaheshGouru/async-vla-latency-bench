# Stage 1 — Broad Exploratory Screen: OOD × Inference Delay in π0.5 on LIBERO-Plus

## 0. Purpose

**Primary question**

> **Which kinds of distribution shift become especially harmful under inference delay, and does that depend on the behavioral demands of the manipulation task?**

Stage 1 is an **exploratory screen**, not the final confirmatory experiment. It evaluates all seven official LIBERO-Plus perturbation families on three preselected base tasks chosen to represent three different task-demand groups.

The screen is intentionally broad and low-replication. Its purpose is to identify candidate **OOD × delay interactions** for higher-replication follow-up.

Do **not** select or change tasks, perturbation variants, delay settings, metrics, or selection criteria after looking at Stage 1 outcomes.

---

## 0A. Canonical terminology

Use these exact display labels in generated tables, plots, and paper text:

**Task-demand groups**

```text
Single-stage transport
Articulated/contact-rich
Multi-stage/sequential
```

**Perturbation-mechanism groups**

```text
Trajectory adaptation
Perceptual localization
Appearance invariance
Semantic grounding
```

Machine-readable snake-case keys may be used internally, but every human-facing output must map back to these display labels.

---

## 1. Policy and execution methods

### Policy

Use exactly:

```text
lerobot/pi05_libero_finetuned
```

The LeRobot checkpoint is trained on `HuggingFaceVLA/libero`, and the official LeRobot LIBERO evaluation uses:

```text
policy.n_action_steps = 10
```

Keep `n_action_steps=10` for Stage 1.

### Execution methods

Run exactly two asynchronous execution methods:

```text
naive_async
rtc
```

Do not include blocking execution in the Stage 1 factorial. Blocking/ideal runs may be retained as historical reference but are not part of the primary Stage 1 interaction analysis.

---

## 2. Task-demand taxonomy

The following taxonomy is **our experimental taxonomy**, not an official LIBERO taxonomy.

Use these labels exactly in logs, plots, and paper drafts.

| `task_group` | Meaning | Selected base task |
|---|---|---|
| `single_stage_transport` | A relatively short pick-and-place behavior dominated by transport between grasp and placement | Pick up the black bowl from table center and place it on the plate |
| `articulated_contact_rich` | Manipulation in which successful contact/alignment with an articulated object is central | Open the middle drawer of the cabinet |
| `multi_stage_sequential` | A task requiring multiple ordered subgoals whose errors can propagate across stages | Turn on the stove and put the moka pot on it |

### Important terminology

Do **not** call `single_stage_transport` a “coarse-motion task.” Pick-and-place still contains precise grasp and placement phases.

Do **not** claim these three groups are a standard literature taxonomy. In the paper, describe them as:

> “We stratify tasks by behavioral demand into single-stage transport, articulated/contact-rich manipulation, and multi-stage sequential manipulation.”

---

## 3. Exact base tasks

LIBERO's task API is zero-indexed: `task_suite.get_task(task_id)`.

Use these three base tasks exactly:

| `task_key` | `suite` | Standard LIBERO `task_id` | Exact LIBERO task name | `task_group` |
|---|---:|---:|---|---|
| `spatial_transport` | `libero_spatial` | **2** | `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate` | `single_stage_transport` |
| `goal_drawer` | `libero_goal` | **0** | `open_the_middle_drawer_of_the_cabinet` | `articulated_contact_rich` |
| `long_stove_moka` | `libero_10` | **2** | `KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it` | `multi_stage_sequential` |

### Required pre-run assertion

Before running any episodes:

```python
assert task_suite.get_task(task_id).name == EXPECTED_TASK_NAME
```

for all three base tasks.

### Relationship to earlier experiments

These are the **Stage 1 screening tasks defined here**. Do not silently substitute earlier preliminary task IDs. If historical runs used another task index, keep those runs separate and label them as prior/preliminary data.

---

## 4. Perturbation taxonomy

LIBERO-Plus defines seven official perturbation dimensions. We preserve those official perturbation labels and add a second, internal mechanism grouping.

| `perturbation_key` | Official LIBERO-Plus category | Internal `mechanism_group` | Interpretation used in this paper |
|---|---|---|---|
| `object_layout` | `Objects Layout` | `trajectory_adaptation` | Target displacement / confounding-object changes alter task geometry and can require a different trajectory |
| `robot_initial_state` | `Robot Initial States` | `trajectory_adaptation` | A changed manipulator start pose requires adaptation from a different configuration |
| `camera_viewpoint` | `Camera Viewpoints` | `perceptual_localization` | Camera position/orientation/FOV changes affect visual localization and spatial interpretation |
| `sensor_noise` | `Sensor Noise` | `perceptual_localization` | Image degradation stresses reliable state/object localization from observations |
| `light_conditions` | `Light Conditions` | `appearance_invariance` | Illumination changes should ideally preserve the underlying task geometry |
| `background_textures` | `Background Textures` | `appearance_invariance` | Scene/surface appearance changes should ideally not require a different control objective |
| `language_instructions` | `Language Instructions` | `semantic_grounding` | Instruction rewriting stresses language-conditioned task grounding |

### Exact mechanism groups

Use only these four internal labels:

```text
trajectory_adaptation
perceptual_localization
appearance_invariance
semantic_grounding
```

### Paper wording

Use:

> “We organize the seven official LIBERO-Plus perturbation families into four mechanism-oriented groups: trajectory adaptation, perceptual localization, appearance invariance, and semantic grounding.”

Immediately clarify:

> “These mechanism groups are an analysis taxonomy introduced for this study; the underlying seven perturbation dimensions are defined by LIBERO-Plus.”

---

## 5. Exactly which LIBERO-Plus variant to run

LIBERO-Plus contains many variants of each base task within each perturbation family. Stage 1 uses **one preselected OOD variant per `(base task, perturbation family)`**, giving 21 OOD task variants.

### Do not hand-pick variants

Variant selection must be deterministic and outcome-independent.

Use the official:

```text
libero/libero/benchmark/task_classification.json
```

The file contains:

```text
id
name
category
difficulty_level
```

for LIBERO-Plus tasks.

### Deterministic selection rule

For each of the 3 base tasks and each of the 7 official perturbation categories:

1. Filter entries in the matching suite whose `name` starts with the exact base-task name.
2. Filter to the exact official perturbation `category`.
3. Prefer entries with `difficulty_level == 2`.
4. If multiple level-2 entries exist, select the entry with the **smallest official `id`**.
5. If no level-2 entry exists:
   - select the entry minimizing `abs(difficulty_level - 2)`;
   - break ties using the smallest official `id`.
6. Freeze the resulting 21 variants **before any Stage 1 policy outcomes are inspected**.
7. Save the resolved mapping to:

```text
stage1_resolved_variants.csv
```

### Why level 2?

Stage 1 is intended to test nontrivial but non-extreme OOD shifts. Selecting the first deterministic moderate-difficulty variant avoids choosing variants based on π0.5 outcomes.

### LIBERO-Plus ID convention

Record **both**:

```text
classification_id
api_task_index
```

The official `task_classification.json` uses an `id` field, while the benchmark API indexes tasks with zero-based `get_task(i)`.

Do not assume the conversion silently. Resolve and verify it.

For the current official repository ordering, test:

```python
candidate_api_index = classification_id - 1
assert plus_suite.get_task(candidate_api_index).name == variant_name
```

If this assertion fails, determine the index by exact name lookup:

```python
names = plus_suite.get_task_names()
api_task_index = names.index(variant_name)
assert plus_suite.get_task(api_task_index).name == variant_name
```

The **exact task name is the canonical identifier** for Stage 1.

### Resolver script

Run this once in the LIBERO-Plus environment and save its output.

```python
import csv
import json
from pathlib import Path

from libero.libero import benchmark

TASKS = [
    {
        "task_key": "spatial_transport",
        "suite": "libero_spatial",
        "base_task_id": 2,
        "base_name": "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate",
        "task_group": "single_stage_transport",
    },
    {
        "task_key": "goal_drawer",
        "suite": "libero_goal",
        "base_task_id": 0,
        "base_name": "open_the_middle_drawer_of_the_cabinet",
        "task_group": "articulated_contact_rich",
    },
    {
        "task_key": "long_stove_moka",
        "suite": "libero_10",
        "base_task_id": 2,
        "base_name": "KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
        "task_group": "multi_stage_sequential",
    },
]

PERTURBATIONS = [
    ("object_layout", "Objects Layout", "trajectory_adaptation"),
    ("robot_initial_state", "Robot Initial States", "trajectory_adaptation"),
    ("camera_viewpoint", "Camera Viewpoints", "perceptual_localization"),
    ("sensor_noise", "Sensor Noise", "perceptual_localization"),
    ("light_conditions", "Light Conditions", "appearance_invariance"),
    ("background_textures", "Background Textures", "appearance_invariance"),
    ("language_instructions", "Language Instructions", "semantic_grounding"),
]

classification_path = Path(
    "libero/libero/benchmark/task_classification.json"
)

with classification_path.open() as f:
    classification = json.load(f)

benchmark_dict = benchmark.get_benchmark_dict()

rows = []

for task in TASKS:
    suite_name = task["suite"]
    suite = benchmark_dict[suite_name]()

    # Verify base task identity separately in the standard-LIBERO environment.
    # In LIBERO-Plus, suite ordering contains thousands of perturbed tasks.

    names = suite.get_task_names()

    for perturbation_key, category, mechanism_group in PERTURBATIONS:
        candidates = [
            x for x in classification[suite_name]
            if x["name"].startswith(task["base_name"])
            and x["category"] == category
        ]

        if not candidates:
            raise RuntimeError(
                f"No LIBERO-Plus candidate for "
                f"{suite_name=} {task['base_name']=} {category=}"
            )

        candidates.sort(
            key=lambda x: (
                abs(int(x["difficulty_level"]) - 2),
                int(x["id"]),
            )
        )
        chosen = candidates[0]

        # Never rely on id -> index conversion without verification.
        guessed_index = int(chosen["id"]) - 1
        if (
            0 <= guessed_index < len(names)
            and names[guessed_index] == chosen["name"]
        ):
            api_task_index = guessed_index
        else:
            api_task_index = names.index(chosen["name"])

        assert suite.get_task(api_task_index).name == chosen["name"]

        rows.append({
            "task_key": task["task_key"],
            "suite": suite_name,
            "base_task_id": task["base_task_id"],
            "base_task_name": task["base_name"],
            "task_group": task["task_group"],
            "perturbation_key": perturbation_key,
            "official_category": category,
            "mechanism_group": mechanism_group,
            "classification_id": chosen["id"],
            "api_task_index": api_task_index,
            "variant_name": chosen["name"],
            "difficulty_level": chosen["difficulty_level"],
        })

with open("stage1_resolved_variants.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

assert len(rows) == 21
print("Wrote 21 frozen Stage-1 OOD variants.")
```

### Mandatory provenance

Record:

```text
LIBERO_PLUS_GIT_SHA = <git rev-parse HEAD>
LEROBOT_GIT_SHA     = <git rev-parse HEAD>
MODEL_REVISION      = <resolved Hugging Face revision if pinned>
```

Do not start the screen until `stage1_resolved_variants.csv` and these revisions are saved.

---

## 5A. Dependency on Stage 0 latency calibration

Before Stage 1, run [`STAGE_0_LATENCY_CALIBRATION.md`](STAGE_0_LATENCY_CALIBRATION.md).

Stage 0 uses **ID only** to select one frozen high-delay value `d*` from `+100` through `+700 ms`.

Stage 1 then **does test OOD under latency**: every one of the 21 selected LIBERO-Plus OOD variants is evaluated at both **Native** and **Native + d*** under both **Naive async** and **RTC**.

The selected value must be loaded from:

```text
selected_high_delay.json
```

Do not select or modify `d*` using OOD outcomes.

---

## 6. Delay conditions

Use exactly two delay conditions.

### `low`

```text
delay_condition = low
added_delay_ms = 0
```

This means **native inference latency**. It does not mean zero request latency.

### `high`

```text
delay_condition = high
added_delay_ms = d*
```

`d*` must be chosen using **ID-only calibration**, before examining LIBERO-Plus OOD outcomes.

### Calibration rule for `d*`

Test candidate added delays:

```text
100 ms
200 ms
300 ms
```

using the three standard LIBERO base tasks and both execution methods.

Choose **one common `d*` for the entire Stage 1 screen** satisfying, as closely as possible:

1. delay causes visible degradation relative to native;
2. performance is not driven to floor across most task/method cells;
3. the same `d*` is used for every task, perturbation family, and method.

Prefer the smallest candidate that creates a useful separation without widespread saturation.

Once selected:

```text
HIGH_DELAY_MS = d*
```

is frozen.

Do **not**:
- use `+700 ms` by default;
- choose a different high delay for RTC and naive async;
- choose a different high delay for each task;
- recalibrate using OOD outcomes.

Log both wall-clock delay in milliseconds and effective logical delay in control steps.

---

## 7. Stage 1 factorial

### Factors

```text
task_group:
    3 levels

perturbation:
    7 OOD families + shared ID control

delay_condition:
    low
    high

execution_method:
    naive_async
    rtc

seed:
    2 exploratory seeds
```

Use the same two seed values in every condition.

Recommended frozen seeds:

```text
seed = 0
seed = 1
```

If the existing harness requires another seed convention, choose two fixed seeds before running and record them here. Do not change seeds by condition.

### OOD episodes

```text
3 tasks
× 7 perturbations
× 2 delays
× 2 execution methods
× 2 seeds
= 168 OOD episodes
```

### Shared ID controls

The same ID condition is reused across all seven perturbations:

```text
3 tasks
× 2 delays
× 2 execution methods
× 2 seeds
= 24 ID episodes
```

### Total Stage 1 budget

```text
168 OOD + 24 ID = 192 episodes
```

Do **not** rerun ID separately for each perturbation family.

---

## 7A. Complete experiment table
This section enumerates the **entire Stage 1 run plan** using the same display terminology as the analysis taxonomy.

- **96 unique condition blocks**
- **2 fixed seeds per condition** (`0`, `1`)
- **192 total episodes**
- ID controls are shared across perturbation families and are therefore listed only once per task × method × delay.
- For OOD rows, the exact LIBERO-Plus `classification_id`, `api_task_index`, and `variant_name` are filled from `stage1_resolved_variants.csv` before execution.

### 7A.1 Condition-level matrix — 96 conditions
| # | Scene | Task-demand group | Suite:task_id | Perturbation | Perturbation mechanism | Method | Delay | Seeds | Episodes |
|---:|---|---|---|---|---|---|---|---|---:|
| 1 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | Naive async | Native | `0, 1` | 2 |
| 2 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | Naive async | Native + d* | `0, 1` | 2 |
| 3 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | RTC | Native | `0, 1` | 2 |
| 4 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | RTC | Native + d* | `0, 1` | 2 |
| 5 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | Naive async | Native | `0, 1` | 2 |
| 6 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | Naive async | Native + d* | `0, 1` | 2 |
| 7 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | RTC | Native | `0, 1` | 2 |
| 8 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | RTC | Native + d* | `0, 1` | 2 |
| 9 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | Naive async | Native | `0, 1` | 2 |
| 10 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | Naive async | Native + d* | `0, 1` | 2 |
| 11 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | RTC | Native | `0, 1` | 2 |
| 12 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | RTC | Native + d* | `0, 1` | 2 |
| 13 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | Naive async | Native | `0, 1` | 2 |
| 14 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | Naive async | Native + d* | `0, 1` | 2 |
| 15 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | RTC | Native | `0, 1` | 2 |
| 16 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | RTC | Native + d* | `0, 1` | 2 |
| 17 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | Naive async | Native | `0, 1` | 2 |
| 18 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | `0, 1` | 2 |
| 19 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | RTC | Native | `0, 1` | 2 |
| 20 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | RTC | Native + d* | `0, 1` | 2 |
| 21 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | Naive async | Native | `0, 1` | 2 |
| 22 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | `0, 1` | 2 |
| 23 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | RTC | Native | `0, 1` | 2 |
| 24 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | RTC | Native + d* | `0, 1` | 2 |
| 25 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | Naive async | Native | `0, 1` | 2 |
| 26 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | Naive async | Native + d* | `0, 1` | 2 |
| 27 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | RTC | Native | `0, 1` | 2 |
| 28 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | RTC | Native + d* | `0, 1` | 2 |
| 29 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | Naive async | Native | `0, 1` | 2 |
| 30 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | Naive async | Native + d* | `0, 1` | 2 |
| 31 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | RTC | Native | `0, 1` | 2 |
| 32 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | RTC | Native + d* | `0, 1` | 2 |
| 33 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | Naive async | Native | `0, 1` | 2 |
| 34 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | Naive async | Native + d* | `0, 1` | 2 |
| 35 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | RTC | Native | `0, 1` | 2 |
| 36 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | RTC | Native + d* | `0, 1` | 2 |
| 37 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | Naive async | Native | `0, 1` | 2 |
| 38 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | Naive async | Native + d* | `0, 1` | 2 |
| 39 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | RTC | Native | `0, 1` | 2 |
| 40 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | RTC | Native + d* | `0, 1` | 2 |
| 41 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | Naive async | Native | `0, 1` | 2 |
| 42 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | Naive async | Native + d* | `0, 1` | 2 |
| 43 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | RTC | Native | `0, 1` | 2 |
| 44 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | RTC | Native + d* | `0, 1` | 2 |
| 45 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | Naive async | Native | `0, 1` | 2 |
| 46 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | `0, 1` | 2 |
| 47 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | RTC | Native | `0, 1` | 2 |
| 48 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | RTC | Native + d* | `0, 1` | 2 |
| 49 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | Naive async | Native | `0, 1` | 2 |
| 50 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | `0, 1` | 2 |
| 51 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | RTC | Native | `0, 1` | 2 |
| 52 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | RTC | Native + d* | `0, 1` | 2 |
| 53 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | Naive async | Native | `0, 1` | 2 |
| 54 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | Naive async | Native + d* | `0, 1` | 2 |
| 55 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | RTC | Native | `0, 1` | 2 |
| 56 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | RTC | Native + d* | `0, 1` | 2 |
| 57 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | Naive async | Native | `0, 1` | 2 |
| 58 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | Naive async | Native + d* | `0, 1` | 2 |
| 59 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | RTC | Native | `0, 1` | 2 |
| 60 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | RTC | Native + d* | `0, 1` | 2 |
| 61 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | Naive async | Native | `0, 1` | 2 |
| 62 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | Naive async | Native + d* | `0, 1` | 2 |
| 63 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | RTC | Native | `0, 1` | 2 |
| 64 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | RTC | Native + d* | `0, 1` | 2 |
| 65 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | Naive async | Native | `0, 1` | 2 |
| 66 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | Naive async | Native + d* | `0, 1` | 2 |
| 67 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | RTC | Native | `0, 1` | 2 |
| 68 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | RTC | Native + d* | `0, 1` | 2 |
| 69 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | Naive async | Native | `0, 1` | 2 |
| 70 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | Naive async | Native + d* | `0, 1` | 2 |
| 71 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | RTC | Native | `0, 1` | 2 |
| 72 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | RTC | Native + d* | `0, 1` | 2 |
| 73 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | Naive async | Native | `0, 1` | 2 |
| 74 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | `0, 1` | 2 |
| 75 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | RTC | Native | `0, 1` | 2 |
| 76 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | RTC | Native + d* | `0, 1` | 2 |
| 77 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | Naive async | Native | `0, 1` | 2 |
| 78 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | `0, 1` | 2 |
| 79 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | RTC | Native | `0, 1` | 2 |
| 80 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | RTC | Native + d* | `0, 1` | 2 |
| 81 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | Naive async | Native | `0, 1` | 2 |
| 82 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | Naive async | Native + d* | `0, 1` | 2 |
| 83 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | RTC | Native | `0, 1` | 2 |
| 84 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | RTC | Native + d* | `0, 1` | 2 |
| 85 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | Naive async | Native | `0, 1` | 2 |
| 86 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | Naive async | Native + d* | `0, 1` | 2 |
| 87 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | RTC | Native | `0, 1` | 2 |
| 88 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | RTC | Native + d* | `0, 1` | 2 |
| 89 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | Naive async | Native | `0, 1` | 2 |
| 90 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | Naive async | Native + d* | `0, 1` | 2 |
| 91 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | RTC | Native | `0, 1` | 2 |
| 92 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | RTC | Native + d* | `0, 1` | 2 |
| 93 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | Naive async | Native | `0, 1` | 2 |
| 94 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | Naive async | Native + d* | `0, 1` | 2 |
| 95 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | RTC | Native | `0, 1` | 2 |
| 96 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | RTC | Native + d* | `0, 1` | 2 |

### 7A.2 Episode-level execution manifest — all 192 planned episodes
This table is the exact planned episode set. It can be copied directly into a run manifest generator.

| Exp. | Scene | Task-demand group | Suite:task_id | Perturbation | Mechanism group | Method | Delay | Seed | Variant source |
|---:|---|---|---|---|---|---|---|---:|---|
| E001 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | Naive async | Native | 0 | Standard LIBERO base task |
| E002 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | Naive async | Native | 1 | Standard LIBERO base task |
| E003 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | Naive async | Native + d* | 0 | Standard LIBERO base task |
| E004 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | Naive async | Native + d* | 1 | Standard LIBERO base task |
| E005 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | RTC | Native | 0 | Standard LIBERO base task |
| E006 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | RTC | Native | 1 | Standard LIBERO base task |
| E007 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | RTC | Native + d* | 0 | Standard LIBERO base task |
| E008 | ID | Single-stage transport | `libero_spatial:2` | ID control | ID control | RTC | Native + d* | 1 | Standard LIBERO base task |
| E009 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | Naive async | Native | 0 | Standard LIBERO base task |
| E010 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | Naive async | Native | 1 | Standard LIBERO base task |
| E011 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | Naive async | Native + d* | 0 | Standard LIBERO base task |
| E012 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | Naive async | Native + d* | 1 | Standard LIBERO base task |
| E013 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | RTC | Native | 0 | Standard LIBERO base task |
| E014 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | RTC | Native | 1 | Standard LIBERO base task |
| E015 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | RTC | Native + d* | 0 | Standard LIBERO base task |
| E016 | ID | Articulated/contact-rich | `libero_goal:0` | ID control | ID control | RTC | Native + d* | 1 | Standard LIBERO base task |
| E017 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | Naive async | Native | 0 | Standard LIBERO base task |
| E018 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | Naive async | Native | 1 | Standard LIBERO base task |
| E019 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | Naive async | Native + d* | 0 | Standard LIBERO base task |
| E020 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | Naive async | Native + d* | 1 | Standard LIBERO base task |
| E021 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | RTC | Native | 0 | Standard LIBERO base task |
| E022 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | RTC | Native | 1 | Standard LIBERO base task |
| E023 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | RTC | Native + d* | 0 | Standard LIBERO base task |
| E024 | ID | Multi-stage/sequential | `libero_10:2` | ID control | ID control | RTC | Native + d* | 1 | Standard LIBERO base task |
| E025 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E026 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E027 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E028 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E029 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E030 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E031 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E032 | OOD | Single-stage transport | `libero_spatial:2` | Object layout | Trajectory adaptation | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E033 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E034 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E035 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E036 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E037 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E038 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E039 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E040 | OOD | Single-stage transport | `libero_spatial:2` | Robot initial state | Trajectory adaptation | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E041 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E042 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E043 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E044 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E045 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E046 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E047 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E048 | OOD | Single-stage transport | `libero_spatial:2` | Camera viewpoint | Perceptual localization | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E049 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E050 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E051 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E052 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E053 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E054 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E055 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E056 | OOD | Single-stage transport | `libero_spatial:2` | Sensor noise | Perceptual localization | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E057 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E058 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E059 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E060 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E061 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E062 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E063 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E064 | OOD | Single-stage transport | `libero_spatial:2` | Lighting | Appearance invariance | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E065 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E066 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E067 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E068 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E069 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E070 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E071 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E072 | OOD | Single-stage transport | `libero_spatial:2` | Background texture | Appearance invariance | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E073 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E074 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E075 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E076 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E077 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E078 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E079 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E080 | OOD | Single-stage transport | `libero_spatial:2` | Language instruction | Semantic grounding | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E081 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E082 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E083 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E084 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E085 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E086 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E087 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E088 | OOD | Articulated/contact-rich | `libero_goal:0` | Object layout | Trajectory adaptation | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E089 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E090 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E091 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E092 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E093 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E094 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E095 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E096 | OOD | Articulated/contact-rich | `libero_goal:0` | Robot initial state | Trajectory adaptation | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E097 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E098 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E099 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E100 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E101 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E102 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E103 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E104 | OOD | Articulated/contact-rich | `libero_goal:0` | Camera viewpoint | Perceptual localization | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E105 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E106 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E107 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E108 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E109 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E110 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E111 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E112 | OOD | Articulated/contact-rich | `libero_goal:0` | Sensor noise | Perceptual localization | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E113 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E114 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E115 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E116 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E117 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E118 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E119 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E120 | OOD | Articulated/contact-rich | `libero_goal:0` | Lighting | Appearance invariance | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E121 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E122 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E123 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E124 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E125 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E126 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E127 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E128 | OOD | Articulated/contact-rich | `libero_goal:0` | Background texture | Appearance invariance | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E129 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E130 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E131 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E132 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E133 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E134 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E135 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E136 | OOD | Articulated/contact-rich | `libero_goal:0` | Language instruction | Semantic grounding | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E137 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E138 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E139 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E140 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E141 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E142 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E143 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E144 | OOD | Multi-stage/sequential | `libero_10:2` | Object layout | Trajectory adaptation | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E145 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E146 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E147 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E148 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E149 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E150 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E151 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E152 | OOD | Multi-stage/sequential | `libero_10:2` | Robot initial state | Trajectory adaptation | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E153 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E154 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E155 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E156 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E157 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E158 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E159 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E160 | OOD | Multi-stage/sequential | `libero_10:2` | Camera viewpoint | Perceptual localization | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E161 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E162 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E163 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E164 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E165 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E166 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E167 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E168 | OOD | Multi-stage/sequential | `libero_10:2` | Sensor noise | Perceptual localization | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E169 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E170 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E171 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E172 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E173 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E174 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E175 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E176 | OOD | Multi-stage/sequential | `libero_10:2` | Lighting | Appearance invariance | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E177 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E178 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E179 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E180 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E181 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E182 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E183 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E184 | OOD | Multi-stage/sequential | `libero_10:2` | Background texture | Appearance invariance | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E185 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | Naive async | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E186 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | Naive async | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E187 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | Naive async | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E188 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | Naive async | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E189 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | RTC | Native | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E190 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | RTC | Native | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E191 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | RTC | Native + d* | 0 | Resolved LIBERO-Plus variant (freeze before outcomes) |
| E192 | OOD | Multi-stage/sequential | `libero_10:2` | Language instruction | Semantic grounding | RTC | Native + d* | 1 | Resolved LIBERO-Plus variant (freeze before outcomes) |

### 7A.3 Canonical display terms for all generated outputs
Every plot/table generator should map machine keys to the following display labels:

| Machine key | Display label |
|---|---|
| `single_stage_transport` | **Single-stage transport** |
| `articulated_contact_rich` | **Articulated/contact-rich** |
| `multi_stage_sequential` | **Multi-stage/sequential** |
| `trajectory_adaptation` | **Trajectory adaptation** |
| `perceptual_localization` | **Perceptual localization** |
| `appearance_invariance` | **Appearance invariance** |
| `semantic_grounding` | **Semantic grounding** |
| `object_layout` | **Object layout** |
| `robot_initial_state` | **Robot initial state** |
| `camera_viewpoint` | **Camera viewpoint** |
| `sensor_noise` | **Sensor noise** |
| `light_conditions` | **Lighting** |
| `background_textures` | **Background texture** |
| `language_instructions` | **Language instruction** |
| `naive_async` | **Naive async** |
| `rtc` | **RTC** |
| `low` | **Native** |
| `high` | **Native + d*** |

## 8. Required run manifest

Create one row per episode in:

```text
stage1_manifest.csv
```

Required columns:

```text
run_id
git_sha
model_revision
task_key
suite
base_task_id
base_task_name
task_group

scene_condition              # id | ood
perturbation_key             # id | object_layout | ...
official_category            # ID | official LIBERO-Plus category
mechanism_group              # id | one of the four internal groups
classification_id            # null for ID
api_task_index               # standard task id for ID; resolved plus index for OOD
variant_name                 # exact task/environment name

execution_method             # naive_async | rtc
delay_condition              # low | high
added_delay_ms
seed
n_action_steps

output_path
status                       # pending | running | complete | invalid
invalid_reason
```

### Run ID format

Use:

```text
{task_key}__{scene_condition}__{perturbation_key}__{execution_method}__{delay_condition}__s{seed}
```

Example:

```text
goal_drawer__ood__camera_viewpoint__rtc__high__s1
```

---

## 9. Required episode-level observations

Create:

```text
stage1_episode_results.csv
```

with one row per completed episode.

### Identity columns

```text
run_id
task_key
suite
base_task_id
task_group
scene_condition
perturbation_key
official_category
mechanism_group
variant_name
classification_id
api_task_index
execution_method
delay_condition
added_delay_ms
seed
```

### Outcome columns

```text
success                       # 0/1
episode_steps
completion_fraction           # if available; otherwise null
failure_mode                  # taxonomy below
failure_notes                 # short factual note
```

### Latency / freshness columns

```text
request_latency_mean_ms
request_latency_p50_ms
request_latency_p95_ms

action_age_mean_ms
action_age_p50_ms
action_age_p95_ms
action_age_max_ms

logical_delay_steps_mean
logical_delay_steps_p95
```

### Queue / execution columns

```text
queue_occupancy_mean
queue_occupancy_p95
underrun_count
hold_count
discard_count
num_policy_requests
```

Keep `hold_count` and `underrun_count` separate. Do not count intentional blocking/hold semantics as queue underruns.

### Action-continuity columns

```text
action_delta_mean
action_accel_mean
action_jerk_mean
```

If these are vector-valued internally, aggregate using the same norm convention across every episode and document the norm once.

### Compute columns

```text
wall_clock_episode_s
gpu_id
gpu_peak_memory_mb
```

---

## 10. Failure-mode taxonomy

Use a small fixed taxonomy. Do not invent a new label for every episode.

```text
success
perception_localization
approach_alignment
grasp_failure
contact_execution
trajectory_recovery
wrong_subgoal_or_semantics
sequential_error_accumulation
timeout
other
```

### Annotation rule

`failure_mode` is descriptive secondary analysis, not the primary outcome.

If failure cannot be assigned confidently:

```text
failure_mode = other
```

and add a short factual `failure_notes`.

Do not infer internal model reasoning from the video.

---

## 11. Primary Stage 1 statistic

For each task × perturbation × execution method, compute success rate in four cells:

```text
ID, low
ID, high
OOD, low
OOD, high
```

Define:

```text
I = [S(OOD, high) - S(OOD, low)]
    - [S(ID, high) - S(ID, low)]
```

Call `I`:

```text
OOD × delay interaction
```

### Interpretation

```text
I < 0
```

means the OOD perturbation makes the policy **less tolerant to delay** than the corresponding ID task.

```text
I ≈ 0
```

means the delay penalty is approximately unchanged by that OOD shift.

```text
I > 0
```

means delay is less damaging under that OOD condition; treat this cautiously, especially with two seeds.

### Stage 1 wording

Do not say “significant” based on two seeds.

Use:

```text
candidate interaction
exploratory interaction estimate
screening result
candidate amplification of delay sensitivity
```

Do not use:

```text
statistically significant interaction
proves
establishes
```

---

## 12. Tables to generate immediately

Every completed run should feed the following tables automatically.

### Table A — Coverage / completion

One row per task × perturbation.

| task group | task | perturbation | mechanism group | intended episodes | completed | invalid |
|---|---|---|---|---:|---:|---:|

Purpose: detect missing cells before interpretation.

---

### Table B — Four-cell success table

One row per:

```text
task × perturbation × execution method
```

Columns:

| task group | perturbation | mechanism group | method | ID-low | ID-high | OOD-low | OOD-high | `I` |
|---|---|---|---|---:|---:|---:|---:|---:|

This is the **main quick-read Stage 1 table**.

---

### Table C — Perturbation-family summary

Pool descriptively over the three tasks, but retain task-level rows elsewhere.

| perturbation | mechanism group | method | ID delay drop | OOD delay drop | pooled `I` | OOD-low success |
|---|---|---|---:|---:|---:|---:|

Definitions:

```text
ID delay drop  = S(ID, high)  - S(ID, low)
OOD delay drop = S(OOD, high) - S(OOD, low)
pooled I       = OOD delay drop - ID delay drop
```

---

### Table D — Mechanism-group summary

| mechanism group | perturbations included | method | mean/pooled `I` | interpretation |
|---|---|---|---:|---|
| trajectory adaptation | object layout; robot initial state | ... | ... | ... |
| perceptual localization | camera viewpoint; sensor noise | ... | ... | ... |
| appearance invariance | light conditions; background textures | ... | ... | ... |
| semantic grounding | language instructions | ... | ... | ... |

Do not overinterpret the semantic-grounding group: it contains only one perturbation family.

---

### Table E — Task-demand summary

| task group | method | mean/pooled `I` across perturbations | strongest perturbation | weakest perturbation |
|---|---|---:|---|---|
| single-stage transport | ... | ... | ... | ... |
| articulated/contact-rich | ... | ... | ... | ... |
| multi-stage/sequential | ... | ... | ... | ... |

This table directly addresses whether delay/OOD interaction depends on behavioral demand.

---

### Table F — Method comparison

| task group | perturbation | `I_naive` | `I_rtc` | RTC − naive interaction difference | ranking change? |
|---|---|---:|---:|---:|---|

`ranking change? = yes` if the preferred method under ID/high differs from the preferred method under OOD/high.

---

### Table G — Freshness diagnostics

| task group | perturbation | method | delay | success | mean action age | p95 action age | p95 queue occupancy | underruns |
|---|---|---|---|---:|---:|---:|---:|---:|

Use this as mechanism analysis. It is **not** the headline contribution.

---

## 13. Plots to generate immediately

Generate all plots from the episode-level CSV. Never manually copy numbers.

### Plot 1 — OOD × delay interaction heatmap

**Rows**

```text
3 task-demand groups
```

**Columns**

```text
7 perturbation families
```

**Cell value**

```text
I
```

Create one heatmap for:

```text
naive_async
```

and one for:

```text
rtc
```

This should be the fastest visual for identifying candidate interactions.

---

### Plot 2 — Four-cell interaction plot

For each perturbation family:

- x-axis: `low`, `high`
- y-axis: success rate
- line 1: `ID`
- line 2: `OOD`

Facet by:

```text
task_group × execution_method
```

Interpretation:

> Non-parallel ID and OOD lines indicate a candidate OOD × delay interaction.

---

### Plot 3 — Perturbation-family interaction ranking

For each method, rank the seven perturbations by pooled `I`.

- x-axis: perturbation family
- y-axis: `I`
- horizontal line at `0`

More-negative values indicate stronger candidate amplification of delay sensitivity.

---

### Plot 4 — Mechanism-group interaction summary

Aggregate the perturbation-level estimates into:

```text
trajectory adaptation
perceptual localization
appearance invariance
semantic grounding
```

Plot `I` by mechanism group and execution method.

Label this **exploratory/descriptive**.

---

### Plot 5 — Behavioral-demand interaction summary

- x-axis: task group
- y-axis: `I`
- separate markers/lines: perturbation families
- facet by execution method

This answers:

> Does the same perturbation interact differently with delay depending on task behavioral demand?

---

### Plot 6 — Action age versus outcome

Episode-level:

- x-axis: `action_age_p95_ms`
- y-axis: success/failure
- shape/facet: task group
- facet or annotation: perturbation family

Use only as explanatory evidence for temporal freshness.

---

## 14. Automatic observation sheet

After Stage 1, produce a compact Markdown report with these headings exactly.

```markdown
# Stage 1 Observations

## 1. Coverage
- Completed:
- Invalid:
- Missing:

## 2. Overall OOD × Delay Pattern
- ID-low success:
- ID-high success:
- OOD-low success:
- OOD-high success:
- Overall exploratory interaction I:

## 3. By Perturbation Family
### Object Layout — trajectory adaptation
- OOD-low:
- OOD-high:
- I:
- strongest task group:
- naive vs RTC:
- observation:

### Robot Initial State — trajectory adaptation
...

### Camera Viewpoint — perceptual localization
...

### Sensor Noise — perceptual localization
...

### Light Conditions — appearance invariance
...

### Background Textures — appearance invariance
...

### Language Instructions — semantic grounding
...

## 4. By Behavioral Demand
### Single-stage transport
- strongest candidate interaction:
- weakest candidate interaction:
- naive vs RTC:
- observation:

### Articulated/contact-rich
...

### Multi-stage/sequential
...

## 5. Execution-Method Effects
- conditions where RTC > naive:
- conditions where naive > RTC:
- ranking reversals:
- candidate method × OOD × delay effects:

## 6. Temporal-Freshness Diagnostics
- action-age pattern:
- queue pattern:
- underrun/hold pattern:
- relationship to failure:

## 7. Candidate Confirmatory Effects
- candidate 1:
- candidate 2:
- candidate 3:

## 8. Null / Counterintuitive Results
- perturbations with little interaction:
- positive I values:
- task groups that contradict expectation:

## 9. Data-Quality Warnings
- floor effects:
- ceiling effects:
- invalid episodes:
- latency drift:
- simulator anomalies:
```

---

## 15. Predefined rule for choosing confirmatory conditions

This rule must be frozen **before Stage 1 results are examined**.

### Eligibility

A perturbation family is eligible for confirmation only if, pooled over the three task groups and both methods:

```text
OOD-low success >= 25%
```

This prevents selecting a perturbation that already fails almost completely without added delay.

Also require:

```text
ID-low success >= 50%
```

for the relevant task/method subset used to support the claim.

### Ranking

Among eligible perturbation families:

1. rank by pooled `I`, from most negative to most positive;
2. select the **two most-negative perturbation families** as the primary confirmatory candidates;
3. if a third family has a qualitatively different mechanism group and comparable `I`, retain it as an optional third candidate.

### Behavioral-demand follow-up

For each selected perturbation family, identify the task-demand group with the most negative task-level `I`.

This determines which task × perturbation combinations receive additional seeds.

### Important

The confirmation stage uses **new seeds**.

Do not simply count the original two Stage 1 seeds as if the hypothesis had been specified before seeing them. Report Stage 1 as exploratory and the additional seeds as confirmatory.

---

## 16. What counts as an interesting Stage 1 result

### Strong candidate result

Any of the following is potentially publishable if it replicates:

1. **Static OOD robustness does not predict delayed OOD robustness.**
2. A perturbation with modest native-latency degradation causes a much larger degradation under delay.
3. The OOD × delay interaction differs systematically by perturbation mechanism.
4. The same perturbation interacts differently with delay across behavioral-demand groups.
5. RTC and naive async change ranking under OOD + delay.
6. An execution method that looks robust on ID tasks does not remain robust under particular OOD shifts.

### Weak result

This alone is insufficient:

> “OOD hurts, delay hurts, and OOD plus delay hurts more.”

The paper needs a nontrivial interaction, taxonomy-dependent pattern, method-ranking effect, or failure of static robustness to predict delayed robustness.

---

## 17. Paper verbiage

### Experimental design

Use:

> “We conduct a broad exploratory screen across all seven LIBERO-Plus perturbation families. To separate the source of distribution shift from the behavioral demands of the underlying manipulation problem, we analyze perturbations along two axes: the official LIBERO-Plus perturbation dimension and an internal mechanism-oriented grouping, while stratifying base tasks into single-stage transport, articulated/contact-rich, and multi-stage sequential manipulation.”

### Main scientific question

Use:

> “Which kinds of distribution shift reduce a VLA policy’s tolerance to inference delay, and under which behavioral demands?”

### Interaction framing

Use:

> “We test whether distribution shift changes the marginal effect of inference delay, rather than merely measuring the independent degradation caused by OOD inputs and latency.”

### Stage 1 status

Use:

> “Stage 1 is a low-budget exploratory sweep used to identify candidate interactions. We report the complete sweep, including null results, and evaluate selected candidate effects on additional held-out seeds.”

### Avoid

Do not write:

```text
We tried all perturbations and selected the interesting ones.
```

Do write:

```text
We used a predefined exploratory-to-confirmatory protocol:
a broad low-budget screen followed by higher-replication evaluation of
candidate interactions selected using a frozen criterion.
```

---

## 18. Minimum artifact checklist before Stage 1 is considered complete

Required files:

```text
stage1_resolved_variants.csv
stage1_manifest.csv
stage1_episode_results.csv

stage1_table_coverage.csv
stage1_table_four_cell.csv
stage1_table_perturbation_summary.csv
stage1_table_mechanism_summary.csv
stage1_table_task_group_summary.csv
stage1_table_method_comparison.csv
stage1_table_freshness.csv

stage1_heatmap_naive.png
stage1_heatmap_rtc.png
stage1_interaction_four_cell.png
stage1_perturbation_ranking.png
stage1_mechanism_summary.png
stage1_task_group_summary.png
stage1_action_age_outcome.png

STAGE_1_OBSERVATIONS.md
```

Before interpreting any result, assert:

```text
expected total episodes = 192
all 21 OOD variants were frozen before outcome inspection
same two seeds used everywhere
same high-delay d* used everywhere
same policy checkpoint used everywhere
same n_action_steps=10 used everywhere
ID controls shared rather than duplicated
no missing factorial cells
```

---

## 19. Sources and provenance

Primary benchmark/model sources used to define this specification:

1. **Official LIBERO task map**  
   https://raw.githubusercontent.com/Lifelong-Robot-Learning/LIBERO/master/libero/libero/benchmark/libero_suite_task_map.py

2. **Official LIBERO repository**  
   https://github.com/Lifelong-Robot-Learning/LIBERO

3. **Official LIBERO-Plus repository**  
   https://github.com/sylvestf/LIBERO-plus

4. **Official LIBERO-Plus task classification**  
   https://raw.githubusercontent.com/sylvestf/LIBERO-plus/refs/heads/main/libero/libero/benchmark/task_classification.json

5. **Official LIBERO-Plus task map**  
   https://raw.githubusercontent.com/sylvestf/LIBERO-plus/refs/heads/main/libero/libero/benchmark/libero_suite_task_map.py

6. **LeRobot LIBERO documentation / π0.5 reproduction protocol**  
   https://huggingface.co/docs/lerobot/v0.5.1/libero

7. **π0.5 LIBERO fine-tuned checkpoint training configuration**  
   https://huggingface.co/lerobot/pi05_libero_finetuned/blob/6348c67dbbd696bdf89321c07b107434cbee1baf/train_config.json

### Source-backed facts used here

- Standard LIBERO exposes the three selected base tasks at zero-based indices:
  - `libero_spatial:2`
  - `libero_goal:0`
  - `libero_10:2`
- LIBERO-Plus defines seven perturbation dimensions:
  - Objects Layout
  - Camera Viewpoints
  - Robot Initial States
  - Language Instructions
  - Light Conditions
  - Background Textures
  - Sensor Noise
- LIBERO-Plus provides `task_classification.json` mapping task IDs to perturbation categories and difficulty levels.
- The official LIBERO-Plus benchmark implementation contains thousands of perturbed tasks per suite and retrieves tasks using zero-based `get_task(i)`.
- The LeRobot π0.5 LIBERO checkpoint is trained using `HuggingFaceVLA/libero`, and the documented evaluation uses `n_action_steps=10`.

---

## 20. Frozen Stage 1 design summary

```text
POLICY:
    lerobot/pi05_libero_finetuned

N_ACTION_STEPS:
    10

TASKS:
    libero_spatial:2
        -> single_stage_transport
    libero_goal:0
        -> articulated_contact_rich
    libero_10:2
        -> multi_stage_sequential

PERTURBATIONS:
    Objects Layout
        -> trajectory_adaptation
    Robot Initial States
        -> trajectory_adaptation
    Camera Viewpoints
        -> perceptual_localization
    Sensor Noise
        -> perceptual_localization
    Light Conditions
        -> appearance_invariance
    Background Textures
        -> appearance_invariance
    Language Instructions
        -> semantic_grounding

VARIANT RULE:
    difficulty_level closest to 2
    -> lowest official id as tie-break
    -> freeze before outcomes

METHODS:
    naive_async
    rtc

DELAYS:
    low  = native
    high = native + frozen ID-calibrated d*

SEEDS:
    2 fixed exploratory seeds

OOD EPISODES:
    168

SHARED ID EPISODES:
    24

TOTAL:
    192

PRIMARY STATISTIC:
    I = [S(OOD,high)-S(OOD,low)]
        - [S(ID,high)-S(ID,low)]

PRIMARY INTERPRETATION:
    I < 0 => candidate evidence that OOD reduces delay tolerance

STAGE:
    exploratory
```
