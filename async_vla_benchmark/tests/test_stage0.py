"""Stage 0 manifest and `d*` selection-rule tests.

The selection rule is the one piece of Stage 0 with real branching logic, and it
runs once on data that costs ~6 GPU-hours to produce. These tests pin it against
the thresholds in `docs/STAGE_0_LATENCY_CALIBRATION.md` section 8 so a later edit
cannot quietly move the operating point.
"""

from async_vla_benchmark.benchmark.stage0 import (
    ADDED_DELAYS_MS,
    EXECUTION_METHODS,
    SEEDS,
    STAGE0_TASKS,
    CalibrationRow,
    cell_viability,
    latency_profile_name,
    select_high_delay,
    selection_payload,
    stage0_manifest,
)


#: The selection rule works on pooled rates, so it does not care how many seeds
#: production runs with. These fixtures keep two seeds because the thresholds are
#: easiest to read against small denominators; the production count lives in
#: `SEEDS` and is asserted by the manifest tests below.
TEST_SEEDS: tuple[int, ...] = (0, 1)


def rows_from(
    spec: dict[tuple[str, str], dict[int, int]],
    seeds: tuple[int, ...] = TEST_SEEDS,
) -> list[CalibrationRow]:
    """Build rows from {(task, method): {delay: successes_out_of_len(seeds)}}."""
    out = []
    for (task, method), by_delay in spec.items():
        for delay, successes in by_delay.items():
            for index, seed in enumerate(seeds):
                out.append(
                    CalibrationRow(
                        task_key=task,
                        execution_method=method,
                        added_delay_ms=delay,
                        seed=seed,
                        success=index < successes,
                    )
                )
    return out


def flat(successes_by_delay: dict[int, int], cells=(("a", "naive_async"), ("b", "rtc"))):
    return rows_from({cell: dict(successes_by_delay) for cell in cells})


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


def test_manifest_is_the_full_180_episode_grid():
    # The literal is the point: it fails if a frozen constant moves without the
    # matching DECISIONS/spec amendment (D002/D007/D014, STAGE_0 sections 4-5).
    plans = stage0_manifest()
    assert len(plans) == 180
    assert len(plans) == (
        len(STAGE0_TASKS) * len(EXECUTION_METHODS) * len(ADDED_DELAYS_MS) * len(SEEDS)
    )
    assert len({p.run_id for p in plans}) == 180


def test_calibration_seeds_avoid_the_stage_2_held_out_range():
    # STAGE_2 section 4 reserves seeds 2-9 for held-out confirmation; calibrating
    # d* on one of them would weaken that claim two stages downstream.
    assert SEEDS[:2] == (0, 1), "Stage 1 reuses the first two seeds as ID controls"
    assert not set(SEEDS) & set(range(2, 10))


def test_manifest_covers_every_cell_at_every_delay():
    plans = stage0_manifest()
    for task in STAGE0_TASKS:
        for method in EXECUTION_METHODS:
            for delay in ADDED_DELAYS_MS:
                matching = [
                    p
                    for p in plans
                    if p.task_key == task.task_key
                    and p.execution_method == method
                    and p.added_delay_ms == delay
                ]
                assert len(matching) == len(SEEDS)


def test_native_subset_is_thirty_six_episodes():
    # The smoke test that gates the remaining 144.
    assert len([p for p in stage0_manifest() if p.added_delay_ms == 0]) == 36


def test_delay_grid_stops_below_the_rtc_chunk_ceiling():
    # RTC discards the leading delay_steps actions of each chunk, so its queue
    # starves once total latency passes half the raw chunk (25 steps / 1250 ms for
    # pi05's 50-action chunk) at any horizon. With RTC inference measured at
    # ~660-735 ms, delays above ~500 ms only re-measure starvation (D007, STAGE_0
    # section 4.1).
    assert max(ADDED_DELAYS_MS) <= 500


def test_profile_names_match_config_keys_and_never_use_ideal():
    # "ideal" zeroes total latency in LatencyProfile; Native must not map to it.
    assert latency_profile_name(0) == "native"
    assert latency_profile_name(300) == "native_plus_300"
    assert all(latency_profile_name(d) != "ideal" for d in ADDED_DELAYS_MS)


# --------------------------------------------------------------------------
# Viability (section 8.1)
# --------------------------------------------------------------------------


def test_cell_is_viable_at_one_of_two_native_successes():
    rows = rows_from({("a", "rtc"): {0: 1}})
    assert cell_viability(rows)[0].viable is True


def test_cell_at_native_floor_is_not_viable():
    rows = rows_from({("a", "rtc"): {0: 0}})
    assert cell_viability(rows)[0].viable is False


def test_floor_cells_do_not_drag_the_pooled_curve():
    # A dead cell contributes zeros at every delay. If it were pooled in, the
    # drop from Native would shrink and d* would drift later.
    rows = rows_from(
        {
            ("live", "rtc"): {0: 2, 100: 2, 200: 1},
            ("dead", "rtc"): {0: 0, 100: 0, 200: 0},
        }
    )
    result = select_high_delay(rows)
    assert result.viable_cells == (("live", "rtc"),)
    native = next(p for p in result.curve if p.added_delay_ms == 0)
    assert (native.successes, native.episodes) == (2, 2)


# --------------------------------------------------------------------------
# Primary rule (section 8.3)
# --------------------------------------------------------------------------


