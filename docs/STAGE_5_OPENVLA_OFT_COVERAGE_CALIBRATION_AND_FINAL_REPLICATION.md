# STATUS — CANCELED BEFORE EXECUTION

**Canceled on 2026-08-26. No OpenVLA-OFT Temporal-Coverage Calibration experiments will be run.**

The protocol below is retained only for provenance. It must not be dispatched.
The active final experiment is:

```text
STAGE_3_NEW_HIGH_POWER_REPLICATION.md
```

Reason: reviewer feedback identified low rollout count in the existing Held-Out OOD–Delay Horizon Confirmation /
Held-Out Object-Layout Cross-Task Replication four-cell interaction estimates as the higher-value limitation to
address. The remaining compute budget is therefore concentrated on a fresh
64-seed replication of the π0.5 Held-Out OOD–Delay Horizon Confirmation and Held-Out Object-Layout Cross-Task Replication matrix.

---

# OpenVLA-OFT Temporal-Coverage Calibration — OpenVLA-OFT Temporal-Coverage Calibration and Final Second-Policy Replication

## 0. Motivation

Cross-Policy OpenVLA-OFT Diagnostic used OpenVLA-OFT's native/default 8-action chunk under naive asynchronous execution. That was a defensible policy-native diagnostic, but unlike π0.5 it was **not preceded by an ID-only temporal-coverage calibration**.

Cross-Policy OpenVLA-OFT Diagnostic therefore remains a valid completed native-stack diagnostic, but it must not be treated as the final calibrated cross-policy experiment until we determine whether OpenVLA-OFT's executable action coverage is actually tunable.

OpenVLA-OFT Temporal-Coverage Calibration has two parts:

```text
OpenVLA-OFT Temporal-Coverage Calibration Phase A = capability audit + ID-only temporal-coverage calibration
OpenVLA-OFT Temporal-Coverage Calibration Phase B = final OOD × delay replication at the frozen OpenVLA-OFT Temporal-Coverage Calibration Phase A operating point, only if a legitimate alternative coverage exists
```

Do not call OpenVLA-OFT Temporal-Coverage Calibration Phase A a search for the "best" chunk length. The goal is to identify a **legitimate, locally stable operating point without using OOD outcomes**.

---

## 1. Policy freeze

Use the same policy provenance as Cross-Policy OpenVLA-OFT Diagnostic:

```text
policy_family = OpenVLA-OFT
checkpoint_id = moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10
checkpoint_revision = 13cdacd486c504e65408fc3c9e12fec9c5bf0382
openvla_oft_repo = moojink/openvla-oft
openvla_oft_commit = e4287e94541f459edc4feabc4e181f537cd569a8
```

No retraining, fine-tuning, chunk concatenation, repeated actions, time-stretching, or RTC-like guidance is allowed.

---

## 2. OpenVLA-OFT Temporal-Coverage Calibration Phase A0 — capability audit before any sweep

Before running calibration rollouts, establish the exact semantics of OpenVLA-OFT's action output.

Record:

```text
model_native_output_horizon
whether returned action tensor contains >8 future actions
whether evaluation-time executed coverage can be set independently of model output horizon
whether values >8 are supported by a single inference without concatenation/re-query
whether values <native_output_horizon are supported by simple prefix execution
```

Save:

```text
stage5_openvla_coverage_capability_audit.json
```

### Gate

If a single inference returns **exactly 8 valid future actions and no legitimate mechanism exposes >8 actions**, then:

```text
maximum_native_coverage = 8
OpenVLA-OFT Temporal-Coverage Calibration Phase A coverage sweep over >8 = NOT ALLOWED
OpenVLA-OFT Temporal-Coverage Calibration Phase B rerun = NOT REQUIRED
```

In that case Cross-Policy OpenVLA-OFT Diagnostic remains the native-horizon second-policy diagnostic, and the paper should state that OpenVLA-OFT's native 8-step horizon is itself a temporal-coverage constraint.

