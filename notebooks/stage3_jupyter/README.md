# Held-Out OOD–Delay Horizon Confirmation A100 Jupyter workflow

Run notebooks `01` through `05` in order. Held-Out OOD–Delay Horizon Confirmation is RTC-only and uses one
physical A100 serially. ID and OOD processes must never overlap.

Frozen matrix: horizons `{20,25,30}`, delays `{Native,+200 ms}`, seeds
`{14..21}`, 96 shared ID episodes and 192 OOD episodes. The 48 sensor-noise
episodes remain labeled post-hoc replication. Confirmatory Horizon–Delay Operating Envelope results do not select or
change any Held-Out OOD–Delay Horizon Confirmation condition.

The workflow reuses the Exploratory OOD–Delay Screening environments, `~/LIBERO-plus`, and
`~/stage1-native`. Outputs are written durably under `~/stage3`; every runner
uses `--resume`. Notebook 03 uses throwaway seed `999` and writes only to
`~/stage3_smoke`; it does not touch the confirmatory output directory or seeds.
Resume skips only artifacts that parse as a valid JSON/Parquet triplet.

Notebooks 01–03 persist these provenance gates under `~/stage3`, so notebook 05
includes them in the final archive:

- `stage3_preflight_environment.json`
- `stage3_initialization_pairing_audit.csv`
- `stage3_smoke_validation.json`
