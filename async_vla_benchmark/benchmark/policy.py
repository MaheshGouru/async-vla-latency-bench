"""Lazy π0.5 loading with mandatory checkpoint revision and CUDA checks."""

from typing import Any


def load_pi05_policy(checkpoint: str, revision: str, n_action_steps: int = 10) -> Any:
    if not revision:
        raise ValueError("checkpoint_revision must be pinned before loading the policy")
    try:
        import torch
        from lerobot.policies.pi05.modeling_pi05 import PI05Policy
    except ImportError as exc:
        raise RuntimeError("LeRobot π0.5 dependencies are not installed") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("the Days 1–3 benchmark requires a CUDA device")
    policy = PI05Policy.from_pretrained(checkpoint, revision=revision)
    policy.config.n_action_steps = n_action_steps
    return policy.to("cuda").eval()
