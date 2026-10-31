#!/usr/bin/env bash
#
# Stage 0 follow-up: widen the calibration grid before freezing d*.
#
# Adds seeds 14-19 to the four viable cells, taking each pooled point from n=24
# to n=48. At n=24 the frozen rule reproduces its own d*=200 only about half the
# time, and 200 currently turns on a single episode -- which also happens to be
# the one episode below +400 ms that underran. d* is inherited by every later
# stage, so this is the cheapest place in the pipeline to buy that precision.
#
# Two strategies only, naive_async and rtc, exactly as EXECUTION_METHODS freezes
# them. Nothing here introduces a condition the Stage 1 factorial does not have.
#
# The separate question -- why naive_async is 0/6 at Native ID on
# spatial_transport and long_stove_moka -- needs no episodes at all. Run
#   python3 -m async_vla_benchmark.scripts.chunk_boundary_report
# against the 180 episodes already on disk. It is GPU-free and answers whether
# that floor is open-loop drift across the 25-step chunk or staleness within it.
# Do that first; if it comes back "horizon", the seeds below are calibrating a
# grid whose horizon is about to change.
#
# Re-runnable: both phases pass --resume, so a killed job costs one episode.
#
# BEFORE RUNNING: record the seed widening in docs/DECISIONS.md. Adding
# pre-specified seeds to an estimate is sound; adding them after seeing where d*
# landed is not, and only the timestamp on that entry tells the two apart.

set -uo pipefail

CONFIG="${CONFIG:-async_vla_benchmark/configs/stage0.yaml}"
CAL_DIR="${CAL_DIR:-outputs/stage0}"

# EXTRA_ARGS=--dry-run prints each phase's manifest and exits without touching a
# GPU. Worth doing once on the box before spending the hour.
IFS=' ' read -r -a EXTRA <<< "${EXTRA_ARGS:-}"

EXTRA_SEEDS=(--extra-seed 14 --extra-seed 15 --extra-seed 16
             --extra-seed 17 --extra-seed 18 --extra-seed 19)
ONLY_NEW=(--seed 14 --seed 15 --seed 16 --seed 17 --seed 18 --seed 19)

declare -a PHASE_NAMES PHASE_CODES

phase() {
    local name="$1"; shift
    echo ""
    echo "=================================================================="
    echo "  $name   ($(date -u +%H:%M:%SZ))"
    echo "=================================================================="
    python3 -m async_vla_benchmark.scripts.run_stage0 "$@" ${EXTRA[@]+"${EXTRA[@]}"}
    local rc=$?
    PHASE_NAMES+=("$name")
    PHASE_CODES+=("$rc")
    echo "--- $name exit=$rc ---"
}

# Seeds 14-19 on the viable cells only. goal_drawer is viable under both
# methods; spatial and long only under RTC. Not a task x method rectangle, so it
# takes two invocations. The floored naive cells are deliberately left at n=6 --
# 60 more episodes cannot move a cell that is already at zero, and the reason it
# is at zero is what chunk_boundary_report answers for free.
#
# Preflight runs on the first phase only; the second reuses the verified setup.
phase "A goal_drawer x both methods, seeds 14-19 (60 ep)" \
    --config "$CONFIG" --output-dir "$CAL_DIR" --resume \
    "${EXTRA_SEEDS[@]}" "${ONLY_NEW[@]}" --task goal_drawer

phase "B spatial+long x RTC, seeds 14-19 (60 ep)" \
    --config "$CONFIG" --output-dir "$CAL_DIR" --resume --skip-preflight \
    "${EXTRA_SEEDS[@]}" "${ONLY_NEW[@]}" --method rtc \
    --task spatial_transport --task long_stove_moka

echo ""
echo "=================================================================="
echo "  summary   ($(date -u +%H:%M:%SZ))"
echo "=================================================================="
for i in "${!PHASE_NAMES[@]}"; do
    # rc=1 means some episodes were recorded invalid, not that the phase died.
    printf '  exit=%-3s %s\n' "${PHASE_CODES[$i]}" "${PHASE_NAMES[$i]}"
done

echo ""
echo "next: re-select d* on the widened grid (nothing is overwritten until you run it)"
echo "  python3 -m async_vla_benchmark.scripts.validate_results --output-dir $CAL_DIR"
echo "  python3 -m async_vla_benchmark.scripts.select_high_delay \\"
echo "    --results $CAL_DIR/latency_calibration_episode_results.csv"
