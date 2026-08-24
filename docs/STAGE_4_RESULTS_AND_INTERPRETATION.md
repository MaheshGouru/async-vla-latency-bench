# Stage 4 — Results and Interpretation

## Status

**COMPLETE**

This document is the post-run record for Stage 4.

The frozen pre-run specification remains unchanged in:

```text
STAGE_4_SECOND_POLICY_OPENVLA_OFT.md
```

Do not modify that file retroactively.

---

## 1. Purpose of this results document

Stage 4 evaluated OpenVLA-OFT as a second-policy external-validity diagnostic using its native/default 8-action chunk under naive asynchronous execution.

After completing the experiment, we recognized that unlike π0.5, OpenVLA-OFT had **not** undergone an ID-only temporal-coverage calibration before the OOD × delay test.

Therefore:

- Stage 4 remains valid as a **native/default-8 diagnostic**.
- Stage 4 should **not** be presented as the final calibrated second-policy comparison.
- Stage 5 is the prospective follow-up that first audits/calibrates OpenVLA-OFT temporal coverage and then conditionally reruns the OOD × delay diagnostic.

---

## 2. Frozen Stage 4 setup

```text
policy_family = OpenVLA-OFT
checkpoint = moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10
execution_method = naive_async_openvla_oft
control_rate_hz = 20
native_chunk_size = 8
configured_action_coverage = 8
request_threshold_actions = 4
delay = Native, Native + 200 ms
seeds = 38..45
libero_episode_index = 0
analysis episodes = 64
```

Tasks:

```text
spatial_transport
long_stove_moka
```

Perturbation:

```text
Objects Layout
```

Exact frozen OOD variants:

```text
spatial_transport:
  classification_id = 1773
  api_task_index = 1772
  variant = pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate_add_15

long_stove_moka:
  classification_id = 1941
  api_task_index = 1940
  variant = KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it_add_25
```

---

## 3. Primary four-cell results

Interaction definition:

```text
I_task =
  [S(OOD,+200)-S(OOD,Native)]
  -
  [S(ID,+200)-S(ID,Native)]
```

Observed results:

| Task | ID Native | ID +200 | OOD Native | OOD +200 | Interaction `I` |
|---|---:|---:|---:|---:|---:|
| `spatial_transport` | 8/8 | 6/8 | 8/8 | 8/8 | +0.250 |
| `long_stove_moka` | 1/8 | 0/8 | 0/8 | 0/8 | +0.125 |

---

## 4. Interpretation

### 4.1 `spatial_transport`

The prior π0.5 null interaction did not become negative under OpenVLA-OFT.

```text
ID:  8/8 -> 6/8
OOD: 8/8 -> 8/8
I = +0.250
```

This is not evidence that OOD is beneficial. It indicates that the added-delay penalty was larger in ID than in the frozen OOD layout for this particular second-policy diagnostic.

### 4.2 `long_stove_moka`

OpenVLA-OFT was near floor even at Native latency.

```text
ID Native = 1/8
OOD Native = 0/8
```

Therefore the Stage 4 interaction is not a meaningful test of whether OOD amplifies delay on this task. The policy lacks enough baseline performance to provide interaction headroom.

This is a **floor-effect limitation**, not evidence that OOD reduces latency sensitivity.

---

## 5. Temporal-coverage finding

Stage 4 also exposed a strong mismatch between OpenVLA-OFT's native 8-action chunk and the logical asynchronous delay regime.

Observed request latency was approximately:

```text
Native request latency ≈ 118–124 ms
```

At 20 Hz:

```text
1 control step = 50 ms
```

so native request latency already consumes roughly 2–3 control steps. With +200 ms added delay, the response delay occupies most of the 8-action temporal coverage.

Substantial queue underruns / hold actions were observed at +200 ms, especially on the longer task.

This is consistent with the broader paper result from Stage 2:

> latency robustness depends strongly on temporal action coverage relative to inference delay.

However, Stage 4 alone cannot establish that 8 is the correct OpenVLA-OFT operating point because no OpenVLA-specific coverage calibration preceded it.

---

## 6. Why Stage 5 is required

π0.5 received explicit ID-only temporal-coverage calibration before the main OOD analysis.

OpenVLA-OFT did not.

The correct prospective follow-up is therefore:

```text
Stage 5A:
  verify whether OpenVLA-OFT single-inference action coverage is tunable
  calibrate temporal coverage on ID only if legitimate

Stage 5B:
  if Stage 5A yields a legitimate calibrated operating point,
  rerun the frozen two-task Objects-Layout × Native/+200 ms diagnostic
  using fresh seeds
```

Do not choose coverage after inspecting OOD outcomes.

Do not fabricate longer chunks by repeating, stretching, or concatenating actions if the model cannot natively produce them.

---

## 7. Paper-facing status

Until Stage 5 is complete, Stage 4 should be described as:

> **a preliminary second-policy diagnostic at OpenVLA-OFT's native/default 8-action coverage**

and not as:

> a calibrated policy-to-policy comparison.

The strongest Stage 4-supported conclusion is:

> OpenVLA-OFT did not reproduce the localized negative π0.5 interaction in the tested diagnostic subset, but interpretation is limited by uncalibrated 8-action temporal coverage and a severe floor effect on the stove–moka task.

