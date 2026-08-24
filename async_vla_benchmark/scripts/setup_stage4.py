#!/usr/bin/env python3
"""Stage 4 preflight setup: pinned checkouts, venv, dependency overrides, robosuite fix."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

OFT_SHA = "e4287e94541f459edc4feabc4e181f537cd569a8"
LEROBOT_SHA = "2aba372b4e217cc47db28e0f836859b20d1456c9"
CKPT = "moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10"
REV = "13cdacd486c504e65408fc3c9e12fec9c5bf0382"

P = Path.home() / "LIBERO-plus"
OFT = Path.home() / "openvla-oft"
DLIMP = Path.home() / "dlimp_openvla"
LERO = Path.home() / "lerobot-stage4"
ENV = Path.home() / "venv-stage4-openvla"
PY = ENV / "bin/python"
OUT = Path.home() / "stage4"


def run(cmd, env=None, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run([str(c) for c in cmd], env=env, check=True, **kwargs)


def run_out(cmd, env=None, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run([str(c) for c in cmd], env=env, capture_output=True, text=True, check=True, **kwargs)


def gpu_info(index):
    line = run_out(
        [
            "nvidia-smi",
            "-i",
            index,
            "--query-gpu=name,memory.total,memory.used,utilization.gpu,driver_version",
            "--format=csv,noheader,nounits",
        ]
    ).stdout.strip()
    name, total, used, util, driver = [v.strip() for v in line.split(",")]
    return name, int(total), int(used), int(util), driver, line


def pinned_checkout(path, url, sha):
    if not path.exists():
        run(["git", "clone", url, str(path)])
    actual = run_out(["git", "-C", str(path), "rev-parse", "HEAD"]).stdout.strip()
    if actual != sha:
        dirty = run_out(["git", "-C", str(path), "status", "--porcelain"]).stdout
        if dirty:
            raise SystemExit(f"STOP: {path} is modified; preserve before checkout")
        run(["git", "-C", str(path), "fetch", "origin", sha])
        run(["git", "-C", str(path), "checkout", "--detach", sha])
    resolved = run_out(["git", "-C", str(path), "rev-parse", "HEAD"]).stdout.strip()
    if resolved != sha:
        raise SystemExit(f"STOP: checkout mismatch for {path}: expected {sha}, found {resolved}")


def patch_dep_files(root):
    for fname in ["pyproject.toml", "setup.py", "requirements.txt"]:
        ffile = root / fname
        if not ffile.exists():
            continue
        text = ffile.read_text()
        text = text.replace("tensorflow==2.15.0", "tensorflow>=2.16.1")
        text = text.replace('"tensorflow_graphics==2021.12.3",', "")
        text = text.replace("tensorflow_graphics==2021.12.3", "")
        text = text.replace('"tensorflow-graphics==2021.12.3",', "")
        text = text.replace("tensorflow-graphics==2021.12.3", "")
        text = text.replace("git+https://github.com/moojink/dlimp_openvla", f"file://{DLIMP}")
        ffile.write_text(text)


def ensure_venv():
    if PY.exists():
        return
    py312 = shutil.which("python3.12")
    conda = shutil.which("conda") or shutil.which("mamba")
    if py312:
        run([py312, "-m", "venv", str(ENV)])
    elif conda:
        run([conda, "create", "-y", "-p", str(ENV), "python=3.12", "pip"])
    else:
        raise SystemExit("STOP: python3.12 or conda/mamba is required")


def install(marker, repo, force):
    if marker.exists() and not force:
        print("PASS: dependencies already installed; skipping base install")
        return
    run([str(PY), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([str(PY), "-m", "pip", "install", "-e", str(OFT)])
    run([str(PY), "-m", "pip", "install", "--no-deps", "-e", str(LERO)])
    run(
        [str(PY), "-m", "pip", "install", "-e", str(repo), "pandas", "pyarrow", "pytest", "gymnasium", "hf-libero"]
    )


def override_deps():
    run([str(PY), "-m", "pip", "install", "numpy==1.26.4"])
    run([str(PY), "-m", "pip", "install", "scipy==1.13.1"])
    run([str(PY), "-m", "pip", "install", "ml-dtypes==0.5.1"])
    run([str(PY), "-m", "pip", "install", "opencv-python==4.10.0.84"])
    run([str(PY), "-m", "pip", "install", "packaging==24.2"])
    run([str(PY), "-m", "pip", "install", "setuptools==75.8.0"])


def configure_libero():
    libero_dir = Path.home() / ".libero"
    libero_dir.mkdir(parents=True, exist_ok=True)
    config_file = libero_dir / "config.yaml"
    code = f"""
import yaml
from pathlib import Path
try:
    from libero.libero import get_default_path_dict
    paths = get_default_path_dict()
except Exception:
    pkg = Path("{PY.parent.parent / 'lib' / 'python3.12' / 'site-packages' / 'libero' / 'libero'}")
    paths = {{
        "benchmark_root": str(pkg),
        "bddl_files": str(pkg / "bddl_files"),
        "init_states": str(pkg / "init_files"),
        "datasets": str(Path.home() / "libero_datasets"),
        "assets": str(pkg / "assets"),
    }}