def test_picks_smallest_delay_meeting_both_thresholds():
    # Native 4/4. 100ms: 4/4 (no drop). 200ms: 2/4 (drop .50, retain .50) -> d*.
    # 300ms would also qualify but is larger, and the rule takes the smallest.
    rows = flat({0: 2, 100: 2, 200: 1, 300: 1, 400: 0})
    result = select_high_delay(rows)
    assert result.selected_delay_ms == 200
    assert result.rule_applied == "primary"
    assert result.success_drop == 0.5


def test_delay_with_a_big_drop_but_below_floor_is_rejected():
    # 100ms drops to 0/4: a 100% drop, but nothing survives, so it is saturated
    # rather than informative. Falls through to the fallbacks.
    rows = flat({0: 2, 100: 0, 200: 0, 300: 0, 400: 0})
    result = select_high_delay(rows)
    assert result.rule_applied != "primary"
    assert result.calibration_saturated is True


def test_delay_that_retains_success_but_barely_drops_is_rejected():
    rows = flat({0: 2, 100: 2, 200: 2, 300: 2, 400: 2})
    result = select_high_delay(rows)
    assert result.rule_applied != "primary"
    assert result.calibration_weak is True


FOUR_CELLS = (
    ("a", "naive_async"),
    ("a", "rtc"),
    ("b", "naive_async"),
    ("b", "rtc"),
)


def test_primary_rule_requires_two_viable_cells():
    rows = rows_from({("only", "rtc"): {0: 2, 100: 2, 200: 1, 300: 1}})
    result = select_high_delay(rows)
    assert result.insufficient_viable_cells is True
    assert result.rule_applied != "primary"


# --------------------------------------------------------------------------
# Fallbacks (section 8.4)
# --------------------------------------------------------------------------


def test_fallback_1_takes_largest_drop_among_survivors():
    # Four cells x 2 seeds = 8 episodes per level, so a sub-threshold drop is
    # representable: 7/8 is a 0.125 drop, under the 0.20 the primary rule needs.
    # Only the last level moves at all, so fallback 1 must land there.
    rows = rows_from(
        {
            cell: {0: 2, 100: 2, 200: 2, 300: 2, 400: 2}
            for cell in FOUR_CELLS
        }
    )
    last = max(ADDED_DELAYS_MS)
    rows = [
        r
        for r in rows
        if not (r.added_delay_ms == last and r.cell == FOUR_CELLS[0] and r.seed == 1)
    ] + [CalibrationRow(*FOUR_CELLS[0], last, 1, success=False)]
    result = select_high_delay(rows)
    assert result.rule_applied == "fallback_1_largest_drop"
    assert result.selected_delay_ms == last


def test_fallback_1_breaks_ties_toward_the_smaller_delay():
    rows = flat({0: 2, 100: 1, 200: 1, 300: 1, 400: 1})
    result = select_high_delay(rows)
    # Every candidate ties at a 0.5 drop; the earliest one wins. This satisfies
    # the primary rule too, which is the correct outcome.
    assert result.selected_delay_ms == 100


def test_fallback_2_flags_saturation_and_takes_the_smallest_qualifying_delay():
    rows = flat({0: 2, 100: 0, 200: 0, 300: 0, 400: 0})
    result = select_high_delay(rows)
    assert result.rule_applied == "fallback_2_saturated"
    assert result.selected_delay_ms == 100
    assert result.calibration_saturated is True
    assert result.calibration_weak is False


def test_flat_curve_is_flagged_weak_even_though_fallback_1_claims_it():
    # Section 8.4 orders fallback 1 ahead of fallback 3, so a curve where delay
    # does nothing is still "selected" by fallback 1. The flag has to come from
    # the curve, or the one result that most invalidates Stage 1 goes unlabelled.
    rows = flat({d: 2 for d in ADDED_DELAYS_MS})
    result = select_high_delay(rows)
    assert result.rule_applied == "fallback_1_largest_drop"
    assert result.calibration_weak is True
    assert result.success_drop == 0.0


def test_no_valid_nonzero_delay_yields_no_selection():
    rows = rows_from({("a", "rtc"): {0: 2}, ("b", "rtc"): {0: 2}})
    result = select_high_delay(rows)
    assert result.selected_delay_ms is None
    assert result.rule_applied == "none"


# --------------------------------------------------------------------------
# Hygiene
# --------------------------------------------------------------------------


def test_invalid_episodes_are_excluded_from_selection():
    rows = flat({0: 2, 100: 2, 200: 1, 300: 1, 400: 0})
    poisoned = rows + [
        CalibrationRow("a", "naive_async", 200, seed, success=True, status="invalid")
        for seed in range(20)
    ]
    assert select_high_delay(poisoned).selected_delay_ms == 200


def test_payload_always_declares_ood_was_not_used():
    result = select_high_delay(flat({0: 2, 100: 2, 200: 1, 300: 1}))
    payload = selection_payload(result)
    assert payload["selection_used_ood_results"] is False
    assert payload["low_added_delay_ms"] == 0
    assert payload["high_added_delay_ms"] == result.selected_delay_ms
    assert set(payload) >= {
        "low_added_delay_ms",
        "high_added_delay_ms",
        "selection_used_ood_results",
        "calibration_saturated",
        "calibration_weak",
    }
