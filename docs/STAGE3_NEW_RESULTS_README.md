# High-Power OOD–Delay Replication results archive

The complete 64-seed run is stored at:

```text
DataArchive/stage3_new_64_seeds/
```

It contains the original `stage3_new_results.tar.gz` and its extracted
`stage3_new/` directory. The episode CSV contains 3,456 valid physical rows:

```text
64 seeds (46..109)
RTC only
horizons = 20, 25, 30
added delay = 0, 200 ms
shared ID controls + six frozen OOD candidates
```

Run the mechanism analysis with:

```bash
# The analysis environment needs pandas (and pyarrow if you extend it to Parquet).
python -m pip install pandas
python -m async_vla_benchmark.scripts.analyze_stage3_new_mechanisms \
  --results DataArchive/stage3_new_64_seeds/stage3_new/stage3_new_episode_results.csv \
  --output-dir DataArchive/stage3_new_64_seeds/analysis
```

Run the follow-up manifest generator with:

```bash
python -m async_vla_benchmark.scripts.prepare_cvpr_followups \
  --output-dir DataArchive/stage3_new_64_seeds/followup_protocols
```

The extracted episode and Parquet files are intentionally ignored by Git;
commit the scripts and documentation, not large run artifacts.