Path("{libero_dir}").mkdir(parents=True, exist_ok=True)
with open("{config_file}", "w") as f:
    yaml.dump(paths, f)
"""
    run([str(PY), "-c", code])


def patch_robosuite():
    site_packages = run_out([str(PY), "-c", "import site; print(site.getsitepackages()[0])"]).stdout.strip()
    robosuite_dir = Path(site_packages) / "robosuite"
    if not robosuite_dir.exists():
        raise SystemExit("STOP: robosuite not installed")

    macros_file = robosuite_dir / "macros.py"
    text = macros_file.read_text()
    text = text.replace('FILE_LOGGING_LEVEL = "DEBUG"', "FILE_LOGGING_LEVEL = None")
    macros_file.write_text(text)

    private = robosuite_dir / "macros_private.py"
    private.write_text(
        "# Auto-generated private macros\n"
        "import robosuite.macros as _macros\n"
        "_macros.FILE_LOGGING_LEVEL = None\n"
    )


def preflight(repo, gpu, gpu_line):
    env = os.environ.copy()
    env.update(
        {
            "CUDA_VISIBLE_DEVICES": gpu,
            "MUJOCO_EGL_DEVICE_ID": gpu,
            "MUJOCO_GL": "egl",
            "PYOPENGL_PLATFORM": "egl",
            "MPLBACKEND": "Agg",
            "PYTHONPATH": f"{OFT}{os.pathsep}{repo}",
        }
    )

    versions = run_out(
        [str(PY), "-c", "import sys, torch, transformers; print(sys.version.split()[0], torch.__version__, transformers.__version__)"],
        env=env,
    ).stdout.strip()
    print("runtime", versions)
    pyver, torchver, transformersver = versions.split()
    if not torchver.startswith("2.2.0") or not transformersver.startswith("4.40.1"):
        raise SystemExit(f"STOP: unexpected runtime versions {versions}")

    run([str(PY), "-m", "pytest", "-q", "-s", str(repo / "async_vla_benchmark" / "tests")], env=env)

    code = f"from huggingface_hub import snapshot_download; print(snapshot_download(repo_id='{CKPT}', revision='{REV}'))"
    snap = run_out([str(PY), "-c", code], env=env).stdout.strip().splitlines()[-1]
    snap_path = Path(snap)
    (OUT / "stage4_checkpoint_snapshot.txt").write_text(str(snap_path) + "\n")

    required = [
        "config.json",
        "dataset_statistics.json",
        "action_head--300000_checkpoint.pt",
        "proprio_projector--300000_checkpoint.pt",
    ]
    missing = [x for x in required if not (snap_path / x).is_file()]
    if missing:
        raise SystemExit(f"STOP: pinned checkpoint snapshot missing {missing}")

    packages = run_out([str(PY), "-m", "pip", "freeze"]).stdout.splitlines()
    repo_sha = run_out(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip()
    plus_sha = run_out(["git", "-C", str(P), "rev-parse", "HEAD"]).stdout.strip()
    provenance = {
        "repository_sha": repo_sha,
        "libero_plus_sha": plus_sha,
        "lerobot_sha": LEROBOT_SHA,
        "openvla_oft_sha": OFT_SHA,
        "checkpoint_id": CKPT,
        "checkpoint_revision": REV,
        "checkpoint_snapshot": str(snap_path),
        "gpu_index": gpu,
        "gpu": gpu_line,
        "python": pyver,
        "packages": packages,
    }
    (OUT / "stage4_preflight_environment.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print("PASS: Stage 4 pinned OpenVLA-OFT preflight complete")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--gpu", default="3")
    parser.add_argument("--min-free-mib", type=int, default=34000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    for path in (args.repo, P, P / "libero" / "libero" / "assets"):
        if not path.exists():
            raise SystemExit(f"STOP: missing prerequisite {path}")

    name, total, used, util, driver, line = gpu_info(args.gpu)
    if "A100" not in name:
        raise SystemExit(f"STOP: expected A100, found {name}")
    free = total - used
    if free < args.min_free_mib or util >= 5:
        raise SystemExit(f"STOP: GPU {args.gpu} lacks capacity: {line}; free={free} MiB")
    print(f"GPU {args.gpu}: used={used} MiB, free={free} MiB, util={util}%")

    OUT.mkdir(exist_ok=True)
    pinned_checkout(OFT, "https://github.com/moojink/openvla-oft.git", OFT_SHA)
    pinned_checkout(LERO, "https://github.com/huggingface/lerobot.git", LEROBOT_SHA)
    if not DLIMP.exists():
        run(["git", "clone", "https://github.com/moojink/dlimp_openvla", str(DLIMP)])
    patch_dep_files(DLIMP)
    patch_dep_files(OFT)

    ensure_venv()
    marker = ENV / ".stage4_dependencies_complete"
    install(marker, args.repo, args.force)
    override_deps()
    configure_libero()
    patch_robosuite()
    preflight(args.repo, args.gpu, line)
    marker.write_text("complete\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
