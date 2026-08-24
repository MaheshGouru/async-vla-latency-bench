# Stage 5 — OpenVLA-OFT temporal-coverage calibration and final second-policy replication

Run notebooks `01` through `05` in order.

1. `01_setup_and_preflight.ipynb` — record provenance.
2. `02_freeze_manifest_and_pairing.ipynb` — run the 5A0 capability audit and build the conditional 5A manifest.
3. `03_stage5a0_capability_audit.ipynb` — inspect the 5A0 gate.
4. `04_full_serial_run.ipynb` — launch any permitted 5A/5B rollouts (empty when the 8-action gate is closed).
5. `05_validate_analyze_export.ipynb` — analyze (produces the selected operating point), build the 5B manifest, validate, and export the final observations.

The standard OpenVLA-OFT LIBERO checkpoint has a fixed 8-action output horizon. If the 5A0 audit confirms this, Stage 4 remains the native-horizon second-policy diagnostic and no additional episodes are required.
