# Initialization-State Audit Jupyter workflow

Run notebooks in order on the same single-GPU environment used for earlier primary-policy stages:

1. `01_setup_and_preflight.ipynb`
2. `02_reset_only_initialization_audit.ipynb`
3. `03_validate_and_export.ipynb`

Initialization-State Audit performs 144 resets and **no policy inference or rollout**. Notebook 02
has separate ID and OOD cells. Each cell replaces only its own scene shard, so it
is safe to rerun after interruption. Do not proceed to Held-Out OOD–Delay Horizon Confirmation unless notebook 03
writes a passing 48-row `stage3c_validated_initializations.csv`.
