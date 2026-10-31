#!/usr/bin/env python3
"""Render the exact Stage-1 ID/OOD reset frames and compose a paper gallery.

Run the ``id`` and ``ood`` shards in their respective pinned environments, then
run ``compose`` after both shards finish. No policy checkpoint is loaded.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import textwrap
from pathlib import Path
from typing import Any

TASK_ORDER = ["spatial_transport", "goal_drawer", "long_stove_moka"]
CONDITION_ORDER = [
    "id",
    "object_layout",
    "robot_initial_state",
    "camera_viewpoint",
    "sensor_noise",
    "light_conditions",
    "background_textures",
    "language_instructions",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def reset_observation(env: Any, seed: int) -> dict[str, Any]:
    reset = env.reset(seed=seed)
    observation = reset[0] if isinstance(reset, tuple) else reset
    if not isinstance(observation, dict):
        raise TypeError(f"expected dictionary observation, got {type(observation)!r}")
    return observation


def agentview(observation: dict[str, Any]) -> tuple[str, Any]:
    import numpy as np

    pixels = observation.get("pixels")
    if not isinstance(pixels, dict):
        raise KeyError(f"observation has no pixel dictionary; keys={sorted(observation)}")
    candidates = [(name, value) for name, value in pixels.items() if "agentview" in name.lower()]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one agentview camera, found {sorted(pixels)}")
    name, value = candidates[0]
    array = np.asarray(value)
    if array.ndim == 4 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 3 or array.shape[-1] not in (3, 4):
        raise ValueError(f"unexpected {name} image shape {array.shape}")
    if array.dtype != np.uint8:
        array = ((array * 255).clip(0, 255) if array.max() <= 1 else array.clip(0, 255)).astype(np.uint8)
    # This is the exact correction used by policy._correct_libero_image_orientation.
    return name, np.ascontiguousarray(array[::-1, ::-1, :3])


def direct_libero_reset(
    suite_name: str,
    task_index: int,
    *,
    is_libero_plus: bool,
    seed: int,
    width: int,
    height: int,
    num_steps_wait: int,
) -> tuple[Any, str, str, str, Any]:
    """Create one LIBERO reset without importing LeRobot or a policy checkpoint."""
    import numpy as np
    import torch
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    suites = benchmark.get_benchmark_dict()
    if suite_name not in suites:
        raise KeyError(f"unknown LIBERO suite {suite_name!r}")
    suite = suites[suite_name]()
    task = suite.get_task(task_index)
    filename = Path(task.init_states_file)
    init_root = Path(get_libero_path("init_states"))
    if is_libero_plus and ("_add_" in filename.name or "_level" in filename.name):
        init_path = init_root / "libero_newobj" / task.problem_folder / filename.name
        init_states = torch.load(init_path, map_location="cpu").reshape(1, -1)
    elif is_libero_plus:
        suffix = re.compile(r"_(?:language|view|light)_[^.]*|_(?:table|tb)_\d+")
        stripped = suffix.sub("", filename.stem) + filename.suffix
        init_path = init_root / task.problem_folder / stripped
        init_states = torch.load(init_path, map_location="cpu")
    else:
        init_path = init_root / task.problem_folder / filename.name
        init_states = torch.load(init_path, map_location="cpu")

    bddl = Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
    env = OffScreenRenderEnv(
        bddl_file_name=str(bddl),
        camera_heights=height,
        camera_widths=width,
        control_freq=20,
        hard_reset=True,
    )
    env.seed(seed)
    env.reset()
    raw = env.set_init_state(init_states[0])
    for _ in range(num_steps_wait):
        raw, _, _, _ = env.step([0, 0, 0, 0, 0, 0, -1])
    image = np.ascontiguousarray(np.asarray(raw["agentview_image"])[::-1, ::-1, :3])
    return env, task.name, task.language, "agentview_image", image


def render(args: argparse.Namespace) -> int:
    from PIL import Image
    from async_vla_benchmark.benchmark.config import load_config

    if args.backend == "lerobot":
        from async_vla_benchmark.benchmark.environment import (
            get_task_info,
            make_libero_env,
            make_libero_plus_env,
        )

    if args.scene == "ood":
        # Match the known-good Stage-1 import order for the no-sudo ImageMagick setup.
        from wand.api import library as _wand_library  # noqa: F401

    cfg = load_config(args.config)
    variants = read_csv(args.variants)
    if len(variants) != 21:
        raise RuntimeError(f"expected the frozen 21-row Stage-1 variant CSV, found {len(variants)} rows")
    if {row["task_key"] for row in variants} != set(TASK_ORDER):
        raise RuntimeError("frozen variant task keys differ from the three Stage-1 tasks")
    if {row["perturbation_key"] for row in variants} != set(CONDITION_ORDER[1:]):
        raise RuntimeError("frozen variant perturbation keys differ from the seven Stage-1 perturbations")

    frame_dir = args.output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    plans: list[dict[str, str]] = []
    if args.scene == "id":
        for task_key in TASK_ORDER:
            source = next(row for row in variants if row["task_key"] == task_key)
            plans.append({
                **source,
                "perturbation_key": "id",
                "official_category": "ID",
                "classification_id": "",
                "api_task_index": source["base_task_id"],
                "variant_name": source["base_task_name"],
                "difficulty_level": "",
            })
    else:
        plans = sorted(
            variants,
            key=lambda row: (TASK_ORDER.index(row["task_key"]), CONDITION_ORDER.index(row["perturbation_key"])),
        )

    records = []
    for index, plan in enumerate(plans, 1):
        task_index = int(plan["api_task_index"])
        if args.backend == "direct_libero":
            env, task_name, query, camera_key, image = direct_libero_reset(
                plan["suite"], task_index, is_libero_plus=args.scene == "ood",
                seed=args.seed, width=cfg.observation_width,
                height=cfg.observation_height, num_steps_wait=cfg.num_steps_wait,
            )
        else:
            maker = make_libero_env if args.scene == "id" else make_libero_plus_env
            env = maker(
                plan["suite"], task_index, seed=args.seed,
                control_mode=cfg.control_mode, obs_type=cfg.obs_type,
                camera_name=cfg.camera_name,
                observation_width=cfg.observation_width,
                observation_height=cfg.observation_height,
                init_states=cfg.init_states, episode_length=cfg.episode_length,
                num_steps_wait=cfg.num_steps_wait, episode_index=0,
                reset_on_create=False,
            )
            observation = reset_observation(env, args.seed)
            task_info = get_task_info(env, plan["suite"], task_index)
            task_name = task_info.task_name
            query = task_info.language_instruction
            camera_key, image = agentview(observation)
        try:
            if task_name != plan["variant_name"]:
                raise RuntimeError(
                    f"task mismatch for {plan['task_key']}/{plan['perturbation_key']}: "
                    f"{task_name!r} != {plan['variant_name']!r}"
                )
            relative = Path("frames") / f"{plan['task_key']}__{plan['perturbation_key']}__agentview.png"
            Image.fromarray(image).save(args.output_dir / relative)
            record = {
                "task_key": plan["task_key"],
                "scene_condition": args.scene,
                "perturbation_key": plan["perturbation_key"],
                "official_category": plan["official_category"],
                "suite": plan["suite"],
                "base_task_id": plan["base_task_id"],
                "classification_id": plan["classification_id"],
                "api_task_index": plan["api_task_index"],
                "difficulty_level": plan["difficulty_level"],
                "variant_name": task_name,
                "policy_query": query,
                "camera_key": camera_key,
                "orientation": "policy_facing_180_degree_correction",
                "seed": str(args.seed),
                "frame_path": str(relative),
            }
            records.append(record)
            print(f"[{index}/{len(plans)}] {plan['task_key']}/{plan['perturbation_key']}: {query}")
        finally:
            close = getattr(env, "close", None)
            if callable(close):
                close()

    shard = args.output_dir / f"stage1_task_gallery_{args.scene}.csv"
    with shard.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"PASS: rendered {len(records)} {args.scene} frames to {frame_dir}; metadata={shard}")
    return 0


def font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def compose(args: argparse.Namespace) -> int:
    from PIL import Image, ImageDraw

    records = read_csv(args.output_dir / "stage1_task_gallery_id.csv")
    records += read_csv(args.output_dir / "stage1_task_gallery_ood.csv")
    if len(records) != 24:
        raise RuntimeError(f"expected 24 frames (3 ID + 21 OOD), found {len(records)}")
    by_key = {(row["task_key"], row["perturbation_key"]): row for row in records}
    expected = {(task, condition) for task in TASK_ORDER for condition in CONDITION_ORDER}
    if set(by_key) != expected:
        raise RuntimeError(f"gallery key mismatch: missing={sorted(expected-set(by_key))}")

    cell_w, image_h, caption_h = 270, 224, 122
    row_header, col_header, margin = 205, 64, 20
    canvas = Image.new("RGB", (row_header + cell_w * 8 + margin, col_header + (image_h + caption_h) * 3 + margin), "white")
    draw = ImageDraw.Draw(canvas)
    title_font, label_font, body_font, tiny_font = font(17, True), font(13, True), font(11), font(9)
    for ci, condition in enumerate(CONDITION_ORDER):
        x = row_header + ci * cell_w + cell_w // 2
        draw.text((x, 20), condition, font=label_font, fill="#17212B", anchor="mm")
    for ti, task in enumerate(TASK_ORDER):
        y0 = col_header + ti * (image_h + caption_h)
        draw.text((12, y0 + image_h // 2), task, font=title_font, fill="#17212B", anchor="lm")
        for ci, condition in enumerate(CONDITION_ORDER):
            row = by_key[(task, condition)]
            x0 = row_header + ci * cell_w
            image = Image.open(args.output_dir / row["frame_path"]).convert("RGB").resize((224, 224))
            canvas.paste(image, (x0 + (cell_w - 224) // 2, y0))
            query_lines = textwrap.wrap(f"Query: {row['policy_query']}", width=37)[:4]
            caption = "\n".join(query_lines)
            draw.multiline_text((x0 + 8, y0 + image_h + 7), caption, font=body_font, fill="#17212B", spacing=2)
            provenance = "ID" if condition == "id" else f"c{row['classification_id']} · L{row['difficulty_level']}"
            draw.text((x0 + 8, y0 + image_h + caption_h - 19), provenance, font=tiny_font, fill="#52606D")

    png = args.output_dir / "stage1_exact_task_perturbation_gallery.png"
    pdf = args.output_dir / "stage1_exact_task_perturbation_gallery.pdf"
    canvas.save(png)
    canvas.save(pdf, "PDF", resolution=300.0)
    combined = args.output_dir / "stage1_task_gallery_metadata.csv"
    with combined.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(sorted(records, key=lambda r: (TASK_ORDER.index(r["task_key"]), CONDITION_ORDER.index(r["perturbation_key"]))))
    (args.output_dir / "stage1_task_gallery_provenance.json").write_text(json.dumps({
        "frame_count": 24,
        "tasks": TASK_ORDER,
        "conditions": CONDITION_ORDER,
        "camera": "agentview",
        "orientation": "same 180-degree correction as policy input",
        "queries": "get_task_info(...).language_instruction; exact string supplied to policy",
    }, indent=2) + "\n")
    print(f"PASS: composed 3x8 exact Stage-1 gallery: {png} and {pdf}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", choices=("id", "ood", "compose"), required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--backend", choices=("lerobot", "direct_libero"), default="lerobot")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    return compose(args) if args.scene == "compose" else render(args)


if __name__ == "__main__":
    raise SystemExit(main())
