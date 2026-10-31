#!/usr/bin/env python3
"""Rebuild the spec §20 summary tables from per-episode artifacts.

`episodes.csv`, `requests.csv`, and `horizon_sweep.csv` are named entry
requirements for Days 4-8 (`DAYS_4_8_SPEC.md` §2), but nothing in the repository
produced them -- the existing copies were assembled by hand during the Days 1-3
audit, so they go stale the moment any episode is re-run and there is no command
to refresh them.

Everything here is derived from `episodes/*.json` and `requests/*.parquet`, which
are the authoritative per-episode records. That also makes the aggregate summary
JSONs race-proof: `run_benchmark.py` merges its own results into them at the end
of a run, so two concurrently dispatched jobs (one per strategy) can interleave
their read-modify-write and drop each other's rows. Rebuilding from the episode
files recovers the full set regardless of how the runs were sharded.

Experiment membership comes from `run_benchmark`'s own plan functions rather than
by parsing episode_id strings, so the matrix cannot drift from what was run.
"""

import argparse
import json
from pathlib import Path

from async_vla_benchmark.benchmark.config import load_config
from async_vla_benchmark.benchmark.logging import ensure_dir, write_json
from async_vla_benchmark.scripts.run_benchmark import (
    _episode_id,
    _selected_tasks_from_file,
    core_plans,
    horizon_plans,
)

ROOT = Path(__file__).resolve().parents[1]


def _expected_episode_ids(cfg, tasks: list[str]) -> tuple[list[str], list[str]]:
    """The episode ids the core and horizon-sweep matrices call for, in plan order."""
    core = [_episode_id(plan) for plan in core_plans(tasks, cfg.seeds)]
    sweep = [_episode_id(plan) for plan in horizon_plans(tasks)]
    return core, sweep


def _load_episode_summaries(output_dir: Path) -> dict[str, dict]:
    summaries = {}
    for path in sorted((output_dir / "episodes").glob("*.json")):
        summary = json.loads(path.read_text())
        summaries[summary.get("episode_id", path.stem)] = summary
    return summaries


def _write_csv(path: Path, rows: list[dict]) -> None:
    import pandas as pd

    ensure_dir(path.parent)
    pd.DataFrame(rows).to_csv(path, index=False)


def _collect_requests(output_dir: Path, episode_ids: list[str]) -> list[dict]:
    import pandas as pd

    frames = []
    for episode_id in episode_ids:
        path = output_dir / "requests" / f"{episode_id}.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path))
    if not frames:
        return []
    return pd.concat(frames, ignore_index=True).to_dict("records")


def main(config_path: Path, output_dir: Path) -> int:
    cfg = load_config(config_path)
    # Resolve the manifest against --output-dir, matching run_benchmark.py's own
    # rewrite. cfg.selected_tasks_file is a repo-relative path, which is wrong
    # anywhere the outputs are not the repo's own directory -- on Modal the
    # outputs live on a volume at /data/outputs and the repo copy is excluded by
    # .dockerignore, so the configured path resolves to nothing.
    cfg.selected_tasks_file = str(output_dir / "summaries" / "selected_tasks.json")
    tasks = _selected_tasks_from_file(Path(cfg.selected_tasks_file))
    if not tasks:
        print(f"no selected tasks found at {cfg.selected_tasks_file}")
        return 1

    core_ids, sweep_ids = _expected_episode_ids(cfg, tasks)
    summaries = _load_episode_summaries(output_dir)

    core_rows = [summaries[eid] for eid in core_ids if eid in summaries]
    sweep_rows = [summaries[eid] for eid in sweep_ids if eid in summaries]

    summaries_dir = output_dir / "summaries"
    _write_csv(summaries_dir / "episodes.csv", core_rows)
    _write_csv(summaries_dir / "horizon_sweep.csv", sweep_rows)

    # Rebuilt from the episode files, so a sharded or interrupted run cannot leave
    # these holding only the last writer's subset.
    write_json(summaries_dir / "core_summaries.json", core_rows)
    write_json(summaries_dir / "horizon_sweep_summaries.json", sweep_rows)

    # Union, preserving order: the sweep's h=10 cells reuse core's episodes, so a
    # plain concatenation would duplicate every shared request row.
    all_ids = list(dict.fromkeys(core_ids + sweep_ids))
    request_rows = _collect_requests(output_dir, [i for i in all_ids if i in summaries])
    _write_csv(summaries_dir / "requests.csv", request_rows)

    missing_core = [eid for eid in core_ids if eid not in summaries]
    missing_sweep = [eid for eid in sweep_ids if eid not in summaries]

    print(f"episodes.csv:       {len(core_rows)}/{len(core_ids)} core episodes")
    print(f"horizon_sweep.csv:  {len(sweep_rows)}/{len(sweep_ids)} horizon-sweep episodes")
    print(f"requests.csv:       {len(request_rows)} request records")
    for label, missing in (("core", missing_core), ("horizon_sweep", missing_sweep)):
        if missing:
            print(f"\nMISSING {label} episodes ({len(missing)}):")
            for eid in missing:
                print(f"  {eid}")
    return 1 if (missing_core or missing_sweep) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "days1_3.yaml")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.config, args.output_dir))
