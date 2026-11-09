"""Measure teacher-forced action error of a robomimic policy on recorded trajectories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
from robomimic.utils.file_utils import policy_from_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--filter-key", default="source_only")
    args = parser.parse_args()

    policy, _ = policy_from_checkpoint(ckpt_path=str(args.checkpoint), verbose=False)
    squared_errors = []
    zero_errors = []
    early_errors = []
    per_demo = []
    with h5py.File(args.dataset, "r") as handle:
        names = handle["mask"][args.filter_key][...]
        names = [name.decode("utf-8") if isinstance(name, bytes) else str(name) for name in names]
        for name in names:
            group = handle["data"][name]
            actions = group["actions"][...]
            obs_group = group["obs"]
            policy.start_episode()
            demo_errors = []
            for step, target in enumerate(actions):
                observation = {key: obs_group[key][step] for key in obs_group}
                prediction = np.asarray(policy(ob=observation))
                error = float(np.mean(np.square(prediction - target)))
                demo_errors.append(error)
                squared_errors.append(error)
                zero_errors.append(float(np.mean(np.square(target))))
                if step < 20:
                    early_errors.append(error)
            per_demo.append({"demo": name, "mse": float(np.mean(demo_errors))})

    result = {
        "num_demos": len(per_demo),
        "num_steps": len(squared_errors),
        "policy_mse": float(np.mean(squared_errors)),
        "zero_action_mse": float(np.mean(zero_errors)),
        "relative_to_zero": float(np.mean(squared_errors) / np.mean(zero_errors)),
        "first_20_steps_mse": float(np.mean(early_errors)),
        "per_demo": per_demo,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
