# Stage 4 — OpenVLA-OFT second-policy diagnostic

Run notebooks `01` through `05` in order on one physical NVIDIA A100. Stage 4
is the frozen 64-episode OpenVLA-OFT diagnostic in
`docs/STAGE_4_SECOND_POLICY_OPENVLA_OFT.md`; it is naive asynchronous execution,
not RTC.

The setup notebook creates a separate Python 3.10 environment because the pinned
official OpenVLA-OFT stack uses PyTorch 2.2 and its custom Transformers 4.40.1
fork. Set the global `GPU` variable to an idle physical A100 in notebooks 01, 03,
and 04. Run ID and OOD serially; never launch both shards together.

1. `01_setup_and_policy_preflight.ipynb`
2. `02_freeze_manifest_and_pairing.ipynb`
3. `03_seed999_smoke.ipynb`
4. `04_full_serial_run.ipynb`
5. `05_validate_analyze_export.ipynb`

Do not change the tasks, variants, 8-action coverage, request threshold 4,
Native/+200-ms delays, initialization index 0, or seeds 38–45 after outcomes are
observed.
