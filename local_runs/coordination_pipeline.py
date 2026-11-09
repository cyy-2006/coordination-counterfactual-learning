"""Batch counterfactual timing experiments for DexMimicGen demonstrations.

The intervention delays a complete suffix of one arm's 7D action stream. No
demonstrated motion command is deleted, so the experiment changes relative
timing without conflating timing with a smaller end-to-end motion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import robosuite

import dexmimicgen  # noqa: F401 - registers DexMimicGen environments


ARM_SLICES = {"right": slice(0, 7), "left": slice(7, 14)}


def natural_demo_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)$", name)
    return (int(match.group(1)) if match else 10**12, name)


def decode_json_attr(value: Any) -> dict[str, Any]:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)


def inspect_dataset(path: Path, deep_verify: bool = False) -> dict[str, Any]:
    with h5py.File(path, "r") as handle:
        data = handle["data"]
        demos = sorted(data.keys(), key=natural_demo_key)
        if not demos:
            raise ValueError("dataset has no demonstrations")
        first = data[demos[0]]
        action_shape = tuple(first["actions"].shape)
        state_shape = tuple(first["states"].shape)
        contained_samples = sum(len(data[d]["actions"]) for d in demos)
        declared_total = int(data.attrs["total"]) if "total" in data.attrs else None
        if deep_verify:
            for demo_name in demos:
                demo = data[demo_name]
                if not {"actions", "states"}.issubset(demo.keys()):
                    raise ValueError(f"{demo_name} is missing actions or states")
                if len(demo["actions"]) != len(demo["states"]):
                    raise ValueError(f"{demo_name} has mismatched action and state lengths")
                # Touch the final chunks so corrupt object headers / truncated data fail now.
                if len(demo["actions"]):
                    _ = demo["actions"][-1]
                    _ = demo["states"][-1]
        meta = decode_json_attr(data.attrs["env_args"])
        return {
            "path": str(path.resolve()),
            "file_size_bytes": path.stat().st_size,
            "environment": meta["env_name"],
            "demonstrations": len(demos),
            "contained_samples": contained_samples,
            "declared_total_samples": declared_total,
            "deep_verified": deep_verify,
            "first_demo": demos[0],
            "first_action_shape": action_shape,
            "first_state_shape": state_shape,
            "has_action_dict": "action_dict" in first,
        }


def validate_action_layout(demo: h5py.Group) -> None:
    actions = demo["actions"]
    if actions.ndim != 2 or actions.shape[1] != 14:
        raise ValueError(f"expected flattened 14D dual-arm actions, got {actions.shape}")
    if "action_dict" not in demo:
        return
    action_dict = demo["action_dict"]
    keys = set(action_dict.keys())
    expected = {
        "right_rel_pos",
        "right_rel_rot_axis_angle",
        "right_gripper",
        "left_rel_pos",
        "left_rel_rot_axis_angle",
        "left_gripper",
    }
    if not expected.issubset(keys):
        raise ValueError("action_dict does not match the expected right-then-left dual-arm layout")
    # Confirm rather than assume the flattened layout used by this dataset.
    right = np.concatenate(
        [action_dict["right_rel_pos"][0], action_dict["right_rel_rot_axis_angle"][0], action_dict["right_gripper"][0]]
    )
    left = np.concatenate(
        [action_dict["left_rel_pos"][0], action_dict["left_rel_rot_axis_angle"][0], action_dict["left_gripper"][0]]
    )
    if not np.allclose(actions[0], np.concatenate([right, left]), atol=1e-6):
        raise ValueError("flattened actions are not ordered as right 7D followed by left 7D")


def make_env(meta: dict[str, Any]):
    kwargs = dict(meta["env_kwargs"])
    kwargs.update(
        env_name=meta["env_name"],
        has_renderer=False,
        has_offscreen_renderer=False,
        use_camera_obs=False,
        ignore_done=True,
    )
    kwargs.pop("env_lang", None)
    return robosuite.make(**kwargs)


def reset_to_demo(env, model_xml: str, initial_state: np.ndarray, ep_meta: dict[str, Any] | None):
    if ep_meta and hasattr(env, "set_ep_meta"):
        env.set_ep_meta(ep_meta)
    env.reset()
    xml = env.edit_model_xml(model_xml)
    env.reset_from_xml_string(xml)
    env.sim.reset()
    env.sim.set_state_from_flattened(initial_state)
    env.sim.forward()
    if hasattr(env, "update_state"):
        env.update_state()


def arm_hold(reference: np.ndarray, arm: str) -> np.ndarray:
    result = np.zeros(7, dtype=reference.dtype)
    result[6] = reference[ARM_SLICES[arm].stop - 1]
    return result


def delay_suffix(actions: np.ndarray, arm: str | None, delay: int, onset_step: int = 0) -> np.ndarray:
    """Delay one arm's suffix while preserving every demonstrated command once."""
    if arm is None or delay == 0:
        return actions.copy()
    if arm not in ARM_SLICES:
        raise ValueError(arm)
    if delay < 0 or not 0 <= onset_step <= len(actions):
        raise ValueError("invalid delay or onset")

    total = len(actions) + delay
    selected = ARM_SLICES[arm]
    other_arm = "left" if arm == "right" else "right"
    other = ARM_SLICES[other_arm]
    result = np.zeros((total, actions.shape[1]), dtype=actions.dtype)

    for t in range(total):
        # The other arm keeps its original clock and then holds its final gripper state.
        if t < len(actions):
            result[t, other] = actions[t, other]
        else:
            result[t, other] = arm_hold(actions[-1], other_arm)

        # Before onset, replay normally. During the inserted interval, hold. Then
        # replay the full original suffix, shifted but otherwise unchanged.
        if t < onset_step:
            source = t
        elif t < onset_step + delay:
            source = None
        else:
            source = t - delay
        if source is not None and source < len(actions):
            result[t, selected] = actions[source, selected]
        else:
            reference_index = max(0, min(onset_step - 1, len(actions) - 1))
            if source is not None and source >= len(actions):
                reference_index = len(actions) - 1
            result[t, selected] = arm_hold(actions[reference_index], arm)
    return result


