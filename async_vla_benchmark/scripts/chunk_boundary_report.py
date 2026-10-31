"""Is naive_async's 0/6 an open-loop-horizon failure or a staleness failure?

Runs on episodes already on disk. No GPU, no new episodes, no third execution
strategy -- only the naive_async and rtc traces Stage 0 already wrote.

The question the pooled success table cannot answer: naive_async scored 0/6 at
Native ID on spatial_transport and long_stove_moka while rtc scored 6/6 and 5/6.
Two different stories produce that, and they imply opposite fixes:

  open-loop drift   H=25 means 1.25 s of blind execution at 20 Hz. The policy's
                    error accumulates across the chunk, and every chunk boundary
                    snaps the arm back toward reality. Fix is the horizon.
  staleness         Actions are wrong from the moment they are executed, evenly
                    across the chunk. Fix is the method.

They separate on *where in the chunk* the discontinuity lives. `action_vector`
is logged per control step, so take the per-step movement ||a_t - a_{t-1}|| and
split it by whether the step crossed a chunk boundary:

  drift      boundary jump >> interior step. The arm is being yanked at the seam
             because the chunk it just finished had drifted off.
  staleness  ratio near 1. Nothing special happens at the seam; the whole chunk
             is uniformly wrong.

RTC is the built-in reference: it blends across the boundary by construction, so
its ratio is the floor this measurement can produce on this task. naive_async's
ratio is only interesting relative to that, not in absolute terms.

Boundaries come from `chunk_id` changing, not `chunk_action_index == 0` -- RTC
discards the leading `delay_steps` actions of each chunk, so its first executed
index is not 0 and an index test would silently miss every RTC boundary.
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

from async_vla_benchmark.benchmark.stage0 import METHOD_DISPLAY


def episode_stats(frame: pd.DataFrame) -> dict[str, float] | None:
    """Boundary vs interior step size for one episode.

    Hold actions are dropped: they are a synthetic "freeze the arm" vector with
    no source observation, so the step into and out of a hold is an artefact of
    the queue, not of the policy's chunking.
    """
    frame = frame[~frame["is_hold_action"].astype(bool)].reset_index(drop=True)
    if len(frame) < 3:
        return None

    actions = np.stack(frame["action_vector"].apply(np.asarray).to_numpy())
    deltas = np.linalg.norm(np.diff(actions, axis=0), axis=1)

    # deltas[i] is the move from row i to row i+1, so label it by row i+1.
    chunk = frame["chunk_id"].to_numpy()
    crossed = chunk[1:] != chunk[:-1]

    boundary = deltas[crossed]
    interior = deltas[~crossed]
    if boundary.size == 0 or interior.size == 0:
        return None

    ages = frame["action_age_steps"].to_numpy()
    return {
        "boundary": float(boundary.mean()),
        "interior": float(interior.mean()),
        "ratio": float(boundary.mean() / interior.mean()) if interior.mean() else float("nan"),
        "chunks": int(crossed.sum()) + 1,
        "age_min": float(ages.min()),
        "age_max": float(ages.max()),
        "steps": int(len(frame)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/stage0"))
    parser.add_argument(
        "--delay",
        type=int,
        default=0,
        help="added delay to report on; 0 (Native) isolates the horizon question "
        "from the delay sweep",
    )
    parser.add_argument("--task", action="append", help="task_key filter, repeatable")
    args = parser.parse_args()

    results = args.output_dir / "latency_calibration_episode_results.csv"
    if not results.exists():
        print(f"no results CSV at {results}")
        return 1

    episodes = pd.read_csv(results)
    episodes = episodes[
        (episodes["added_delay_ms"] == args.delay) & (episodes["status"] == "ok")
    ]
    if args.task:
        episodes = episodes[episodes["task_key"].isin(args.task)]
    if episodes.empty:
        print("no episodes matched the filters")
        return 1

    print(f"Chunk-boundary discontinuity at added delay {args.delay} ms")
    print(f"source: {args.output_dir}\n")
    header = (
        f"{'task':<20}{'method':<14}{'ok':>6}{'boundary':>11}"
        f"{'interior':>10}{'ratio':>8}{'age steps':>12}"
    )
    print(header)
    print("-" * len(header))

    missing = 0
    for task in sorted(episodes["task_key"].unique()):
        for method in sorted(episodes["execution_method"].unique()):
            subset = episodes[
                (episodes["task_key"] == task)
                & (episodes["execution_method"] == method)
            ]
            if subset.empty:
                continue

            ratios, boundaries, interiors, age_lo, age_hi = [], [], [], [], []
            for run_id in subset["run_id"]:
                path = args.output_dir / "actions" / f"{run_id}.parquet"
                if not path.exists():
                    missing += 1
                    continue
                stats = episode_stats(pd.read_parquet(path))
                if stats is None:
                    continue
                ratios.append(stats["ratio"])
                boundaries.append(stats["boundary"])
                interiors.append(stats["interior"])
                age_lo.append(stats["age_min"])
                age_hi.append(stats["age_max"])

            if not ratios:
                continue
            ok = int((subset["success"] == 1).sum())
            print(
                f"{task:<20}{METHOD_DISPLAY.get(method, method):<14}"
                f"{ok:>3}/{len(subset):<2}"
                f"{statistics.mean(boundaries):>11.4f}"
                f"{statistics.mean(interiors):>10.4f}"
                f"{statistics.mean(ratios):>8.2f}"
                f"{statistics.mean(age_lo):>6.0f}-{statistics.mean(age_hi):<5.0f}"
            )

    if missing:
        print(f"\n{missing} episode(s) had no actions parquet and were skipped")

    print(
        "\nratio = mean step size crossing a chunk boundary / mean step size inside a "
        "chunk.\nRead naive_async against rtc on the same row-pair, not against 1.0: "
        "rtc blends\nacross the seam by construction, so it sets the floor this "
        "measurement can reach.\nA naive ratio well above rtc's means the chunk had "
        "drifted before it ended, which\nis a horizon finding. Comparable ratios mean "
        "the chunk was wrong throughout, which\nis a staleness finding."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
