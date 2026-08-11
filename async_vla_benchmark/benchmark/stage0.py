"""Stage 0 — ID-only latency calibration: manifest and `d*` selection rule.

Everything in this module is pure (no GPU, no LeRobot import) so the selection
rule can be unit-tested without a container. `scripts/run_stage0.py` produces the
episodes; `scripts/select_high_delay.py` applies the rule defined here.

Spec: `docs/STAGE_0_LATENCY_CALIBRATION.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Frozen design constants (STAGE_0 sections 3-5, DECISIONS D002/D003/D007/D009)
# ---------------------------------------------------------------------------

#: Added artificial delay in ms. `0` is "Native": measured inference latency is
#: still present, so this is not a zero-latency condition.
ADDED_DELAYS_MS: tuple[int, ...] = (0, 100, 200, 300, 400, 500, 600, 700)

#: Stage 0 calibrates the same two methods the Stage 1 factorial compares.
#: Blocking/ideal are historical context only (D003) and are not run here.
EXECUTION_METHODS: tuple[str, ...] = ("naive_async", "rtc")

#: Two fixed exploratory seeds, shared with Stage 1 so the Native and `d*`
#: episodes can be reused as Stage 1's ID controls (STAGE_0 section 5).
SEEDS: tuple[int, ...] = (0, 1)

#: n_action_steps=10 (D002); Stage 0 runs no horizon sweep.
FIXED_HORIZON: int = 10

# Selection thresholds (STAGE_0 section 8.3).
MIN_SUCCESS_DROP: float = 0.20
MIN_REMAINING_SUCCESS: float = 0.25
MIN_VIABLE_CELLS: int = 2
NATIVE_VIABILITY_THRESHOLD: float = 0.5
SATURATED_FALLBACK_DROP: float = 0.10


@dataclass(frozen=True)
class TaskSpec:
    task_key: str
    task_group: str
    suite: str
    task_id: int
    expected_task_name: str


#: The three base tasks Stage 1 will perturb (STAGE_0 section 3 / D004).
#: `expected_task_name` is asserted against the live suite before any episode
#: runs -- LIBERO's task API is zero-indexed and index != name is a real failure
#: mode that would silently invalidate every downstream number.
STAGE0_TASKS: tuple[TaskSpec, ...] = (
    TaskSpec(
        task_key="spatial_transport",
        task_group="single_stage_transport",
        suite="libero_spatial",
        task_id=2,
        expected_task_name=(
            "pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate"
        ),
    ),
    TaskSpec(
        task_key="goal_drawer",
        task_group="articulated_contact_rich",
        suite="libero_goal",
        task_id=0,
        expected_task_name="open_the_middle_drawer_of_the_cabinet",
    ),
    TaskSpec(
        task_key="long_stove_moka",
        task_group="multi_stage_sequential",
        suite="libero_10",
        task_id=2,
        expected_task_name="KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it",
    ),
)

TASKS_BY_KEY = {task.task_key: task for task in STAGE0_TASKS}

#: Human-facing labels required in generated outputs (STAGE_1 section 0A).
TASK_GROUP_DISPLAY = {
    "single_stage_transport": "Single-stage transport",
    "articulated_contact_rich": "Articulated/contact-rich",
    "multi_stage_sequential": "Multi-stage/sequential",
}

METHOD_DISPLAY = {"naive_async": "Naive async", "rtc": "RTC"}


def delay_display(added_delay_ms: int) -> str:
    return "Native" if added_delay_ms == 0 else f"Native + {added_delay_ms} ms"


def latency_profile_name(added_delay_ms: int) -> str:
    """Map an added delay onto a `latency_profiles` key in the YAML config.

    Never returns "ideal": `LatencyProfile.logical_latency_ms` special-cases that
    name to zero total latency, which is a different condition from Native.
    """
    if added_delay_ms < 0:
        raise ValueError("added_delay_ms cannot be negative")
    return "native" if added_delay_ms == 0 else f"native_plus_{added_delay_ms}"


@dataclass(frozen=True)
class Stage0Plan:
    task_key: str
    task_group: str
    suite: str
    task_id: int
    execution_method: str
    added_delay_ms: int
    seed: int

    @property
    def latency_profile(self) -> str:
        return latency_profile_name(self.added_delay_ms)

    @property
    def run_id(self) -> str:
        return (
            f"stage0__{self.task_key}__{self.execution_method}"
            f"__d{self.added_delay_ms}__s{self.seed}"
        )

    @property
    def cell(self) -> tuple[str, str]:
        """The task x method cell used for viability and pooling."""
        return (self.task_key, self.execution_method)


def stage0_manifest(
    tasks: Sequence[TaskSpec] = STAGE0_TASKS,
    methods: Sequence[str] = EXECUTION_METHODS,
    delays: Sequence[int] = ADDED_DELAYS_MS,
    seeds: Sequence[int] = SEEDS,
) -> list[Stage0Plan]:
    """Expand the 96-episode calibration manifest in a stable order.

    Ordered task -> method -> delay -> seed so that a partial run always
    completes whole task x method cells first, which is what viability is
    computed over.
    """
    plans = []
    for task in tasks:
        for method in methods:
            for delay in delays:
                for seed in seeds:
                    plans.append(
                        Stage0Plan(
                            task_key=task.task_key,
                            task_group=task.task_group,
                            suite=task.suite,
                            task_id=task.task_id,
                            execution_method=method,
                            added_delay_ms=delay,
                            seed=seed,
                        )
                    )
    return plans


# ---------------------------------------------------------------------------
# `d*` selection (STAGE_0 section 8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationRow:
    """The subset of a results row the selection rule is allowed to see.

    Deliberately narrow: the rule may not consult OOD outcomes, task identity
    beyond the cell, or any latency/freshness metric.
    """

    task_key: str
    execution_method: str
    added_delay_ms: int
    seed: int
    success: bool
    status: str = "ok"

    @property
    def cell(self) -> tuple[str, str]:
        return (self.task_key, self.execution_method)


@dataclass(frozen=True)
class CellViability:
    task_key: str
    execution_method: str
    native_successes: int
    native_episodes: int
    viable: bool

    @property
    def native_success_rate(self) -> float:
        if self.native_episodes == 0:
            return float("nan")
        return self.native_successes / self.native_episodes


@dataclass(frozen=True)
class DelayPoint:
    added_delay_ms: int
    successes: int
    episodes: int

    @property
    def success_rate(self) -> float:
        if self.episodes == 0:
            return float("nan")
        return self.successes / self.episodes


@dataclass(frozen=True)
class SelectionResult:
    selected_delay_ms: int | None
    rule_applied: str
    native_success: float
    selected_success: float | None
    success_drop: float | None
    viable_cells: tuple[tuple[str, str], ...]
    calibration_saturated: bool
    calibration_weak: bool
    insufficient_viable_cells: bool
    curve: tuple[DelayPoint, ...]
    notes: tuple[str, ...]


def _valid(rows: Iterable[CalibrationRow]) -> list[CalibrationRow]:
    return [row for row in rows if row.status == "ok"]


def cell_viability(rows: Iterable[CalibrationRow]) -> list[CellViability]:
    """Native success per task x method cell (STAGE_0 section 8.1).

    A cell is viable when Native success >= 1/2. Non-viable cells stay in every
    reported table but get no vote in choosing `d*`: a cell already at the floor
    cannot drop further, so including it would make delay look harmless.
    """
    rows = _valid(rows)
    cells = sorted({row.cell for row in rows})
    out = []
    for task_key, method in cells:
        native = [
            row
            for row in rows
            if row.cell == (task_key, method) and row.added_delay_ms == 0
        ]
        successes = sum(1 for row in native if row.success)
        rate = successes / len(native) if native else 0.0
        out.append(
            CellViability(
                task_key=task_key,
                execution_method=method,
                native_successes=successes,
                native_episodes=len(native),
                viable=bool(native) and rate >= NATIVE_VIABILITY_THRESHOLD,
            )
        )
    return out


def pooled_curve(
    rows: Iterable[CalibrationRow],
    viable_cells: Sequence[tuple[str, str]],
    delays: Sequence[int] = ADDED_DELAYS_MS,
) -> list[DelayPoint]:
    """Success pooled over viable cells and both seeds, per delay level."""
    rows = _valid(rows)
    allowed = set(viable_cells)
    points = []
    for delay in delays:
        subset = [
            row for row in rows if row.added_delay_ms == delay and row.cell in allowed
        ]
        points.append(
            DelayPoint(
                added_delay_ms=delay,
                successes=sum(1 for row in subset if row.success),
                episodes=len(subset),
            )
        )
    return points


def select_high_delay(rows: Iterable[CalibrationRow]) -> SelectionResult:
    """Apply the frozen `d*` rule (STAGE_0 sections 8.3-8.4).

    Primary: the *smallest* candidate delay that drops pooled success by at least
    20 points while leaving at least 25% success, with at least two viable cells
    contributing and at least one surviving success at that delay.

    The fallbacks exist so a saturated or flat curve still yields a defensible
    single number with a flag attached, rather than an ad-hoc judgment call made
    after the fact. The flags describe the calibration; they are never grounds
    for retuning against OOD outcomes.
    """
    rows = list(rows)
    viability = cell_viability(rows)
    viable = tuple(
        (cell.task_key, cell.execution_method) for cell in viability if cell.viable
    )
    notes: list[str] = []

    curve = tuple(pooled_curve(rows, viable))
    native_point = next((p for p in curve if p.added_delay_ms == 0), None)
    native_success = native_point.success_rate if native_point else float("nan")
    candidates = [p for p in curve if p.added_delay_ms > 0 and p.episodes > 0]

    insufficient = len(viable) < MIN_VIABLE_CELLS
    if insufficient:
        notes.append(
            f"only {len(viable)} viable task x method cell(s); "
            f"section 8.3 requires at least {MIN_VIABLE_CELLS}. "
            "d* below is not trustworthy -- investigate the harness before Stage 1."
        )

    if not candidates:
        notes.append("no valid episodes at any nonzero delay; cannot select d*.")
        return SelectionResult(
            selected_delay_ms=None,
            rule_applied="none",
            native_success=native_success,
            selected_success=None,
            success_drop=None,
            viable_cells=viable,
            calibration_saturated=False,
            calibration_weak=False,
            insufficient_viable_cells=insufficient,
            curve=curve,
            notes=tuple(notes),
        )

    # Flags describe the *curve*, not the branch that happened to fire.
    #
    # Section 8.4 orders the fallbacks so that fallback 1 ("any candidate retains
    # >= 25%") is tried before fallback 3 ("no candidate dropped even 10 points").
    # Taken literally that makes CALIBRATION_WEAK unreachable: a perfectly flat
    # curve retains 100% everywhere, so fallback 1 always claims it first and a
    # curve where delay does nothing would be reported as a clean selection.
    # That is the single most important case to flag -- it means Stage 1 cannot
    # resolve an interaction at all. We keep the spec's *selection* order intact
    # and derive the flags from the data instead, so d* is unchanged but a flat
    # or floored curve is always labelled.
    best_drop = max(native_success - p.success_rate for p in candidates)
    curve_saturated = not any(p.success_rate >= MIN_REMAINING_SUCCESS for p in candidates)
    curve_weak = best_drop < SATURATED_FALLBACK_DROP
    if curve_weak:
        notes.append(
            f"largest pooled drop across all delay levels is {best_drop:.3f} "
            f"(< {SATURATED_FALLBACK_DROP}); CALIBRATION_WEAK. Delay barely moves "
            "this policy at these levels, so a Stage 1 interaction is unlikely "
            "to be resolvable."
        )
    if curve_saturated:
        notes.append(
            f"no delay level retained >= {MIN_REMAINING_SUCCESS} pooled success; "
            "CALIBRATION_SATURATED. d* sits on a floor and Stage 1 OOD cells will "
            "likely be uninterpretable (K005)."
        )

    def finish(point: DelayPoint, rule: str):
        return SelectionResult(
            selected_delay_ms=point.added_delay_ms,
            rule_applied=rule,
            native_success=native_success,
            selected_success=point.success_rate,
            success_drop=native_success - point.success_rate,
            viable_cells=viable,
            calibration_saturated=curve_saturated,
            calibration_weak=curve_weak,
            insufficient_viable_cells=insufficient,
            curve=curve,
            notes=tuple(notes),
        )

    # Primary rule: smallest qualifying delay.
    for point in sorted(candidates, key=lambda p: p.added_delay_ms):
        drop = native_success - point.success_rate
        if (
            drop >= MIN_SUCCESS_DROP
            and point.success_rate >= MIN_REMAINING_SUCCESS
            and point.successes >= 1
            and not insufficient
        ):
            return finish(point, "primary")

    # Fallback 1: largest drop among candidates that still retain >= 25%.
    retained = [p for p in candidates if p.success_rate >= MIN_REMAINING_SUCCESS]
    if retained:
        best = min(
            retained,
            key=lambda p: (-(native_success - p.success_rate), p.added_delay_ms),
        )
        notes.append(
            "primary rule unsatisfied; used fallback 1 (largest drop retaining >=25%)."
        )
        return finish(best, "fallback_1_largest_drop")

    # Fallback 2: smallest delay with a >= 10-point drop.
    dropped = [
        p
        for p in sorted(candidates, key=lambda p: p.added_delay_ms)
        if native_success - p.success_rate >= SATURATED_FALLBACK_DROP
    ]
    if dropped:
        notes.append("every candidate fell below 25% success; used fallback 2.")
        return finish(dropped[0], "fallback_2_saturated")

    # Fallback 3: nothing retained 25% and nothing dropped 10 points.
    last = max(candidates, key=lambda p: p.added_delay_ms)
    notes.append("neither fallback 1 nor 2 applied; used fallback 3 (largest delay).")
    return finish(last, "fallback_3_weak")


def selection_payload(result: SelectionResult) -> dict:
    """The exact `selected_high_delay.json` contents (STAGE_0 section 8.5).

    The four spec-required keys come first; the rest are diagnostics so a reader
    can tell a clean primary-rule selection from a flagged fallback without
    re-deriving it from the CSV.
    """
    return {
        "low_added_delay_ms": 0,
        "high_added_delay_ms": result.selected_delay_ms,
        "selection_used_ood_results": False,
        "calibration_saturated": result.calibration_saturated,
        "calibration_weak": result.calibration_weak,
        "rule_applied": result.rule_applied,
        "insufficient_viable_cells": result.insufficient_viable_cells,
        "native_success_pooled": result.native_success,
        "selected_success_pooled": result.selected_success,
        "success_drop": result.success_drop,
        "viable_cells": [f"{task}:{method}" for task, method in result.viable_cells],
        "pooled_curve": [
            {
                "added_delay_ms": p.added_delay_ms,
                "successes": p.successes,
                "episodes": p.episodes,
                "success_rate": p.success_rate,
            }
            for p in result.curve
        ],
        "notes": list(result.notes),
    }
