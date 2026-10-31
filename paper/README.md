# When Delay Meets Distribution Shift: Evaluating Asynchronous Vision-Language-Action Policies

This paper was accepted to the NeurIPS 2026 RoboPAD workshop. See the
[workshop listing](https://neurips.cc/virtual/2026/loc/paris/162917).

## Paper package

This directory contains the current paper source, figures, and compiled PDF for
the asynchronous VLA delay/distribution-shift study.

## Reproducibility snapshot

The final high-power replication used:

- the frozen \(\pi_{0.5}\) checkpoint and RTC execution;
- 64 fresh rollout seeds (`46..109`) per cell;
- configured action coverage \(h \in \{20,25,30\}\);
- Native and Native +200 ms logical delay;
- six frozen OOD task--perturbation candidates;
- 3,456 valid episode rows.

The high-power follow-up does not show a universal OOD amplification of delay.
The interaction is task- and horizon-dependent, while temporal action coverage
and action freshness provide the clearest mechanism-level explanation. The
initialization audit found that the requested LIBERO-Plus initialization
indices resolve to one effective reset state, so seeds represent stochastic
rollouts rather than independent initializations.

The large episode archive is intentionally excluded from Git. See
`docs/STAGE3_NEW_RESULTS_README.md` for the archive layout and analysis
commands.

## Build the paper

From this directory:

```bash
latexmk -pdf -interaction=nonstopmode neurips_2026_latest.tex
```

The source uses the figures stored alongside it. The generated PDF is
`neurips_2026_latest.pdf`.

## Analysis utilities

The committed analysis utilities are:

```bash
python -m async_vla_benchmark.scripts.analyze_stage3_new_mechanisms \
  --results DataArchive/stage3_new_64_seeds/stage3_new/stage3_new_episode_results.csv \
  --output-dir DataArchive/stage3_new_64_seeds/analysis

python -m async_vla_benchmark.scripts.prepare_cvpr_followups \
  --output-dir DataArchive/stage3_new_64_seeds/followup_protocols
```

The second command creates planning manifests only; it does not claim that the
optional second-policy, controller-ablation, or broader-sweep experiments have
been run.
