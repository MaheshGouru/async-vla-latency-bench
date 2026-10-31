# Stage 2 A100 Jupyter workflow

Run these notebooks in order. Do not use **Run All** across notebooks.

1. `01_setup_and_preflight.ipynb`
2. `02_audit_semantics_and_freeze_manifest.ipynb`
3. `03_smoke_test.ipynb`
4. `04_full_serial_run.ipynb`
5. `05_validate_analyze_export.ipynb`

Stage 2 is a 360-episode, ID-only, RTC-only local sensitivity sweep. It uses
the same `lerobot/pi05_libero_finetuned` checkpoint and standard LIBERO
environment as Stage 1. It does not use LIBERO-Plus or rerun any Stage 0/1
episode.

The full run uses one detached benchmark process on one A100. The process
executes horizons and episodes serially, writes request/action/episode artifacts
after every episode, and resumes by skipping completed episode JSON files.
Never launch a second Stage 2 worker on the same GPU: concurrency would
contaminate the latency measurements.

Notebook 2 resolves 15 reset-state fingerprints—one per task×seed—and writes the
same identity into all 24 horizon×delay rows in that paired block. Every episode
recomputes the actual reset fingerprint and fails before recording a result if it
does not match the frozen manifest.

The notebooks expect the existing Stage 1 ID environment at
`~/venv-stage1-id`. If it is absent on a fresh machine, run the Stage 1 setup
notebook first. Authenticate both the notebook kernel and that environment with
Hugging Face before the smoke test.

Download the archive created by notebook 5 before a temporary machine shuts
down. Never save JupyterHub or Hugging Face credentials in the repository.
