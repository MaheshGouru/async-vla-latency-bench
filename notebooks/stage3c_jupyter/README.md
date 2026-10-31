# Stage 3C Jupyter workflow

Run notebooks in order on the same single-GPU environment used for Stages 1–3B:

1. `01_setup_and_preflight.ipynb`
2. `02_reset_only_initialization_audit.ipynb`
3. `03_validate_and_export.ipynb`

Stage 3C performs 144 resets and **no policy inference or rollout**. Notebook 02
has separate ID and OOD cells. Each cell replaces only its own scene shard, so it
is safe to rerun after interruption. Do not proceed to Stage 3D unless notebook 03
writes a passing 48-row `stage3c_validated_initializations.csv`.
