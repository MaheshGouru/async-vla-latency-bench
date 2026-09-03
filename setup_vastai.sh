#!/usr/bin/env bash
# ============================================================
# Stage 3 New — vast.ai A100 bootstrap script
#
# Run this once after SSH-ing into a fresh vast.ai instance.
# Handles everything the Stage 1 notebooks do, condensed into
# a single non-interactive script for vast.ai.
#
# Prerequisites (set before running):
#   export HF_TOKEN="hf_..."       # HuggingFace token (read-only is enough)
#
# Usage:
#   bash setup_vastai.sh 2>&1 | tee ~/setup_vastai.log
# ============================================================
set -euo pipefail

# -----------------------------------------------------------
# Config — all pinned, do not change
# -----------------------------------------------------------
LEROBOT_COMMIT="2aba372b4e217cc47db28e0f836859b20d1456c9"
LIBERO_PLUS_SHA="4976dc3"
MODEL_REVISION="8e174154ef5f6c60a8da12ae99c303d8963138c1"
LIBERO_PLUS_URL="https://github.com/sylvestf/LIBERO-plus.git"

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_ID="$HOME/venv-stage1-id"
VENV_OOD="$HOME/venv-stage1-ood"
LIBERO_PLUS="$HOME/LIBERO-plus"
ASSETS_TARGET="$LIBERO_PLUS/libero/libero/assets"

# -----------------------------------------------------------
# Guards
# -----------------------------------------------------------
if [ -z "${HF_TOKEN:-}" ]; then
    echo "ERROR: HF_TOKEN is not set. Run: export HF_TOKEN='hf_...'"
    exit 1
fi

echo "========================================================"
echo "Stage 3 New — vast.ai setup"
echo "========================================================"

# -----------------------------------------------------------
# 1. System packages
# -----------------------------------------------------------
echo ""
echo ">>> [1/8] Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    git \
    unzip \
    build-essential \
    cmake \
    patchelf \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libglew-dev \
    libosmesa6-dev \
    libglib2.0-0 \
    libexpat1 \
    libfontconfig1-dev \
    imagemagick \
    libmagickwand-dev \
    software-properties-common \
    curl \
    wget \
    tmux

# Python 3.12 via deadsnakes (CUDA base image ships 3.10)
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3.12-distutils

# Make python3.12 the default python3
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 10
update-alternatives --install /usr/bin/python  python  /usr/bin/python3.12 10
python3.12 -m ensurepip --upgrade
python3.12 -m pip install --upgrade pip wheel setuptools

echo "Python: $(python3 --version)"
echo "DONE system packages"

# -----------------------------------------------------------
# 2. Use the extracted anonymous benchmark
# -----------------------------------------------------------
echo ""
echo ">>> [2/8] Using extracted benchmark..."
if [ ! -d "$REPO/async_vla_benchmark" ]; then
    echo "ERROR: extract the complete code archive before running setup."
    exit 1
fi
BENCH_SHA=anonymous-source
echo "Source revision: withheld for anonymous review"

# -----------------------------------------------------------
# 3. Clone LIBERO-Plus
# -----------------------------------------------------------
echo ""
echo ">>> [3/8] Cloning LIBERO-Plus..."
if [ ! -d "$LIBERO_PLUS/.git" ]; then
    git clone "$LIBERO_PLUS_URL" "$LIBERO_PLUS"
fi
git -C "$LIBERO_PLUS" checkout "$LIBERO_PLUS_SHA"
PLUS_SHA=$(git -C "$LIBERO_PLUS" rev-parse HEAD)
echo "LIBERO-Plus SHA: $PLUS_SHA"

# -----------------------------------------------------------
# 4. Create venv-stage1-id  (standard LIBERO via hf-libero)
# -----------------------------------------------------------
echo ""
echo ">>> [4/8] Creating venv-stage1-id..."
if [ ! -d "$VENV_ID" ]; then
    python3.12 -m venv "$VENV_ID"
fi
"$VENV_ID/bin/pip" install --upgrade pip wheel setuptools
"$VENV_ID/bin/pip" install \
    "lerobot[pi,libero] @ git+https://github.com/huggingface/lerobot.git@${LEROBOT_COMMIT}"
"$VENV_ID/bin/pip" install -e "$REPO"
"$VENV_ID/bin/pip" install \
    pandas pyarrow matplotlib pytest jupyter ipykernel
echo "DONE venv-stage1-id"

# -----------------------------------------------------------
# 5. Create venv-stage1-ood  (LIBERO-Plus; cannot coexist with hf-libero)
# -----------------------------------------------------------
echo ""
echo ">>> [5/8] Creating venv-stage1-ood..."
if [ ! -d "$VENV_OOD" ]; then
    python3.12 -m venv "$VENV_OOD"
fi
"$VENV_OOD/bin/pip" install --upgrade pip wheel setuptools
"$VENV_OOD/bin/pip" install \
    "lerobot[pi] @ git+https://github.com/huggingface/lerobot.git@${LEROBOT_COMMIT}"
"$VENV_OOD/bin/pip" install \
    robosuite==1.4.1 \
    bddl==1.0.1 \
    easydict==1.13 \
    mujoco==3.7.0 \
    matplotlib==3.10.8 \
    Wand==0.6.13 \
    scikit-image==0.25.2 \
    "gym==0.26.2" \
    future \
    huggingface_hub \
    pyarrow \
    pandas \
    pytest \
    jupyter \
    ipykernel
"$VENV_OOD/bin/pip" install --no-deps -e "$LIBERO_PLUS"
"$VENV_OOD/bin/pip" install -e "$REPO"
echo "DONE venv-stage1-ood"

