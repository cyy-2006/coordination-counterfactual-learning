"""Create reproducible robomimic BC configs from the validated smoke template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path("local_runs/configs/bc_counterfactual_smoke.json"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--filter-key", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--steps-per-epoch", type=int, default=50)
    parser.add_argument("--save-every", type=int, default=25)
    parser.add_argument("--rnn", action="store_true")
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--normalize-obs", action="store_true")
    parser.add_argument("--actor-empty", action="store_true")
    parser.add_argument("--full-proprio", action="store_true")
    parser.add_argument("--image-policy", action="store_true")
    args = parser.parse_args()

    config = json.loads(args.template.read_text(encoding="utf-8"))
    config["experiment"]["name"] = args.name
    config["experiment"]["epoch_every_n_steps"] = args.steps_per_epoch
    config["experiment"]["save"]["every_n_epochs"] = args.save_every
    config["train"]["data"] = args.dataset
    config["train"]["output_dir"] = args.result_dir
    config["train"]["hdf5_filter_key"] = args.filter_key
    config["train"]["hdf5_normalize_obs"] = args.normalize_obs
    config["train"]["num_epochs"] = args.epochs
    config["train"]["seed"] = args.seed
    config["train"]["batch_size"] = args.batch_size
    config["algo"]["rnn"]["enabled"] = args.rnn
    config["algo"]["rnn"]["hidden_dim"] = args.hidden_dim
    if args.actor_empty:
        config["algo"]["actor_layer_dims"] = []
    if args.full_proprio:
        keys = config["observation"]["modalities"]["obs"]["low_dim"]
        additions = [
            "robot0_joint_pos",
            "robot0_joint_vel",
            "robot0_gripper_qvel",
            "robot1_joint_pos",
            "robot1_joint_vel",
            "robot1_gripper_qvel",
        ]
        config["observation"]["modalities"]["obs"]["low_dim"] = keys + [
            key for key in additions if key not in keys
        ]
    if args.image_policy:
        config["train"]["hdf5_cache_mode"] = "low_dim"
        config["observation"]["modalities"]["obs"]["low_dim"] = [
            "robot0_eef_pos",
            "robot0_eef_quat",
            "robot0_gripper_qpos",
            "robot1_eef_pos",
            "robot1_eef_quat",
            "robot1_gripper_qpos",
        ]
        config["observation"]["modalities"]["obs"]["rgb"] = [
            "agentview_image",
            "robot0_eye_in_hand_image",
            "robot1_eye_in_hand_image",
        ]
        config["observation"]["encoder"]["rgb"] = {
            "core_class": "VisualCore",
            "core_kwargs": {
                "feature_dimension": 64,
                "flatten": True,
                "backbone_class": "ResNet18Conv",
                "backbone_kwargs": {"pretrained": False, "input_coord_conv": False},
                "pool_class": "SpatialSoftmax",
                "pool_kwargs": {
                    "num_kp": 32,
                    "learnable_temperature": False,
                    "temperature": 1.0,
                    "noise_std": 0.0,
                    "output_variance": False,
                },
            },
            "obs_randomizer_class": "CropRandomizer",
            "obs_randomizer_kwargs": {
                "crop_height": 76,
                "crop_width": 76,
                "num_crops": 1,
                "pos_enc": False,
            },
        }
    if args.rnn:
        config["train"]["seq_length"] = config["algo"]["rnn"]["horizon"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
