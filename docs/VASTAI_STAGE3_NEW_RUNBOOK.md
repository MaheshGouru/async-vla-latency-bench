# Vast.ai runbook for Stage 3 New

This runbook launches the frozen 64-seed Stage 3 New replication on one exact
`NVIDIA A100-SXM4-40GB`. Do not use an interruptible instance or mix GPU models.

## Vast.ai instance selection

Select one on-demand offer with:

- exactly one `A100 SXM4` with 40 GB VRAM;
- a verified host and high reliability;
- at least 200 GB of disk;
- a current CUDA/PyTorch Linux image;
- direct SSH access;
- enough prepaid balance for 40 hours plus setup time.

The setup and run scripts fail closed if `nvidia-smi` does not report exactly
`NVIDIA A100-SXM4-40GB` with approximately 40 GB VRAM.

## Connect and install

Copy the SSH command from the Vast.ai instance page, connect, and run:

```bash
cd /workspace
git clone --branch stage3-new-64-seeds \
  https://github.com/MaheshGouru/async-vla-latency-bench.git
cd async-vla-latency-bench
export HF_TOKEN='YOUR_READ_ONLY_HUGGING_FACE_TOKEN'
bash setup_vastai.sh 2>&1 | tee /workspace/setup_vastai.log
```

Do not put the token in a notebook, Git commit, or saved shell script.

## Launch in tmux

After setup succeeds:

```bash
tmux new -s stage3new
cd /workspace/async-vla-latency-bench
export HF_TOKEN='YOUR_READ_ONLY_HUGGING_FACE_TOKEN'
bash run_stage3_new.sh 2>&1 | tee -a /workspace/stage3_new/run.log
```

Detach with `Ctrl-b`, then `d`. The run continues after the SSH connection is
closed. Reattach with:

```bash
tmux attach -t stage3new
```

## Monitoring

```bash
tail -f /workspace/stage3_new/run.log
cat /workspace/stage3_new/heartbeat.txt
find /workspace/stage3_new/episodes -name '*.json' | wc -l
nvidia-smi
```

The runner writes every episode immediately and uses deterministic `--resume`.
If the process exits, inspect the final log lines and rerun the identical launch
command. Completed valid artifacts are skipped.

## Completion

Do not interpret results until the full validator and 10,000-replicate clustered
bootstrap finish. The expected final physical counts are:

```text
ID  = 1,152
OOD = 2,304
all = 3,456
```

The final archive is `/workspace/stage3_new_results.tar.gz`. Download or verify
the private Hugging Face upload before destroying the instance. Stopping or
destroying the instance in the Vast.ai console is required to end GPU billing.