def settle_actions(last_action: np.ndarray, steps: int) -> np.ndarray:
    if steps <= 0:
        return np.empty((0, last_action.shape[0]), dtype=last_action.dtype)
    hold = np.zeros_like(last_action)
    hold[6] = last_action[6]
    hold[13] = last_action[13]
    return np.repeat(hold[None], steps, axis=0)


def task_distance(env) -> float | None:
    try:
        needle = np.asarray(env.sim.data.geom_xpos[env.sim.model.geom_name2id("needle_obj_needle")])
        ring = np.mean(
            [
                np.asarray(env.sim.data.geom_xpos[env.sim.model.geom_name2id(f"tripod_obj_ring_{i}")])
                for i in range(env.tripod.num_ring_geoms)
            ],
            axis=0,
        )
        return float(np.linalg.norm(needle - ring))
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def evaluate(
    env,
    model_xml: str,
    initial_state: np.ndarray,
    ep_meta: dict[str, Any] | None,
    actions: np.ndarray,
    settle_steps: int,
) -> dict[str, Any]:
    reset_to_demo(env, model_xml, initial_state, ep_meta)
    distances: list[float] = []
    successes: list[int] = []
    rewards: list[float] = []
    contacts: list[int] = []
    initial_distance = task_distance(env)
    if initial_distance is not None:
        distances.append(initial_distance)

    for step, action in enumerate(actions):
        _, reward, _, _ = env.step(action)
        rewards.append(float(reward))
        contacts.append(int(env.sim.data.ncon))
        distance = task_distance(env)
        if distance is not None:
            distances.append(distance)
        if env._check_success():
            successes.append(step)

    success_before_settle = bool(env._check_success())
    for offset, action in enumerate(settle_actions(actions[-1], settle_steps)):
        env.step(action)
        contacts.append(int(env.sim.data.ncon))
        distance = task_distance(env)
        if distance is not None:
            distances.append(distance)
        if env._check_success():
            successes.append(len(actions) + offset)

    return {
        "trajectory_steps": int(len(actions)),
        "settle_steps": int(settle_steps),
        "success_any": bool(successes),
        "success_before_settle": success_before_settle,
        "success_after_settle": bool(env._check_success()),
        "first_success_step": int(successes[0]) if successes else None,
        "min_task_distance": float(np.min(distances)) if distances else None,
        "final_task_distance": float(distances[-1]) if distances else None,
        "max_reward": float(np.max(rewards)) if rewards else 0.0,
        "mean_contacts": float(np.mean(contacts)) if contacts else 0.0,
        "max_contacts": int(np.max(contacts)) if contacts else 0,
    }


