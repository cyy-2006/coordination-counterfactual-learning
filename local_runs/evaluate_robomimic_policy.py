"""Closed-loop evaluation of a robomimic checkpoint on DexMimicGen demo resets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import h5py
import numpy as np
from robomimic.utils.file_utils import policy_from_checkpoint

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dexmimicgen  # noqa: F401,E402
from coordination_pipeline import (  # noqa: E402
    decode_json_attr,
    make_env,
    reset_to_demo,
    settle_actions,
    task_distance,
)
from export_counterfactual_dataset import numeric_observation  # noqa: E402


def demo_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)$", name)
    return (int(match.group(1)) if match else 10**12, name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--demo-start", type=int, default=0)
    parser.add_argument("--max-demos", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=300)
    parser.add_argument("--settle-steps", type=int, default=10)
    args = parser.parse_args()

    policy, _ = policy_from_checkpoint(ckpt_path=str(args.checkpoint), verbose=False)
    results = []
    with h5py.File(args.dataset, "r") as handle:
        data = handle["data"]
        meta = decode_json_attr(data.attrs["env_args"])
        demos = sorted(data.keys(), key=demo_sort_key)[args.demo_start : args.demo_start + args.max_demos]
        env = make_env(meta)
        try:
            for demo_name in demos:
                demo = data[demo_name]
                model_xml = demo.attrs["model_file"]
                if isinstance(model_xml, bytes):
                    model_xml = model_xml.decode("utf-8")
                ep_meta = decode_json_attr(demo.attrs["ep_meta"]) if "ep_meta" in demo.attrs else None
                reset_to_demo(env, model_xml, demo["states"][0], ep_meta)
                policy.start_episode()
                observation = env._get_observations(force_update=True)
                success_steps = []
                distances = []
                last_action = np.zeros(env.action_dim, dtype=np.float64)
                for step in range(args.horizon):
                    policy_obs = numeric_observation(observation, env)
                    action = np.asarray(policy(ob=policy_obs), dtype=np.float64)
                    action = np.clip(action, env.action_spec[0], env.action_spec[1])
                    observation, _, _, _ = env.step(action)
                    last_action = action
                    distance = task_distance(env)
                    if distance is not None:
                        distances.append(distance)
                    if env._check_success():
                        success_steps.append(step)
                success_before_settle = bool(env._check_success())
                for action in settle_actions(last_action, args.settle_steps):
                    env.step(action)
                row = {
                    "demo": demo_name,
                    "horizon": args.horizon,
                    "settle_steps": args.settle_steps,
                    "success_any": bool(success_steps),
                    "success_before_settle": success_before_settle,
                    "success_after_settle": bool(env._check_success()),
                    "first_success_step": success_steps[0] if success_steps else None,
                    "min_task_distance": float(np.min(distances)) if distances else None,
                    "final_task_distance": float(task_distance(env)),
                }
                results.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
        finally:
            env.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "checkpoint": str(args.checkpoint.resolve()),
        "dataset": str(args.dataset.resolve()),
        "num_demos": len(results),
        "success_any_rate": sum(row["success_any"] for row in results) / len(results),
        "success_after_settle_rate": sum(row["success_after_settle"] for row in results) / len(results),
        "results": results,
    }
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
