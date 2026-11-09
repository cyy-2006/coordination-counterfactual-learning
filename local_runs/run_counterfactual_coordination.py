"""Minimal counterfactual coordination experiment for DexMimicGen trajectories."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import h5py
import numpy as np
import robosuite

# Registers DexMimicGen environments.
import dexmimicgen  # noqa: F401


def reset_to_demo(env, model_xml: str, initial_state: np.ndarray):
    env.reset()
    xml = env.edit_model_xml(model_xml)
    env.reset_from_xml_string(xml)
    env.sim.reset()
    env.sim.set_state_from_flattened(initial_state)
    env.sim.forward()
    if hasattr(env, "update_state"):
        env.update_state()


def hold_action(source: np.ndarray, arm_slice: slice, use_last: bool) -> np.ndarray:
    action = np.zeros(source.shape[1], dtype=source.dtype)
    reference = source[-1] if use_last else source[0]
    action[6] = reference[6]
    action[13] = reference[13]
    action[arm_slice.stop - 1] = reference[arm_slice.stop - 1]
    return action


def delayed_actions(actions: np.ndarray, delayed_arm: str | None, delay: int) -> np.ndarray:
    if delayed_arm is None or delay == 0:
        return actions.copy()
    if delayed_arm not in {"left", "right"}:
        raise ValueError(delayed_arm)
    # Official action_dict confirms flattened order: right arm first, left arm second.
    delayed_slice = slice(0, 7) if delayed_arm == "right" else slice(7, 14)
    other_slice = slice(7, 14) if delayed_arm == "right" else slice(0, 7)
    total = len(actions) + delay
    result = np.zeros((total, actions.shape[1]), dtype=actions.dtype)
    for t in range(total):
        result[t] = hold_action(actions, slice(0, 14), use_last=t >= len(actions))
        # The non-delayed arm follows the original trajectory, then holds its final pose command.
        if t < len(actions):
            result[t, other_slice] = actions[t, other_slice]
        else:
            result[t, other_slice] = 0.0
            result[t, other_slice.stop - 1] = actions[-1, other_slice.stop - 1]
        # The delayed arm waits, then executes its complete original trajectory.
        source_t = t - delay
        if 0 <= source_t < len(actions):
            result[t, delayed_slice] = actions[source_t, delayed_slice]
        else:
            result[t, delayed_slice] = 0.0
            grip_source = actions[0] if source_t < 0 else actions[-1]
            result[t, delayed_slice.stop - 1] = grip_source[delayed_slice.stop - 1]
    return result


def needle_ring_distance(env) -> float:
    needle = np.asarray(env.sim.data.geom_xpos[env.sim.model.geom_name2id("needle_obj_needle")])
    ring = np.zeros(3)
    for i in range(env.tripod.num_ring_geoms):
        ring += np.asarray(env.sim.data.geom_xpos[env.sim.model.geom_name2id(f"tripod_obj_ring_{i}")])
    ring /= env.tripod.num_ring_geoms
    return float(np.linalg.norm(needle - ring))


def run_variant(env, model_xml, initial_state, variant_actions, name, arm, delay):
    reset_to_demo(env, model_xml, initial_state)
    distances = [needle_ring_distance(env)]
    success_steps = []
    rewards = []
    for step, action in enumerate(variant_actions):
        _, reward, _, _ = env.step(action)
        rewards.append(float(reward))
        distances.append(needle_ring_distance(env))
        if env._check_success():
            success_steps.append(step)
    return {
        "variant": name,
        "delayed_arm": arm,
        "delay_steps": delay,
        "delay_seconds": delay / float(env.control_freq),
        "trajectory_steps": int(len(variant_actions)),
        "success_any": bool(success_steps),
        "success_final": bool(env._check_success()),
        "first_success_step": int(success_steps[0]) if success_steps else None,
        "min_needle_ring_distance": float(np.min(distances)),
        "final_needle_ring_distance": float(distances[-1]),
        "max_reward": float(np.max(rewards)) if rewards else 0.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--delays", type=int, nargs="+", default=[5, 10, 20, 30])
    parser.add_argument("--arms", nargs="+", choices=["left", "right"], default=["left", "right"])
    args = parser.parse_args()

    with h5py.File(args.dataset, "r") as f:
        data = f["data"]
        demo = data["demo_0"]
        env_meta = json.loads(data.attrs["env_args"])
        actions = demo["actions"][...]
        states = demo["states"][...]
        model_xml = demo.attrs["model_file"]

    env_kwargs = env_meta["env_kwargs"]
    env_kwargs.update(
        env_name=env_meta["env_name"],
        has_renderer=False,
        has_offscreen_renderer=False,
        use_camera_obs=False,
        ignore_done=True,
    )
    env_kwargs.pop("env_lang", None)
    env = robosuite.make(**env_kwargs)

    results = []
    baseline = delayed_actions(actions, None, 0)
    results.append(run_variant(env, model_xml, states[0], baseline, "baseline", None, 0))
    print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    for delay in args.delays:
        for arm in args.arms:
            variant = delayed_actions(actions, arm, delay)
            result = run_variant(env, model_xml, states[0], variant, f"delay_{arm}_{delay}", arm, delay)
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    env.close()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset": str(Path(args.dataset).resolve()),
        "environment": env_meta["env_name"],
        "action_shape": list(actions.shape),
        "control_frequency": env.control_freq,
        "intervention": "delay one complete 7D arm action stream while the other arm follows the original timing",
        "results": results,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {output}", flush=True)


if __name__ == "__main__":
    main()
