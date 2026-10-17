#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${VAST_WORKSPACE:-/workspace}"
VENV_ID="$WORKSPACE/venv-stage1-id"
VENV_OOD="$WORKSPACE/venv-stage1-ood"
REPO="$WORKSPACE/async-vla-latency-bench"
OUT="$WORKSPACE/stage3_new"
MANIFEST=$OUT/stage3_new_manifest.csv
LIBERO_PLUS="$WORKSPACE/LIBERO-plus"
STAGE1_NATIVE="$WORKSPACE/stage1-native"
STAGE1_NATIVE_APT="$WORKSPACE/stage1-native-apt"
XKBCOMP_REDIRECT="$WORKSPACE/xkbcomp_redirect.so"

BENCH_SHA=$(git -C "$REPO" rev-parse HEAD)
LEROBOT_SHA=2aba372b4e217cc47db28e0f836859b20d1456c9
LIBEROPLUS_SHA=4976dc30028e805ff8094b55501d532c48fec182
MODEL_SHA=8e174154ef5f6c60a8da12ae99c303d8963138c1

export CUDA_VISIBLE_DEVICES=0
export MUJOCO_EGL_DEVICE_ID=0
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export MPLBACKEND=Agg
export HF_HOME="$WORKSPACE/huggingface"

mkdir -p "$OUT"

GPU_LINE=$(nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu \
    --format=csv,noheader,nounits)
IFS=',' read -r GPU_NAME GPU_TOTAL GPU_USED GPU_UTIL <<< "$GPU_LINE"
GPU_NAME=$(xargs <<< "$GPU_NAME")
GPU_TOTAL=$(xargs <<< "$GPU_TOTAL")
GPU_USED=$(xargs <<< "$GPU_USED")
GPU_UTIL=$(xargs <<< "$GPU_UTIL")
if [ "$GPU_NAME" != "NVIDIA A100-SXM4-40GB" ]; then
    echo "ERROR: expected NVIDIA A100-SXM4-40GB; found $GPU_NAME"
    exit 1
fi
if [ "$GPU_TOTAL" -lt 40000 ] || [ "$GPU_TOTAL" -gt 42000 ]; then
    echo "ERROR: expected approximately 40 GB VRAM; found ${GPU_TOTAL} MiB"
    exit 1
fi
echo "Verified GPU: $GPU_NAME (${GPU_TOTAL} MiB; used=${GPU_USED}; util=${GPU_UTIL}%)"

echo "Running repository tests before consuming analysis seeds..."
$VENV_ID/bin/python -m pytest -q "$REPO/async_vla_benchmark/tests"

# Heartbeat: a stale-timestamp check (`date -d @$(cat ~/stage3_new/heartbeat.txt)`
# or just comparing mtime to `date`) tells you in seconds whether this run is
# still alive, instead of needing to reattach and watch output for a while --
# useful after the whole underlying server got stopped/restarted mid-run once
# already (idle-culler on this shared JupyterHub instance).
( while true; do date +%s > "$OUT/heartbeat.txt"; sleep 60; done ) &
HEARTBEAT_PID=$!
trap 'kill "$HEARTBEAT_PID" 2>/dev/null || true' EXIT

echo "========================================================"
echo "[1/7] Generating full manifest..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.make_stage3_new_manifest \
    --output "$MANIFEST" \
    --git-sha "$BENCH_SHA" \
    --lerobot-git-sha "$LEROBOT_SHA" \
    --libero-plus-git-sha "$LIBEROPLUS_SHA" \
    --model-revision "$MODEL_SHA"

PAIRING_AUDIT="$OUT/stage3_new_initialization_pairing_audit.csv"
echo "Resolving and repeating all frozen reset identities..."
$VENV_ID/bin/python -m async_vla_benchmark.scripts.resolve_stage3_initializations \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$MANIFEST" --scene id --expected-rows 3456 \
    --expected-cells-per-key 6 --audit-output "$PAIRING_AUDIT"
env PYTHONPATH="$LIBERO_PLUS" \
    $VENV_OOD/bin/python -m async_vla_benchmark.scripts.resolve_stage3_initializations \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$MANIFEST" --scene ood --expected-rows 3456 \
    --expected-cells-per-key 6 --audit-output "$PAIRING_AUDIT"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.validate_stage3_new \
    --manifest "$MANIFEST" --output-dir "$OUT" --allow-incomplete

echo ""
echo "========================================================"
echo "[2/7] Smoke run (18 episodes, seed 999, h=25)..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.make_stage3_new_manifest \
    --output "$OUT/smoke_manifest.csv" \
    --git-sha "$BENCH_SHA" \
    --lerobot-git-sha "$LEROBOT_SHA" \
    --libero-plus-git-sha "$LIBEROPLUS_SHA" \
    --model-revision "$MODEL_SHA" \
    --smoke-seed 999 --smoke-horizon 25

$VENV_ID/bin/python -m async_vla_benchmark.scripts.run_stage3_new \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$OUT/smoke_manifest.csv" \
    --output-dir "$OUT/smoke" --scene id --resume
env PYTHONPATH="$LIBERO_PLUS" \
    $VENV_OOD/bin/python -m async_vla_benchmark.scripts.run_stage3_new \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$OUT/smoke_manifest.csv" \
    --output-dir "$OUT/smoke" --scene ood --resume