If a single inference legitimately supports multiple executable coverages, continue to OpenVLA-OFT Temporal-Coverage Calibration Phase A1.

---

## 3. OpenVLA-OFT Temporal-Coverage Calibration Phase A1 — ID-only temporal-coverage calibration

### Tasks

Use the same two standard-LIBERO ID tasks as Cross-Policy OpenVLA-OFT Diagnostic:

```text
spatial_transport
  suite = libero_spatial
  task_id = 2
  task = pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate

long_stove_moka
  suite = libero_10
  task_id = 2
  task = KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it
```

**ID only. Do not inspect any LIBERO-Plus OOD outcomes during OpenVLA-OFT Temporal-Coverage Calibration Phase A.**

### Candidate coverages

Construct the candidate set only from values that OpenVLA-OFT Temporal-Coverage Calibration Phase A0 proves are legitimate from **one model inference**.

Preferred candidate set if all are natively supported:

```text
configured_action_coverage ∈ {8,12,16,20,25}
```

If some values are unsupported, remove them **before any OpenVLA-OFT Temporal-Coverage Calibration Phase A success results are inspected** and record why. Never manufacture longer coverage by concatenating multiple predictions.

For each coverage `c`, use the benchmark's same half-coverage request rule unless implementation semantics require a predeclared exception:

```text
request_threshold_actions = ceil(c/2)
```

### Delay and execution

```text
execution_method = naive_async_openvla_oft
control_rate_hz = 20
period_ms = 50
delay = {Native, Native+200ms}
added_delay_ms = {0,200}
```

### Seeds

Use fresh calibration seeds:

```text
SEEDS = [46,47,48,49,50]
libero_episode_index = 0
```

Within each `(task, coverage, seed)`, Native and +200-ms runs must use the same resolved initialization/reset fingerprint.

### Primary calibration diagnostics

For every task × coverage × delay cell report:

```text
successes / 5
queue_underrun_steps
hold_action_fraction
mean/p95 action_age_ms
measured_request_latency_ms
total_logical_delay_steps
realized_coverage_ratio
```

### Operating-point rule

Freeze one coverage **without using OOD outcomes**.

Select the smallest legitimate coverage satisfying all of the following, where possible:

1. no catastrophic ID floor at Native;
2. Native and +200 ms do not show persistent queue starvation;
3. success is locally stable relative to adjacent supported coverage values;
4. increasing coverage further gives no clear robustness gain large enough to justify substantially more stale open-loop execution.

Do not select solely by maximum success. If no coverage satisfies these conditions, declare that no stable OpenVLA-OFT async operating point was found in the supported range.

Save the frozen decision and all candidate outcomes to:

```text
stage5a_coverage_calibration_results.csv
stage5a_selected_operating_point.json
STAGE_5A_OBSERVATIONS.md
```

---

## 4. OpenVLA-OFT Temporal-Coverage Calibration Phase B — final second-policy OOD × delay replication

Run OpenVLA-OFT Temporal-Coverage Calibration Phase B **only if OpenVLA-OFT Temporal-Coverage Calibration Phase A identifies a legitimate coverage different from Cross-Policy OpenVLA-OFT Diagnostic's uncalibrated native-8 setting, or otherwise establishes a calibrated setting that warrants a clean fresh-seed rerun**.

### Frozen tasks and OOD variants

Use exactly the same diagnostic contrast as Cross-Policy OpenVLA-OFT Diagnostic:

```text
spatial_transport
  ID = libero_spatial task 2
  OOD Objects Layout = classification_id 1773
  api_task_index = 1772
  variant = pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15

long_stove_moka
  ID = libero_10 task 2
  OOD Objects Layout = classification_id 1941
  api_task_index = 1940
  variant = KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25
```

Do not substitute Object-Layout Generalization or Multi-Stage Task Generalization layouts.

