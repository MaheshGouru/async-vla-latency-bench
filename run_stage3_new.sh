#!/usr/bin/env bash
set -euo pipefail

VENV_ID=~/venv-stage1-id
VENV_OOD=~/venv-stage1-ood
REPO=~/async-vla-latency-bench
OUT=~/stage3_new
MANIFEST=$OUT/stage3_new_manifest.csv
LIBERO_PLUS=~/LIBERO-plus
STAGE1_NATIVE=~/stage1-native

BENCH_SHA=11fcf477223cc6212b7c1d9bca82e081cf3a1f1d
LEROBOT_SHA=2aba372b4e217cc47db28e0f836859b20d1456c9
LIBEROPLUS_SHA=4976dc30028e805ff8094b55501d532c48fec182
MODEL_SHA=8e174154ef5f6c60a8da12ae99c303d8963138c1

export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export MPLBACKEND=Agg

mkdir -p "$OUT"

echo "========================================================"
echo "[1/7] Generating full manifest..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.make_stage3_new_manifest \
    --output "$MANIFEST" \
    --git-sha "$BENCH_SHA" \
    --lerobot-git-sha "$LEROBOT_SHA" \
    --libero-plus-git-sha "$LIBEROPLUS_SHA" \
    --model-revision "$MODEL_SHA"

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
    --output-dir "$OUT/smoke" --scene id --resume || true

echo ""
echo "========================================================"
echo "[3/7] Full ID run (1,152 episodes)..."
echo "========================================================"
$VENV_ID/bin/python -m async_vla_benchmark.scripts.run_stage3_new \
    --config "$REPO/async_vla_benchmark/configs/stage3_new.yaml" \
    --manifest "$MANIFEST" \
    --output-dir "$OUT" --scene id --resume

echo ""
echo "========================================================"
echo "[4/7] Full OOD run (2,304 episodes)..."
echo "========================================================"
# On rootless containers, ~/stage1-native is a conda-forge prefix built by
# setup_instance.sh's sudo fallback (see [1/8] there). Its GLVND libEGL.so
# dispatcher needs __EGL_VENDOR_LIBRARY_DIRS pointed at its vendor ICD JSON
# or it silently can't find Mesa's software EGL driver at all; the plain
# LD_LIBRARY_PATH prefix handles the rest (libEGL/libGL/MagickWand).
if [ -d "$STAGE1_NATIVE" ]; then
    NATIVE_ENV=(env
        "PYTHONPATH=$LIBERO_PLUS"
        "LD_LIBRARY_PATH=$STAGE1_NATIVE/lib:${LD_LIBRARY_PATH:-}"
        "PATH=$STAGE1_NATIVE/bin:$PATH"
        "MAGICK_HOME=$STAGE1_NATIVE"
        "__EGL_VENDOR_LIBRARY_DIRS=$STAGE1_NATIVE/share/glvnd/egl_vendor.d")
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
echo "[7/7] Packaging, uploading to HuggingFace, shutting down..."
echo "========================================================"
tar -czf ~/stage3_new_results.tar.gz -C ~ stage3_new

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

archive = Path.home() / "stage3_new_results.tar.gz"
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

sudo -n true 2>/dev/null && sudo shutdown -h now || echo "No usable sudo — skipping auto-shutdown; everything above already completed."
