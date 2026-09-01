#!/usr/bin/env python3
"""Bootstrap analysis for Stage 3 New high-power replication.

Resamples 64 complete seed blocks (not individual rows) with at least 10,000
replicates. Primary operating point: h=25. Includes cross-task object-layout
contrasts and a low-n vs high-n comparison table.
"""
from __future__ import annotations
import argparse, math, os, random
from pathlib import Path

from async_vla_benchmark.benchmark.logging import read_csv, write_csv
from async_vla_benchmark.benchmark.stage3_new import CANDIDATES, HORIZONS, SEEDS, _OLD_SEEDS

_OBJECT_LAYOUT_KEYS = ("spatial_object_layout", "goal_object_layout", "long_stove_object_layout")


def _rate(rows: list[dict]) -> float:
    return sum(int(r["success"]) for r in rows) / len(rows) if rows else float("nan")


def _wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not n:
        return float("nan"), float("nan")
    p = k / n
    den    = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return center - margin, center + margin


def _bootstrap_ci(values: list[float], n_draws: int,
                  rng_seed: int) -> tuple[float, float]:
    rng = random.Random(rng_seed)
    n   = len(values)
    means = sorted(
        sum(values[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(n_draws)
    )
    def q(p: float) -> float:
        x = (len(means) - 1) * p
        lo, hi = math.floor(x), math.ceil(x)
        return means[lo] if lo == hi else means[lo] * (hi - x) + means[hi] * (x - lo)
    return q(0.025), q(0.975)


def _interaction_values(rows: list[dict], task_key: str, candidate_key: str,
                        horizon: int, seeds: tuple[int, ...]) -> list[float]:
    def outcome(scene: str, delay: int, seed: int) -> int:
        matches = [
            r for r in rows
            if r["task_key"] == task_key
            and r["scene_condition"] == scene
            and int(r["configured_n_action_steps"]) == horizon
            and int(r["added_delay_ms"]) == delay
            and int(r["seed"]) == seed
            and (scene == "id" or r["candidate_key"] == candidate_key)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected 1 row for {task_key}/{candidate_key}/h{horizon}/"
                f"s{seed}/{scene}/d{delay}; got {len(matches)}"
            )
        return int(matches[0]["success"])

    return [
        (outcome("ood", 200, s) - outcome("ood", 0, s))
        - (outcome("id", 200, s) - outcome("id", 0, s))
        for s in seeds
    ]


def _candidate_task(candidate_key: str) -> str:
    for c in CANDIDATES:
        if c["candidate_key"] == candidate_key:
            return c["task_key"]
    raise KeyError(candidate_key)


def main() -> int:
    os.environ["MPLBACKEND"] = "Agg"
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--allow-incomplete", action="store_true")
    p.add_argument("--bootstrap-replicates", type=int, default=10_000)
    p.add_argument("--bootstrap-seed", type=int, default=20260826)
    args = p.parse_args()

    all_rows = [r for r in read_csv(args.results) if r.get("status", "").startswith("ok")]

    result_seeds = {int(r["seed"]) for r in all_rows}
    if result_seeds & _OLD_SEEDS:
        raise ValueError("Results contain forbidden old Stage 3/3B seeds (14-21)")

    if len(all_rows) != 3456 and not args.allow_incomplete:
        raise ValueError(f"Refusing incomplete analysis: {len(all_rows)}/3456 valid rows")

    unique = {r["run_id"]: r for r in all_rows}
    if len(unique) != len(all_rows) and not args.allow_incomplete:
        raise ValueError("Duplicate run_ids would bias analysis")

    rows         = list(unique.values())
    seeds_present = tuple(sorted({int(r["seed"]) for r in rows}))

    args.output_dir.mkdir(parents=True, exist_ok=True)

    four_cell_records:   list[dict] = []
    interaction_records: list[dict] = []
    bootstrap_records:   list[dict] = []

    for candidate in CANDIDATES:
        task_key      = candidate["task_key"]
        candidate_key = candidate["candidate_key"]
        a_status      = candidate["analysis_status"]

        for h in HORIZONS:
            cells: dict = {}
            for scene in ("id", "ood"):
                for delay in (0, 200):
                    cell = [
                        r for r in rows
                        if r["task_key"] == task_key
                        and r["scene_condition"] == scene
                        and int(r["configured_n_action_steps"]) == h
                        and int(r["added_delay_ms"]) == delay
                        and (scene == "id" or r["candidate_key"] == candidate_key)
                    ]
                    k = sum(int(r["success"]) for r in cell)
                    lo, hi = _wilson(k, len(cell))
                    cells[(scene, delay)] = (cell, k, lo, hi)

            rec: dict = {
                "candidate_key": candidate_key,
                "task_key": task_key,
                "analysis_status": a_status,
                "configured_n_action_steps": h,
            }
            for scene, label in (("id", "id"), ("ood", "ood")):
                for delay, dlabel in ((0, "native"), (200, "plus_200")):
                    cell, k, lo, hi = cells[(scene, delay)]
                    n = len(cell)
                    rec.update({
                        f"{label}_{dlabel}_successes": k,
                        f"{label}_{dlabel}_trials": n,
                        f"{label}_{dlabel}_rate": _rate(cell),
                        f"{label}_{dlabel}_wilson95_low": lo,
                        f"{label}_{dlabel}_wilson95_high": hi,
                    })
            four_cell_records.append(rec)

            try:
                paired = _interaction_values(rows, task_key, candidate_key, h, seeds_present)
            except ValueError:
                if args.allow_incomplete:
                    paired = []
                else:
                    raise

            I_h = (
                (rec["ood_plus_200_rate"] - rec["ood_native_rate"])
                - (rec["id_plus_200_rate"] - rec["id_native_rate"])
            )
            blo = bhi = float("nan")
            if paired:
                blo, bhi = _bootstrap_ci(paired, args.bootstrap_replicates, args.bootstrap_seed)

            i_rec = {
                "candidate_key": candidate_key,
                "task_key": task_key,
                "analysis_status": a_status,
                "configured_n_action_steps": h,
                "interaction_I_h": I_h,
                "paired_seed_mean": sum(paired) / len(paired) if paired else float("nan"),
                "paired_seed_values": ";".join(map(str, paired)),
                "paired_bootstrap95_low": blo,
                "paired_bootstrap95_high": bhi,
                "n_seeds": len(paired),
                "bootstrap_replicates": args.bootstrap_replicates,
                "bootstrap_rng_seed": args.bootstrap_seed,
            }
            interaction_records.append(i_rec)
            bootstrap_records.append({**i_rec, "shared_id_reference": True})

    write_csv(args.output_dir / "stage3_new_four_cell_by_candidate_horizon.csv",
              four_cell_records)
    write_csv(args.output_dir / "stage3_new_interaction_by_candidate_horizon.csv",
              interaction_records)
    write_csv(args.output_dir / "stage3_new_bootstrap_intervals.csv", bootstrap_records)

    # Cross-task object-layout contrasts.
    contrast_records: list[dict] = []
    ol_by_key = {
        r["candidate_key"]: r
        for r in interaction_records
        if r["candidate_key"] in _OBJECT_LAYOUT_KEYS
    }
    pairs = [
        ("long_stove_object_layout", "spatial_object_layout"),
        ("long_stove_object_layout", "goal_object_layout"),
        ("spatial_object_layout",    "goal_object_layout"),
    ]
    for h in HORIZONS:
        h_ol = {k: v for k, v in ol_by_key.items()
                if int(v["configured_n_action_steps"]) == h}
        for key_a, key_b in pairs:
            if key_a not in h_ol or key_b not in h_ol:
                continue
            ia = float(h_ol[key_a]["interaction_I_h"])
            ib = float(h_ol[key_b]["interaction_I_h"])
            blo = bhi = float("nan")
            diff_vals: list[float] = []
            try:
                vals_a = _interaction_values(
                    rows, _candidate_task(key_a), key_a, h, seeds_present)
                vals_b = _interaction_values(
                    rows, _candidate_task(key_b), key_b, h, seeds_present)
                diff_vals = [a - b for a, b in zip(vals_a, vals_b)]
                blo, bhi = _bootstrap_ci(diff_vals, args.bootstrap_replicates,
                                         args.bootstrap_seed)
            except (ValueError, KeyError):
                pass
            contrast_records.append({
                "candidate_a": key_a, "candidate_b": key_b,
                "configured_n_action_steps": h,
                "I_a": ia, "I_b": ib,
                "difference_I_a_minus_I_b": ia - ib,
                "paired_bootstrap95_low": blo,
                "paired_bootstrap95_high": bhi,
                "n_seeds": len(diff_vals),
            })
    write_csv(args.output_dir / "stage3_new_object_layout_cross_task_contrasts.csv",
              contrast_records)

    # Figures (matplotlib optional).
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = {
            "long_stove_object_layout":  "long_stove x obj_layout",
            "goal_robot_initial_state":  "goal x robot_state",
            "goal_light_conditions":     "goal x lighting",
            "goal_sensor_noise_posthoc": "goal x sensor_noise (post-hoc)",
            "spatial_object_layout":     "spatial x obj_layout",
            "goal_object_layout":        "goal x obj_layout",
        }
        prespec_keys = [c["candidate_key"] for c in CANDIDATES
                        if c["analysis_status"] == "prespecified_confirmatory"]

        fig, ax = plt.subplots(figsize=(8, 5))
        for key in prespec_keys:
            subset = sorted(
                [r for r in interaction_records if r["candidate_key"] == key],
                key=lambda r: int(r["configured_n_action_steps"]),
            )
            if subset:
                ax.plot(
                    [int(r["configured_n_action_steps"]) for r in subset],
                    [float(r["interaction_I_h"]) for r in subset],
                    marker="o", label=labels.get(key, key),
                )
        ax.axhline(0, color="black", linewidth=1)
        ax.axvline(25, color="black", linestyle="--", alpha=0.4)
        ax.set(xlabel="Configured action coverage",
               ylabel="OOD x delay interaction I_h",
               title=f"Stage 3 New — prespecified interactions (n={len(seeds_present)} seeds)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(
            args.output_dir / "stage3_new_interaction_vs_horizon_prespecified.png", dpi=180)
        plt.close(fig)

        # Object-layout cross-task bar chart at h=25.
        ol_keys = list(_OBJECT_LAYOUT_KEYS)
        h25_ol  = {r["candidate_key"]: r for r in interaction_records
                   if r["candidate_key"] in ol_keys
                   and int(r["configured_n_action_steps"]) == 25}
        if h25_ol:
            fig, ax = plt.subplots(figsize=(6, 4))
            xs  = range(len(ol_keys))
            ys  = [float(h25_ol[k]["interaction_I_h"]) if k in h25_ol else float("nan")
                   for k in ol_keys]
            los = [float(h25_ol[k]["paired_bootstrap95_low"]) if k in h25_ol else float("nan")
                   for k in ol_keys]
            his = [float(h25_ol[k]["paired_bootstrap95_high"]) if k in h25_ol else float("nan")
                   for k in ol_keys]
            ax.bar(xs, ys, color="steelblue", alpha=0.7)
            for x, lo, hi in zip(xs, los, his):
                if not math.isnan(lo):
                    ax.plot([x, x], [lo, hi], color="black", linewidth=2)
            ax.axhline(0, color="black", linewidth=1)
            ax.set_xticks(list(xs))
            ax.set_xticklabels([labels.get(k, k) for k in ol_keys],
                               fontsize=8, rotation=15)
            ax.set(ylabel="Interaction I_25",
                   title=f"Stage 3 New — object-layout cross-task (h=25, n={len(seeds_present)})")
            fig.tight_layout()
            fig.savefig(args.output_dir / "stage3_new_object_layout_cross_task.png", dpi=180)
            plt.close(fig)
    except ImportError:
        pass

    # Observations markdown.
    h25 = [r for r in interaction_records if int(r["configured_n_action_steps"]) == 25]
    lines = [
        "# Stage 3 New — High-Power Replication Observations",
        "",
        f"- Completed: {len(rows)}/3456 valid episodes.",
        f"- Fresh seeds: {min(seeds_present)}..{max(seeds_present)} "
        f"({len(seeds_present)} seeds per cell).",
        "- Old Stage 3/3B seeds (14-21) excluded from all estimates.",
        f"- Bootstrap: {args.bootstrap_replicates:,} replicates, "
        f"RNG seed {args.bootstrap_seed}.",
        "",
        "## h=25 primary results",
        "",
    ]
    for r in sorted(h25, key=lambda x: x["candidate_key"]):
        lines.append(
            f"- **{r['candidate_key']}** ({r['analysis_status']}): "
            f"I_25={float(r['interaction_I_h']):+.3f}, "
            f"bootstrap 95% CI [{float(r['paired_bootstrap95_low']):+.3f}, "
            f"{float(r['paired_bootstrap95_high']):+.3f}]."
        )
    lines += ["", "## Object-layout cross-task contrasts (h=25)", ""]
    for r in [r for r in contrast_records if int(r["configured_n_action_steps"]) == 25]:
        lines.append(
            f"- {r['candidate_a']} − {r['candidate_b']}: "
            f"diff={float(r['difference_I_a_minus_I_b']):+.3f}, "
            f"95% CI [{float(r['paired_bootstrap95_low']):+.3f}, "
            f"{float(r['paired_bootstrap95_high']):+.3f}]."
        )
    lines += [
        "", "## Guardrails", "",
        "- Stage 3/3B rows (seeds 14-21) were NOT pooled into these estimates.",
        "- Sensor noise remains labeled `posthoc_replication`.",
        "- Coverage selection (Stage 2) did not alter the frozen horizon set.",
    ]
    (args.output_dir / "STAGE_3_NEW_OBSERVATIONS.md").write_text(
        "\n".join(lines) + "\n")

    print(f"PASS: Stage 3 New analysis complete -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