### Execution

```text
execution_method = naive_async_openvla_oft
configured_action_coverage = <frozen OpenVLA-OFT Temporal-Coverage Calibration Phase A value>
request_threshold_actions = ceil(configured_action_coverage/2)
delay = {Native, Native+200ms}
libero_episode_index = 0
```

### Fresh final seeds

```text
SEEDS = [51,52,53,54,55,56,57,58]
```

Physical analysis episodes:

```text
2 tasks × 2 scenes × 2 delays × 8 seeds = 64
```

Do not reuse Cross-Policy OpenVLA-OFT Diagnostic outcomes as OpenVLA-OFT Temporal-Coverage Calibration Phase B analysis rows.

### Primary interaction

For each task:

```text
I_task =
  [S(OOD,+200)-S(OOD,Native)]
  -
  [S(ID,+200)-S(ID,Native)]
```

Report all four raw `successes/8` cells plus an eight-seed paired-bootstrap 95% interval.

Secondary diagnostics remain request latency, logical delay steps, action age, queue underruns, hold fraction, and realized coverage ratio.

---

## 5. Relationship to completed Cross-Policy OpenVLA-OFT Diagnostic

Cross-Policy OpenVLA-OFT Diagnostic is **not deleted or overwritten**. It is a completed preliminary/native-stack diagnostic at coverage 8.

Observed Cross-Policy OpenVLA-OFT Diagnostic results:

```text
spatial_transport:
  ID Native 8/8
  ID +200  6/8
  OOD Native 8/8
  OOD +200 8/8
  I = +0.250, paired-bootstrap 95% CI [0.000, 0.500]

long_stove_moka:
  ID Native 1/8
  ID +200  0/8
  OOD Native 0/8
  OOD +200 0/8
  I = +0.125, paired-bootstrap 95% CI [0.000, 0.375]
```

The `long_stove_moka` Cross-Policy OpenVLA-OFT Diagnostic interaction is not substantively interpretable because the policy is already at/near floor. Cross-Policy OpenVLA-OFT Diagnostic also showed substantial latency-induced queue starvation at the native 8-action coverage.

OpenVLA-OFT Temporal-Coverage Calibration exists to determine whether that behavior is an unavoidable native-horizon limitation or an artifact of using an uncalibrated executable coverage.

---

## 6. Paper-facing interpretation gate

### If OpenVLA-OFT Temporal-Coverage Calibration Phase A proves maximum native coverage is exactly 8

Do not run an artificial longer-horizon experiment. State:

> OpenVLA-OFT's native action horizon is eight steps in our evaluated checkpoint. Under the 20-Hz asynchronous controller, added latency consumes a large fraction of this temporal coverage, producing substantial queue starvation. We therefore treat the second-policy result as a native-stack operating-envelope diagnostic rather than a coverage-matched comparison to π0.5.

### If OpenVLA-OFT Temporal-Coverage Calibration Phase A finds a stable legitimate coverage and OpenVLA-OFT Temporal-Coverage Calibration Phase B completes

Use OpenVLA-OFT Temporal-Coverage Calibration Phase B as the final calibrated second-policy result and retain Cross-Policy OpenVLA-OFT Diagnostic as preliminary provenance.

### If no stable operating point exists

State that directly. Do not tune on OOD or silently relax +200 ms.

---

## 7. Prohibited adaptations

After OpenVLA-OFT Temporal-Coverage Calibration Phase A ID results are inspected, do not change:

- the candidate-set construction rule;
- the two OpenVLA-OFT Temporal-Coverage Calibration Phase B tasks;
- the exact two OOD variants;
- the +200-ms stress condition;
- OpenVLA-OFT Temporal-Coverage Calibration Phase B seeds `51..58`;
- the interaction definition.

At no point may OOD outcomes influence the OpenVLA-OFT Temporal-Coverage Calibration Phase A coverage choice.