# -----------------------------------------------------------
# 6. Pre-create LIBERO config to prevent interactive prompt
# -----------------------------------------------------------
echo ""
echo ">>> [6/8] Pre-creating LIBERO config..."
"$VENV_ID/bin/python" -c "
import libero, os, yaml
root = os.path.join(os.path.dirname(libero.__file__), 'libero')
cfg_dir = os.path.expanduser('~/.libero')
os.makedirs(cfg_dir, exist_ok=True)
cfg_path = os.path.join(cfg_dir, 'config.yaml')
if not os.path.exists(cfg_path):
    with open(cfg_path, 'w') as f:
        yaml.dump({'assets_dir': os.path.join(root, 'assets')}, f)
    print('Created', cfg_path)
else:
    print('Already exists', cfg_path)
" 2>/dev/null || true

# -----------------------------------------------------------
# 7. Download LIBERO-Plus assets (~6.4 GB)
# -----------------------------------------------------------
echo ""
echo ">>> [7/8] Downloading LIBERO-Plus assets (~6.4 GB)..."
if [ -d "$ASSETS_TARGET" ] && [ "$(ls -A "$ASSETS_TARGET" 2>/dev/null)" ]; then
    echo "Assets already installed at $ASSETS_TARGET; skipping download."
else
    DOWNLOAD_DIR="$HOME/libero-plus-download"
    EXTRACT_DIR="$HOME/libero-plus-assets-extracted"
    mkdir -p "$DOWNLOAD_DIR" "$EXTRACT_DIR"

    HF_TOKEN="$HF_TOKEN" "$VENV_OOD/bin/python" - <<'PYEOF'
from huggingface_hub import hf_hub_download
from pathlib import Path
import os
path = hf_hub_download(
    repo_id="Sylvest/LIBERO-plus",
    repo_type="dataset",
    filename="assets.zip",
    local_dir=str(Path.home() / "libero-plus-download"),
    token=os.environ["HF_TOKEN"],
)
print("Downloaded:", path)
PYEOF

    ARCHIVE="$DOWNLOAD_DIR/assets.zip"
    if [ ! -f "$ARCHIVE" ]; then
        echo "ERROR: assets.zip not found at $ARCHIVE"
        exit 1
    fi
    echo "Extracting $(du -sh "$ARCHIVE" | cut -f1) archive..."
    unzip -q "$ARCHIVE" -d "$EXTRACT_DIR"

    # Find the largest 'assets' subdirectory
    ASSETS_SRC=$(find "$EXTRACT_DIR" -type d -name "assets" | \
        awk '{cmd="du -sb "$0; cmd | getline size; close(cmd); print size, $0}' | \
        sort -rn | head -1 | awk '{print $2}')

    if [ -z "$ASSETS_SRC" ]; then
        echo "ERROR: no assets directory found in extracted archive"
        exit 1
    fi

    mkdir -p "$(dirname "$ASSETS_TARGET")"
    mv "$ASSETS_SRC" "$ASSETS_TARGET"
    echo "Installed assets at $ASSETS_TARGET"

    # Cleanup
    rm -rf "$DOWNLOAD_DIR" "$EXTRACT_DIR"
fi

ASSET_COUNT=$(find "$ASSETS_TARGET" -type f | wc -l)
echo "Assets: $ASSET_COUNT files in $ASSETS_TARGET"

# -----------------------------------------------------------
# 8. Register Jupyter kernels and smoke-check imports
# -----------------------------------------------------------
echo ""
echo ">>> [8/8] Registering Jupyter kernels and checking imports..."

"$VENV_ID/bin/python" -m ipykernel install --user --name stage1-id --display-name "Stage1-ID (py3.12)"
"$VENV_OOD/bin/python" -m ipykernel install --user --name stage1-ood --display-name "Stage1-OOD (py3.12)"

export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MPLBACKEND=Agg

"$VENV_ID/bin/python" -c "
import torch, lerobot, libero
print('ID env OK — torch:', torch.__version__, '| lerobot OK | libero OK')
"

export PYTHONPATH="$LIBERO_PLUS"
"$VENV_OOD/bin/python" -c "
import torch, lerobot
from wand.api import library
print('OOD env OK — torch:', torch.__version__, '| lerobot OK | MagickWand OK')
" || true
unset PYTHONPATH

# Verify benchmark module
"$VENV_ID/bin/python" -c "
from async_vla_benchmark.benchmark.stage3_new import SEEDS, CANDIDATES, _EXPECTED_TOTAL
print(f'stage3_new module OK — {_EXPECTED_TOTAL} planned episodes, {len(SEEDS)} seeds, {len(CANDIDATES)} candidates')
"

# -----------------------------------------------------------
# Summary
# -----------------------------------------------------------
PLUS_FINAL_SHA=$(git -C "$LIBERO_PLUS" rev-parse HEAD)
echo ""
echo "========================================================"
echo "SETUP COMPLETE"
echo "========================================================"
echo "  Repo:         $REPO  (source: $BENCH_SHA)"
echo "  LIBERO-Plus:  $LIBERO_PLUS  (SHA: $PLUS_FINAL_SHA)"
echo "  venv-id:      $VENV_ID"
echo "  venv-ood:     $VENV_OOD"
echo "  Assets:       $ASSETS_TARGET ($ASSET_COUNT files)"
echo ""
echo "Next steps:"
echo "  1. Start Jupyter: jupyter lab --ip=0.0.0.0 --no-browser --port=8888"
echo "  2. Open notebooks/stage3_new_jupyter/ in order (01 -> 05)"
echo "  3. After notebook 05, download ~/stage3_new_results.tar.gz"
echo ""
echo "GPU check:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits | \
    awk -F, '{printf "  GPU %s: %s  used=%sMiB/%sMiB  util=%s%%\n",$1,$2,$3,$4,$5}'
echo "========================================================"
