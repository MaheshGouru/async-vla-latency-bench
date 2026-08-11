I tho# Running Stage 0 on a JupyterLab A100

Modal is only a delivery mechanism. The benchmark is a plain Python module, so
any machine with an A100, a Python 3.10+ interpreter, and headless GL can run it.
This file translates `Dockerfile.modal` into steps for a JupyterLab box.

Everything below assumes a **terminal** inside JupyterLab (File -> New ->
Terminal), not a notebook cell. See section 5 for why that matters.

---

## 1. Check the box first

```bash
nvidia-smi                       # expect an A100; note the memory
python3 --version                # need >= 3.10 (the Modal image uses 3.12)
df -h ~                          # need ~30 GB free: checkpoint + LIBERO assets + outputs
python3 -c "import ctypes; ctypes.CDLL('libEGL.so.1')" && echo "EGL ok"
```

If the EGL check fails and you have `sudo`:

```bash
sudo apt-get update && sudo apt-get install -y \
    libgl1-mesa-glx libgl1-mesa-dev libegl1-mesa-dev libglew-dev \
    libosmesa6-dev libglib2.0-0 patchelf
```

If you do **not** have `sudo` and EGL is missing, fall back to software
rendering in section 3 (`MUJOCO_GL=osmesa`). It works but is markedly slower,
which changes the runtime estimates in section 6.

---

## 2. Environment

Use a fresh virtualenv. This is not optional hygiene: `hf-libero` (what LeRobot's
`[libero]` extra installs) and the LIBERO-Plus fork both claim the top-level
`libero` package and cannot coexist (K007). A shared or pre-existing Algoverse
environment may already have one of them.

```bash
cd ~/async-vla-latency-bench          # wherever you clone this repo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
```

Install LeRobot at the **pinned** commit — the same SHA the Modal image uses.
Inference latency is the independent variable here, so an unpinned LeRobot can
move `d*` between runs:

```bash
LEROBOT_COMMIT=2aba372b4e217cc47db28e0f836859b20d1456c9
python -m pip install \
    "lerobot[pi,libero] @ git+https://github.com/huggingface/lerobot.git@${LEROBOT_COMMIT}"
python -m pip install -e .
```

Do not install `libero` or `robosuite` from their raw GitHub repos — see the
comment block in `Dockerfile.modal` for why.

### Pre-create the LIBERO config

`libero.libero.__init__` calls `input()` the first time it runs if
`~/.libero/config.yaml` is absent. In a terminal that prompts you; under
`nohup` it hangs forever. Create it up front:

```bash
python -c "
import libero, os, yaml
root = os.path.join(os.path.dirname(libero.__file__), 'libero')
cfg = {
    'benchmark_root': root,
    'bddl_files': os.path.join(root, 'bddl_files'),
    'init_states': os.path.join(root, 'init_files'),
    'datasets': os.path.join(root, '../datasets'),
    'assets': os.path.join(root, 'assets'),
}
os.makedirs(os.path.expanduser('~/.libero'), exist_ok=True)
yaml.dump(cfg, open(os.path.expanduser('~/.libero/config.yaml'), 'w'))
"
```

---

## 3. Environment variables

```bash
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export HF_TOKEN=<your HuggingFace token>       # replaces the Modal `hf-token` secret
```

Without EGL, substitute `MUJOCO_GL=osmesa` and `PYOPENGL_PLATFORM=osmesa`.

Put these in the same shell you launch the run from. `nohup` inherits the
environment at launch, so exporting them afterwards has no effect on a running
job.

---

## 4. Preflight

Never launch the full sweep before this passes. It asserts the resolved task
names, the control frequency, `n_action_steps`, the chunk-size invariant the
delay grid depends on, and that RTC is actually enabled on the policy:

```bash
python -m async_vla_benchmark.scripts.run_stage0 \
    --config async_vla_benchmark/configs/stage0.yaml \
    --output-dir outputs/stage0 \
    --preflight-only
```

The first run downloads the pi05 checkpoint and ~586 LIBERO asset files, so
allow several minutes before any output appears.

Then confirm the manifest is the grid you expect:

```bash
python -m async_vla_benchmark.scripts.run_stage0 \
    --config async_vla_benchmark/configs/stage0.yaml \
    --output-dir outputs/stage0 \
    --dry-run
```

---

## 5. Launch the run detached

**Do not run this in a notebook cell.** A multi-hour job in a cell dies when the
browser disconnects, the kernel restarts, or the JupyterLab session is recycled —
and you lose the GPU-hours, not just the output. Use `nohup` (or `tmux` if the
box has it):

```bash
nohup python -m async_vla_benchmark.scripts.run_stage0 \
    --config async_vla_benchmark/configs/stage0.yaml \
    --output-dir outputs/stage0 \
    --resume \
    > outputs/stage0_run.log 2>&1 &

echo $! > outputs/stage0.pid
```

Watch it:

```bash
tail -f outputs/stage0_run.log
grep -c '^completed' outputs/stage0_run.log     # episodes finished so far
```

`--resume` skips episodes already present in the results CSV, so a killed run
restarts with the same command and loses at most one episode. Keep using it.

---

## 6. What to expect

Anchored on the Modal A100-40GB run: ~112 s/episode wall clock, dominated by
MuJoCo stepping and rendering two 224x224 camera views rather than by inference.

| grid | episodes | wall clock |
|---|---:|---|
| 5 delays (0-400) x 6 seeds | 180 | ~4 h 45 m - 5 h 35 m |
| 8 delays (0-700) x 6 seeds | 288 | ~7 h 35 m - 8 h 50 m |

Add roughly 40% if you are on `osmesa` instead of EGL.

Check whether the Algoverse allocation has a session or job wall-clock limit
shorter than that. If it does, run in blocks and rely on `--resume`; episode
order is task -> method -> delay -> seed, so a partial run always completes whole
task x method cells first, which is what viability is computed over.

---

## 7. After the run

```bash
python -m async_vla_benchmark.scripts.validate_results --output-dir outputs/stage0
python -m async_vla_benchmark.scripts.select_high_delay \
    --results outputs/stage0/latency_calibration_episode_results.csv
```

`select_high_delay` writes `selected_high_delay.json`, which Stage 1 reads rather
than choosing its own delay.

---

## 8. Differences from the Modal path

| | Modal | JupyterLab |
|---|---|---|
| environment | rebuilt from `Dockerfile.modal` every deploy | built once by hand; drifts unless you rebuild the venv |
| outputs | persistent Volume at `/data/outputs` | ordinary directory — **back it up yourself** |
| secret | `modal.Secret.from_name("hf-token")` | `HF_TOKEN` env var |
| timeout | hard 10 h function cap | whatever the allocation enforces |
| pinning | `LEROBOT_COMMIT` baked into the image | pinned only by the `pip install` above |

The last row is the one that bites. On Modal the pin is enforced by the image;
here it is enforced only by whoever typed the install command. If the venv is
ever rebuilt without the SHA, measured inference latency can shift and `d*` with
it. Record `pip freeze > outputs/stage0_pip_freeze.txt` alongside the results so
the environment is recoverable.
