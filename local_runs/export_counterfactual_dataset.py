"""Execute selected timing interventions and export robomimic-style HDF5 data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import h5py
import numpy as np
import robosuite

import dexmimicgen  # noqa: F401
from coordination_pipeline import (
    decode_json_attr,
    delay_suffix,
    make_env,
    reset_to_demo,
    settle_actions,
    task_distance,
    validate_action_layout,
)


def demo_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)$", name)
    return (int(match.group(1)) if match else 10**12, name)


def numeric_observation(observation: dict, env) -> dict[str, np.ndarray]:
    result = {}
    for key, value in observation.items():
        array = np.asarray(value)
        if array.dtype.kind in "biuf" and not key.endswith("_image") and not key.endswith("_depth"):
            result[key] = array.copy()
    # DexMimicGen's TwoArmThreading environment does not register task-object
    # observables, despite use_object_obs=True. Add the minimum Markov task
    # state explicitly so a state policy can observe the needle and target.
    if hasattr(env, "obj_body_id") and {"needle", "tripod"}.issubset(env.obj_body_id):
        needle_body = env.obj_body_id["needle"]
        tripod_body = env.obj_body_id["tripod"]
        needle_geom = np.asarray(
            env.sim.data.geom_xpos[env.sim.model.geom_name2id("needle_obj_needle")]
        ).copy()
        ring_center = np.mean(
            [
                np.asarray(
                    env.sim.data.geom_xpos[
                        env.sim.model.geom_name2id(f"tripod_obj_ring_{index}")
                    ]
                )
                for index in range(env.tripod.num_ring_geoms)
            ],
            axis=0,
        )
        result["task_object_pos"] = np.concatenate(
            [env.sim.data.body_xpos[needle_body], env.sim.data.body_xpos[tripod_body]]
        ).copy()
        result["task_object_quat"] = np.concatenate(
            [env.sim.data.body_xquat[needle_body], env.sim.data.body_xquat[tripod_body]]
        ).copy()
        result["task_needle_ring_vector"] = (needle_geom - ring_center).copy()
        result["task_needle_ring_distance"] = np.asarray(
            [np.linalg.norm(needle_geom - ring_center)], dtype=np.float64
        )
    return result


def execute_and_record(env, model_xml, initial_state, ep_meta, actions, settle_steps):
    reset_to_demo(env, model_xml, initial_state, ep_meta)
    observation = env._get_observations(force_update=True)
    states, observations, next_observations = [], [], []
    rewards, dones, contacts, distances = [], [], [], []
    success_steps = []

    for step, action in enumerate(actions):
        states.append(env.sim.get_state().flatten().copy())
        observations.append(numeric_observation(observation, env))
        observation, reward, _, _ = env.step(action)
        next_observations.append(numeric_observation(observation, env))
        rewards.append(float(reward))
        dones.append(False)
        contacts.append(int(env.sim.data.ncon))
        distance = task_distance(env)
        if distance is not None:
            distances.append(distance)
        if env._check_success():
            success_steps.append(step)
    if dones:
        dones[-1] = True

    success_before_settle = bool(env._check_success())
    for action in settle_actions(actions[-1], settle_steps):
        env.step(action)
    success_after_settle = bool(env._check_success())
    return {
        "states": np.asarray(states),
        "actions": np.asarray(actions),
        "obs": observations,
        "next_obs": next_observations,
        "rewards": np.asarray(rewards, dtype=np.float32),
        "dones": np.asarray(dones, dtype=np.uint8),
        "success_any": bool(success_steps),
        "success_before_settle": success_before_settle,
        "success_after_settle": success_after_settle,
        "first_success_step": int(success_steps[0]) if success_steps else None,
        "min_task_distance": float(np.min(distances)) if distances else None,
        "final_task_distance": float(distances[-1]) if distances else None,
        "mean_contacts": float(np.mean(contacts)) if contacts else 0.0,
    }


def stack_observations(records: list[dict[str, np.ndarray]], key: str) -> np.ndarray:
    return np.stack([record[key] for record in records], axis=0)


def should_keep(record: dict, mode: str, hard_distance: float) -> tuple[bool, str]:
    if record["success_after_settle"]:
        return mode in {"stable", "stable_and_hard", "all"}, "stable_positive"
    hard = record["min_task_distance"] is not None and record["min_task_distance"] <= hard_distance
    if hard:
        return mode in {"hard", "stable_and_hard", "all"}, "hard_negative"
    return mode == "all", "invalid_negative"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--demo-start", type=int, default=0)
    parser.add_argument("--max-demos", type=int, default=10)
    parser.add_argument(
        "--demo-names",
        nargs="*",
        default=[],
        help="exact source demo names (for example demo_3 demo_8); overrides demo-start/max-demos",
    )
    parser.add_argument("--arms", nargs="+", choices=["left", "right"], default=["left", "right"])
    parser.add_argument("--delays", type=int, nargs="*", default=[])
    parser.add_argument("--onsets", type=float, nargs="*", default=[])
    parser.add_argument(
        "--condition",
        action="append",
        default=[],
        metavar="ARM:DELAY:ONSET",
        help="repeatable exact intervention; avoids the Cartesian arms/delays/onsets grid",
    )
    parser.add_argument("--settle-steps", type=int, default=10)
    parser.add_argument("--keep", choices=["stable", "hard", "stable_and_hard", "all"], default="stable_and_hard")
    parser.add_argument("--hard-distance", type=float, default=0.015)
    parser.add_argument("--include-baseline", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"output exists: {args.output}; pass --overwrite to replace it")
    conditions = []
    for specification in args.condition:
        try:
            arm, delay_text, onset_text = specification.split(":")
            delay = int(delay_text)
            onset = float(onset_text)
        except ValueError as error:
            raise SystemExit(f"invalid --condition {specification!r}; expected ARM:DELAY:ONSET") from error
        if arm not in {"left", "right"} or delay < 0 or not 0.0 <= onset <= 1.0:
            raise SystemExit(f"invalid --condition {specification!r}")
        conditions.append((arm, delay, onset))
    if args.condition and (args.delays or args.onsets):
        raise SystemExit("use either repeated --condition or the arms/delays/onsets grid, not both")
    if any(not 0.0 <= onset <= 1.0 for onset in args.onsets):
        raise SystemExit("onsets must be fractions in [0, 1]")
    if args.baseline_only:
        args.include_baseline = True
    if not args.include_baseline and not conditions and (not args.delays or not args.onsets):
        raise SystemExit("provide --include-baseline or at least one --delays and --onsets value")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(args.dataset, "r") as source:
        source_data = source["data"]
        meta = decode_json_attr(source_data.attrs["env_args"])
        available_demos = sorted(source_data.keys(), key=demo_sort_key)
        if args.demo_names:
            missing = sorted(set(args.demo_names) - set(available_demos))
            if missing:
                raise SystemExit(f"source demos not found: {missing}")
            demos = list(dict.fromkeys(args.demo_names))
        else:
            demos = available_demos[args.demo_start : args.demo_start + args.max_demos]
        env = make_env(meta)
        written = 0
        total_samples = 0
        groups_by_label: dict[str, list[str]] = {
            "stable_positive": [],
            "hard_negative": [],
            "invalid_negative": [],
        }
        groups_by_role: dict[str, list[str]] = {
            "source_only": [],
            "counterfactual_positive": [],
            "coordination_supervision": [],
        }
        try:
            with h5py.File(args.output, "w") as target:
                data = target.create_group("data")
                data.attrs["env_args"] = json.dumps(meta)
                data.attrs["source_dataset"] = str(args.dataset.resolve())
                data.attrs["intervention"] = "action-complete suffix delay"
                data.attrs["source_demo_names"] = json.dumps(demos)
                for demo_name in demos:
                    source_demo = source_data[demo_name]
                    validate_action_layout(source_demo)
                    source_actions = source_demo["actions"][...]
                    initial_state = source_demo["states"][0]
                    model_xml = source_demo.attrs["model_file"]
                    if isinstance(model_xml, bytes):
                        model_xml = model_xml.decode("utf-8")
                    ep_meta = decode_json_attr(source_demo.attrs["ep_meta"]) if "ep_meta" in source_demo.attrs else None
                    variants = []
                    if args.include_baseline:
                        variants.append(("baseline", None, 0, 0, 0.0, source_actions.copy()))
                    if not args.baseline_only:
                        selected_conditions = conditions or [
                            (arm, delay, onset_fraction)
                            for onset_fraction in args.onsets
                            for delay in args.delays
                            for arm in args.arms
                        ]
                        for arm, delay, onset_fraction in selected_conditions:
                            onset_step = min(len(source_actions), int(round(onset_fraction * len(source_actions))))
                            variants.append(
                                (
                                    "suffix_delay",
                                    arm,
                                    delay,
                                    onset_step,
                                    onset_fraction,
                                    delay_suffix(source_actions, arm, delay, onset_step),
                                )
                            )

                    for variant, arm, delay, onset_step, onset_fraction, actions in variants:
                        record = execute_and_record(
                            env, model_xml, initial_state, ep_meta, actions, args.settle_steps
                        )
                        keep, label = should_keep(record, args.keep, args.hard_distance)
                        print(
                            json.dumps(
                                {
                                    "demo": demo_name,
                                    "arm": arm,
                                    "delay": delay,
                                    "onset": onset_fraction,
                                    "label": label,
                                    "kept": keep,
                                    "success_after_settle": record["success_after_settle"],
                                    "min_task_distance": record["min_task_distance"],
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        if not keep:
                            continue
                        group_name = f"demo_{written}"
                        group = data.create_group(group_name)
                        group.create_dataset("states", data=record["states"], compression="gzip")
                        group.create_dataset("actions", data=record["actions"], compression="gzip")
                        group.create_dataset("rewards", data=record["rewards"])
                        group.create_dataset("dones", data=record["dones"])
                        obs_group = group.create_group("obs")
                        next_obs_group = group.create_group("next_obs")
                        for key in sorted(record["obs"][0]):
                            obs_group.create_dataset(key, data=stack_observations(record["obs"], key), compression="gzip")
                            next_obs_group.create_dataset(
                                key, data=stack_observations(record["next_obs"], key), compression="gzip"
                            )
                        group.attrs["model_file"] = model_xml
                        if ep_meta is not None:
                            group.attrs["ep_meta"] = json.dumps(ep_meta)
                        group.attrs["source_demo"] = demo_name
                        group.attrs["num_samples"] = len(actions)
                        group.attrs["variant"] = variant
                        group.attrs["arm"] = arm or ""
                        group.attrs["delay_steps"] = delay
                        group.attrs["onset_step"] = onset_step
                        group.attrs["onset_fraction"] = onset_fraction
                        group.attrs["counterfactual_label"] = label
                        group.attrs["success_after_settle"] = record["success_after_settle"]
                        group.attrs["min_task_distance"] = (
                            record["min_task_distance"] if record["min_task_distance"] is not None else np.nan
                        )
                        total_samples += len(actions)
                        groups_by_label[label].append(group_name)
                        if label == "stable_positive" and variant == "baseline":
                            groups_by_role["source_only"].append(group_name)
                        if label == "stable_positive" and variant != "baseline":
                            groups_by_role["counterfactual_positive"].append(group_name)
                        if label in {"stable_positive", "hard_negative"}:
                            groups_by_role["coordination_supervision"].append(group_name)
                        written += 1
                data.attrs["total"] = total_samples
                data.attrs["num_demos"] = written
                mask = target.create_group("mask")
                string_dtype = h5py.string_dtype(encoding="utf-8")
                for label, group_names in groups_by_label.items():
                    mask.create_dataset(label, data=np.asarray(group_names, dtype=string_dtype))
                for role, group_names in groups_by_role.items():
                    mask.create_dataset(role, data=np.asarray(group_names, dtype=string_dtype))
                mask.create_dataset(
                    "behavior_cloning",
                    data=np.asarray(groups_by_label["stable_positive"], dtype=string_dtype),
                )
        finally:
            env.close()
    print(json.dumps({"output": str(args.output), "demos": written, "samples": total_samples}, indent=2))


if __name__ == "__main__":
    main()
