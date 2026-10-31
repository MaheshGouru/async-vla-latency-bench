# When Delay Meets Distribution Shift: Evaluating Asynchronous Vision-Language-Action Policies

**Accepted to the NeurIPS 2026 RoboPAD workshop.** See the [official workshop listing](https://neurips.cc/virtual/2026/loc/paris/162917).

This repository contains the benchmark, experiment runners, analysis code, and
paper artifacts for studying how inference delay, temporal action coverage, and
distribution shift affect asynchronous vision-language-action (VLA) execution.

## Repository contents

- [`paper/`](paper/) — paper source, compiled PDF, figures, and paper-specific README.
- [`async_vla_benchmark/`](async_vla_benchmark/) — benchmark implementation, runners, validators, and analysis scripts.
- [`notebooks/`](notebooks/) — setup, experiment, validation, and figure-generation notebooks.
- [`docs/`](docs/) — experiment protocols, results ledger, reproducibility notes, and runbooks.
- [`DataArchive/`](DataArchive/) — selected tracked benchmark artifacts; the large 64-seed episode archive is intentionally kept outside Git.

## Final primary-policy result

The high-power Stage 3 New replication uses the frozen \(\pi_{0.5}\) checkpoint
with RTC execution, 64 rollout seeds per cell, configured action coverage
\(h \in \{20,25,30\}\), native and +200 ms logical delay, and six frozen OOD
task–perturbation candidates. It contains 3,456 valid episode rows.

The results do not support a universal claim that distribution shift amplifies
delay sensitivity. Effects are task- and horizon-dependent; temporal action
coverage and action freshness provide the clearest mechanism-level explanation.

## Paper and reproducibility

Build the paper from [`paper/`](paper/):

```bash
cd paper
latexmk -pdf -interaction=nonstopmode neurips_2026_latest.tex
```

See [`docs/STAGE3_NEW_RESULTS_README.md`](docs/STAGE3_NEW_RESULTS_README.md) for
the results archive layout and analysis commands, and [`docs/README.md`](docs/README.md)
for the complete experiment documentation index.
