# Async VLA Benchmark: Days 1–3

This isolated package implements the π0.5–LIBERO latency benchmark specified in
`docs/DAYS_1_3_SPEC.md`. It does not train a policy or implement deferred methods.

The current development host lacks LeRobot, LIBERO, and CUDA. Pure simulator code and
dry-run planning can be tested here; real evaluation deliberately fails until exact
repository, checkpoint, and dataset revisions are pinned in a Linux CUDA/EGL environment.

```bash
PYTHONPATH=. python async_vla_benchmark/scripts/run_benchmark.py \
  --config async_vla_benchmark/configs/days1_3.yaml --experiment core --dry-run
```
