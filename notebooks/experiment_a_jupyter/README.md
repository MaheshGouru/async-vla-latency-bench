# Experiment A Jupyter workflow

Run `01` through `05` in order on one idle A100. Experiment A uses a distinct
output directory (`~/experiment_a`) and never modifies completed Stage 0–3C
artifacts. Notebook 04 launches ID first and refuses to launch OOD until all 16 ID
episodes are complete and the GPU is idle. All workers use `--resume`.
