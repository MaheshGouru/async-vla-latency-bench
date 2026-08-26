# Stage 3 New high-power replication — Jupyter workflow

Run notebooks `01` through `05` in order on one idle A100. This workflow is the
fresh, high-replication rerun frozen in
`docs/STAGE_3_NEW_HIGH_POWER_REPLICATION.md`; it does not pool Stage 3 or Stage
3B outcomes into the primary estimates.

Frozen physical matrix:

```text
RTC only
horizons                 = {20,25,30}
added delay              = {0,200} ms
fresh rollout seeds      = {46,...,109} (64 seeds)
shared ID episodes       = 1,152
OOD episodes             = 2,304
total physical episodes  = 3,456
```

The three base-task ID controls are executed once and joined logically to the
six candidate analyses. In particular, the 384 `goal_drawer` ID episodes are
reused across its four OOD candidates without copying episode rows. Sensor
noise remains labeled `posthoc_replication`.

Outputs are durable under `~/stage3_new`; every full runner uses `--resume`.
Notebook 03 uses throwaway seed `999` under `~/stage3_new_smoke` and cannot
touch the frozen seed block. ID and OOD workers must never overlap.

Expected backend entry points (implemented with the benchmark package) are:

```text
make_stage3_new_manifest
resolve_stage3_initializations
run_stage3_new
validate_stage3_new
analyze_stage3_new
```

The final validator must reject missing/duplicate physical rows, seed
replacement, reset-pairing failures, variant drift, and any primary row from
the old Stage 3/3B seed block. Bootstrap analysis must resample complete seed
blocks at least 10,000 times using a recorded RNG seed.
