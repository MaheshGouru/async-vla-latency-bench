# Multi-Stage Task Generalization Jupyter workflow

Run notebooks `01` through `05` in order on one idle A100. Every stage fails
closed unless the completed Object-Layout Generalization gate explicitly authorizes Multi-Stage Task Generalization
B. Outputs are isolated under `~/experiment_b` and `~/experiment_b_smoke`.

Notebook 04 runs 16 ID episodes first, then 48 OOD episodes. All workers use
`--resume`; never run the ID and OOD workers concurrently.
