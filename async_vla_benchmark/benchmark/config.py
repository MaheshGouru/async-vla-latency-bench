"""Typed YAML configuration loader for the Days 1-3 benchmark."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LatencyProfileConfig:
    name: str
    use_measured_native_latency: bool
    added_latency_ms: float = 0.0


@dataclass
class TaskCandidateConfig:
    name: str
    suite: str
    task_ids: list[int]


@dataclass
class RTCConfig:
    enabled: bool
    execution_horizon: int
    max_guidance_weight: float
    prefix_attention_schedule: str
    request_threshold_actions: int


@dataclass
class BenchmarkConfig:
    repository: str
    repository_revision: str | None
    policy_checkpoint: str
    checkpoint_revision: str | None
    dataset_repo: str
    dataset_revision: str | None
    device: str
    mujoco_backend: str
    policy_n_action_steps: int
    control_mode: str
    eval_batch_size: int
    max_parallel_tasks: int
    seeds: list[int]
    task_candidates: list[TaskCandidateConfig]
    latency_profiles: list[LatencyProfileConfig]
    execution_horizons: list[int]
    rtc: RTCConfig
    obs_type: str = "pixels_agent_pos"
    camera_name: str = "agentview_image,robot0_eye_in_hand_image"
    observation_width: int = 224
    observation_height: int = 224
    visualization_width: int = 640
    visualization_height: int = 480
    init_states: bool = True
    episode_length: int | None = None
    num_steps_wait: int = 10
    max_episode_steps: int | None = None
    output_dir: Path = field(default_factory=lambda: Path("outputs"))
    selected_tasks_file: str = "outputs/summaries/selected_tasks.json"


def _as_list(value: Any) -> list[int]:
    if isinstance(value, list):
        return [int(v) for v in value]
    if isinstance(value, str):
        return [int(v.strip()) for v in value.split(",") if v.strip()]
    raise ValueError(f"expected list of ints, got {type(value)}")


def load_config(path: Path | str) -> BenchmarkConfig:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if raw is None:
        raise ValueError("empty config file")

    task_candidates = []
    for name, cfg in raw.get("task_candidates", {}).items():
        task_candidates.append(
            TaskCandidateConfig(
                name=name,
                suite=cfg["suite"],
                task_ids=_as_list(cfg["task_ids"]),
            )
        )

    latency_profiles = []
    for name, cfg in raw.get("latency_profiles", {}).items():
        latency_profiles.append(
            LatencyProfileConfig(
                name=name,
                use_measured_native_latency=cfg["use_measured_native_latency"],
                added_latency_ms=cfg.get("added_latency_ms", 0.0),
            )
        )

    rtc_raw = raw.get("rtc", {})
    rtc = RTCConfig(
        enabled=rtc_raw.get("enabled", True),
        execution_horizon=rtc_raw.get("execution_horizon", 10),
        max_guidance_weight=rtc_raw.get("max_guidance_weight", 10.0),
        prefix_attention_schedule=rtc_raw.get("prefix_attention_schedule", "EXP"),
        request_threshold_actions=rtc_raw.get("request_threshold_actions", 5),
    )

    return BenchmarkConfig(
        repository=raw.get("repository", "huggingface/lerobot"),
        repository_revision=raw.get("repository_revision"),
        policy_checkpoint=raw["policy_checkpoint"],
        checkpoint_revision=raw.get("checkpoint_revision"),
        dataset_repo=raw.get("dataset_repo", "HuggingFaceVLA/libero"),
        dataset_revision=raw.get("dataset_revision"),
        device=raw.get("device", "cuda"),
        mujoco_backend=raw.get("mujoco_backend", "egl"),
        policy_n_action_steps=raw.get("policy_n_action_steps", 10),
        control_mode=raw.get("control_mode", "relative"),
        eval_batch_size=raw.get("eval_batch_size", 1),
        max_parallel_tasks=raw.get("max_parallel_tasks", 1),
        seeds=_as_list(raw.get("seeds", [0, 1, 2, 3, 4])),
        task_candidates=task_candidates,
        latency_profiles=latency_profiles,
        execution_horizons=_as_list(raw.get("execution_horizons", [2, 5, 10])),
        rtc=rtc,
        obs_type=raw.get("obs_type", "pixels_agent_pos"),
        camera_name=raw.get("camera_name", "agentview_image,robot0_eye_in_hand_image"),
        observation_width=raw.get("observation_width", 224),
        observation_height=raw.get("observation_height", 224),
        visualization_width=raw.get("visualization_width", 640),
        visualization_height=raw.get("visualization_height", 480),
        init_states=raw.get("init_states", True),
        episode_length=raw.get("episode_length"),
        num_steps_wait=raw.get("num_steps_wait", 10),
        max_episode_steps=raw.get("max_episode_steps"),
        output_dir=Path(raw.get("output_dir", "outputs")),
        selected_tasks_file=raw.get("selected_tasks_file", "outputs/summaries/selected_tasks.json"),
    )
