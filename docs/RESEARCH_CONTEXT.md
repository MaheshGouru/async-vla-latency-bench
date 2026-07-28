
# Research Context

## Research goal

We are studying asynchronous buffering for Vision-Language-Action policies
without physical robot hardware.

The initial target is a workshop paper studying how model inference latency
translates into behavioral latency, action staleness, queue underruns, and task
failure.

## Final Week 1 question

For a frozen π0.5-LIBERO policy, compare:

1. Ideal synchronous execution
2. Blocking synchronous execution
3. Naive asynchronous action replacement
4. Real-Time Chunking
5. Fixed execution horizons

Measure:

- native model latency;
- end-to-end request latency;
- action age;
- task success;
- completion time;
- queue depth and underruns;
- action continuity;
- sensitivity to execution horizon.

## Why this study comes first

Before implementing a new algorithm, we need to determine whether:

- asynchronous strategies produce meaningfully different behavior;
- action age differs from raw inference latency;
- RTC improves continuity, success, or both;
- fixed execution horizon materially changes performance;
- there is a sufficient empirical gap to justify adding VLASH and FASTER.

## Model and benchmark

Primary checkpoint:

`lerobot/pi05_libero_finetuned`

Environment:

LIBERO through LeRobot.

Initial task suites:

- LIBERO-Spatial
- LIBERO-Goal
- LIBERO-10

The dataset reference is:

`HuggingFaceVLA/libero`

No policy training or fine-tuning is required in Days 1–3.

## Important conceptual distinctions

Model inference latency:
Time needed for one policy request.

Logical inference delay:
Number of control steps before a generated chunk becomes available.

Action age:
Time between capturing the source observation and executing an action generated
from that observation.

Reaction latency:
Time between a scene change and execution of an action conditioned on a
post-change observation.

RTC primarily addresses asynchronous chunk compatibility. It should not
automatically be interpreted as reducing raw policy-forward latency.

## Ideas considered but not pursued yet

Semantic slack:
Rejected as the initial contribution because it closely overlaps adaptive
execution-horizon and event-triggered control literature.

Joint adaptive compute and execution horizon:
Potential later project, but too broad before establishing the baseline
phenomenon.

OOD and dynamic perturbations:
Deferred until the standard asynchronous execution harness is validated.

VLASH and FASTER:
Required candidates for a later complete-paper benchmark, but excluded from the
Days 1–3 critical path.

## Current scope boundary

Implement only what is specified in `docs/DAYS_1_3_SPEC.md`.

Do not broaden the task without first documenting why the existing specification
cannot be executed.