def completed_keys(path: Path) -> set[tuple[Any, ...]]:
    keys: set[tuple[Any, ...]] = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        keys.add((row["demo"], row["variant"], row.get("arm"), row.get("delay_steps", 0), row.get("onset_step", 0)))
    return keys


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--deep-verify", action="store_true")
    parser.add_argument("--demo-start", type=int, default=0)
    parser.add_argument("--max-demos", type=int, default=10)
    parser.add_argument("--demo-names", nargs="*")
    parser.add_argument("--arms", nargs="+", choices=["left", "right"], default=["left", "right"])
    parser.add_argument("--delays", type=int, nargs="+", default=[2, 4, 6, 10])
    parser.add_argument("--onsets", type=float, nargs="+", default=[0.0, 0.25, 0.5, 0.75])
    parser.add_argument("--settle-steps", type=int, default=20)
    parser.add_argument("--no-resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = inspect_dataset(args.dataset, deep_verify=args.deep_verify)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if args.inspect_only:
        return
    if args.output is None:
        raise SystemExit("--output is required unless --inspect-only is used")
    if any(not 0.0 <= onset <= 1.0 for onset in args.onsets):
        raise SystemExit("all --onsets must be fractions in [0, 1]")

    if args.no_resume and args.output.exists():
        args.output.unlink()
    done = set() if args.no_resume else completed_keys(args.output)
    with h5py.File(args.dataset, "r") as handle:
        data = handle["data"]
        meta = decode_json_attr(data.attrs["env_args"])
        available = sorted(data.keys(), key=natural_demo_key)
        if args.demo_names:
            unknown = set(args.demo_names) - set(available)
            if unknown:
                raise ValueError(f"unknown demos: {sorted(unknown)}")
            demos = args.demo_names
        else:
            demos = available[args.demo_start : args.demo_start + args.max_demos]

        env = make_env(meta)
        try:
            for demo_name in demos:
                demo = data[demo_name]
                validate_action_layout(demo)
                actions = demo["actions"][...]
                initial_state = demo["states"][0]
                model_xml = demo.attrs["model_file"]
                if isinstance(model_xml, bytes):
                    model_xml = model_xml.decode("utf-8")
                ep_meta = decode_json_attr(demo.attrs["ep_meta"]) if "ep_meta" in demo.attrs else None

                variants: list[tuple[str, str | None, int, int, float]] = [("baseline", None, 0, 0, 0.0)]
                for onset_fraction in args.onsets:
                    onset_step = min(len(actions), int(round(onset_fraction * len(actions))))
                    for delay in args.delays:
                        if delay <= 0:
                            continue
                        for arm in args.arms:
                            variants.append(("suffix_delay", arm, delay, onset_step, onset_fraction))

                for variant, arm, delay, onset_step, onset_fraction in variants:
                    key = (demo_name, variant, arm, delay, onset_step)
                    if key in done:
                        continue
                    variant_actions = delay_suffix(actions, arm, delay, onset_step)
                    metrics = evaluate(env, model_xml, initial_state, ep_meta, variant_actions, args.settle_steps)
                    row = {
                        "schema_version": 1,
                        "dataset": str(args.dataset.resolve()),
                        "demo": demo_name,
                        "environment": meta["env_name"],
                        "control_frequency": float(env.control_freq),
                        "original_steps": int(len(actions)),
                        "variant": variant,
                        "arm": arm,
                        "delay_steps": delay,
                        "delay_seconds": delay / float(env.control_freq),
                        "onset_step": onset_step,
                        "onset_fraction": onset_fraction,
                        **metrics,
                    }
                    append_jsonl(args.output, row)
                    done.add(key)
                    print(json.dumps(row, ensure_ascii=False), flush=True)
        finally:
            env.close()

    print(f"saved checkpointed results to {args.output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