$VENV_ID/bin/python -m async_vla_benchmark.scripts.validate_stage3_new \
    --manifest "$OUT/smoke_manifest.csv" --output-dir "$OUT/smoke" --smoke

echo ""
echo "========================================================"
echo "[3/7] Full ID run (1,152 episodes)..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.run_stage3_new \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$MANIFEST" \
    --output-dir "$OUT" --scene id --resume
$VENV_ID/bin/python -m async_vla_benchmark.scripts.validate_stage3_new \
    --manifest "$MANIFEST" --output-dir "$OUT" --require-scene id

echo ""
echo "========================================================"
echo "[4/7] Full OOD run (2,304 episodes; 64 fresh seeds per cell)..."
echo "========================================================"
# On rootless containers, ~/stage1-native is a conda-forge prefix built by
# setup_instance.sh's sudo fallback (see [1/8] there). This box has no EGL
# at all (confirmed: no libEGL, no vendor ICDs, no NVIDIA EGL anywhere on
# the filesystem) -- but it does have a real system GLX/GL stack, so we
# render via GLFW against a virtual X display (Xvfb) instead. Xvfb itself
# was apt-get-download'd (no root needed) into ~/stage1-native-apt, along
# with its transitive deps (libxfont2, libfontenc1, x11-xkb-utils, xkb-data).
if [ -d "$STAGE1_NATIVE" ]; then
    XDG_RUNTIME_DIR_PATH="/tmp/xdg-runtime-$(whoami)"
    mkdir -p "$XDG_RUNTIME_DIR_PATH"
    chmod 700 "$XDG_RUNTIME_DIR_PATH"

    # Xvfb hardcodes exec("/usr/bin/xkbcomp") with no override flag, and
    # /usr/bin isn't writable here -- an LD_PRELOAD shim (xkbcomp_redirect.c)
    # intercepts that execve() and redirects it to our apt-extracted binary.
    if [ ! -e /tmp/.X99-lock ]; then
        LD_LIBRARY_PATH="$STAGE1_NATIVE_APT/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}" \
        LD_PRELOAD="$XKBCOMP_REDIRECT" \
        XKBCOMP_REPLACEMENT="$STAGE1_NATIVE_APT/usr/bin/xkbcomp" \
            "$STAGE1_NATIVE_APT/usr/bin/Xvfb" :99 -screen 0 1280x1024x24 -nolisten tcp &
        sleep 2
    fi

    NATIVE_ENV=(env -u PYOPENGL_PLATFORM
        "PYTHONPATH=$LIBERO_PLUS"
        "LD_LIBRARY_PATH=$STAGE1_NATIVE/lib:${LD_LIBRARY_PATH:-}"
        "PATH=$STAGE1_NATIVE/bin:$PATH"
        "MAGICK_HOME=$STAGE1_NATIVE"
        "MUJOCO_GL=glx"
        "DISPLAY=:99"
        "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR_PATH")
else
    NATIVE_ENV=(env "PYTHONPATH=$LIBERO_PLUS")
fi
"${NATIVE_ENV[@]}" $VENV_OOD/bin/python -m async_vla_benchmark.scripts.run_stage3_new \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$MANIFEST" \
    --output-dir "$OUT" --scene ood --resume --verbose

echo ""
echo "========================================================"
echo "[5/7] Validating results..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.validate_stage3_new \
    --manifest "$MANIFEST" --output-dir "$OUT"

echo ""
echo "========================================================"
echo "[6/7] Running analysis..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.analyze_stage3_new \
    --results "$OUT/stage3_new_episode_results.csv" \
    --manifest "$MANIFEST" \
    --output-dir "$OUT/analysis" \
    --bootstrap-replicates 10000 --bootstrap-seed 20260826

echo ""
echo "========================================================"
echo "[7/7] Packaging and uploading to HuggingFace..."
echo "========================================================"
tar -czf "$WORKSPACE/stage3_new_results.tar.gz" -C "$WORKSPACE" stage3_new

$VENV_ID/bin/python - <<'PYEOF'
import os
from huggingface_hub import HfApi
from pathlib import Path

api   = HfApi()
token = os.environ["HF_TOKEN"]

try:
    api.create_repo("stage3-new-results", repo_type="dataset", private=True, token=token)
    print("Created repo: stage3-new-results")
except Exception:
    print("Repo already exists: stage3-new-results")

archive = Path(os.environ.get("VAST_WORKSPACE", "/workspace")) / "stage3_new_results.tar.gz"
print(f"Uploading {archive.stat().st_size / 1e9:.2f} GB...")
api.upload_file(
    path_or_fileobj=str(archive),
    path_in_repo="stage3_new_results.tar.gz",
    repo_id="stage3-new-results",
    repo_type="dataset",
    token=token,
)
user = api.whoami(token=token)["name"]
print(f"Upload complete: https://huggingface.co/datasets/{user}/stage3-new-results")
PYEOF

echo "COMPLETE. Results are under $WORKSPACE/stage3_new and the archive is $WORKSPACE/stage3_new_results.tar.gz"
echo "Return to the Vast.ai console and stop or destroy the instance to end GPU billing."
