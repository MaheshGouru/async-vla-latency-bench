# Stage 1 A100 Jupyter workflow

Run these notebooks in order. Do not use **Run All** across notebooks.

1. `01_setup_and_preflight.ipynb`
2. `01a_install_system_dependencies.ipynb`
3. `01b_install_libero_plus_assets.ipynb`
4. `02_freeze_design_and_import.ipynb`
5. `03_smoke_test.ipynb`
6. `04_full_serial_run.ipynb`
7. `05_validate_analyze_export.ipynb`

The default is one A100 and one serial benchmark process. This matches the
Stage 0 latency-measurement practice and avoids cross-GPU latency confounding.
Every long run is detached, resumable, and monitored from per-episode JSON
artifacts rather than an aggregate CSV.

Before notebook 2, place the complete Stage 0 result bundle at `~/stage0`.
Before leaving the temporary machine, download the archive produced by notebook
5 and push all code changes. Do not put JupyterHub or Hugging Face credentials
in this repository.
