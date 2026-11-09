"""Render a side-by-side GIF of baseline and one suffix-delay intervention."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import imageio.v2 as imageio
import numpy as np
import robosuite

import dexmimicgen  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coordination_pipeline import decode_json_attr, delay_suffix, reset_to_demo, settle_actions  # noqa: E402


def render(env, model_xml, state, ep_meta, actions, image_key, frame_skip, settle_steps):
    reset_to_demo(env, model_xml, state, ep_meta)
    observation = env._get_observations(force_update=True)
    frames = [np.flipud(observation[image_key])]
    all_actions = np.concatenate([actions, settle_actions(actions[-1], settle_steps)], axis=0)
    for step, action in enumerate(all_actions):
        observation, _, _, _ = env.step(action)
        if step % frame_skip == 0 or step == len(all_actions) - 1:
            frames.append(np.flipud(observation[image_key]))
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--demo", default="demo_0")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--arm", choices=["left", "right"], default="left")
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--onset", type=float, default=0.5)
    parser.add_argument("--camera", default="frontview")
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--frame-skip", type=int, default=3)
    parser.add_argument("--settle-steps", type=int, default=20)
    args = parser.parse_args()

    with h5py.File(args.dataset, "r") as handle:
        data = handle["data"]
        meta = decode_json_attr(data.attrs["env_args"])
        demo = data[args.demo]
        actions = demo["actions"][...]
        state = demo["states"][0]
        model_xml = demo.attrs["model_file"]
        if isinstance(model_xml, bytes):
            model_xml = model_xml.decode("utf-8")
        ep_meta = decode_json_attr(demo.attrs["ep_meta"]) if "ep_meta" in demo.attrs else None

    kwargs = dict(meta["env_kwargs"])
    kwargs.update(
        env_name=meta["env_name"],
        has_renderer=False,
        has_offscreen_renderer=True,
        use_camera_obs=True,
        camera_names=args.camera,
        camera_widths=args.width,
        camera_heights=args.height,
        ignore_done=True,
    )
    kwargs.pop("env_lang", None)
    env = robosuite.make(**kwargs)
    try:
        image_key = f"{args.camera}_image"
        onset_step = int(round(args.onset * len(actions)))
        intervention = delay_suffix(actions, args.arm, args.delay, onset_step)
        baseline_frames = render(
            env, model_xml, state, ep_meta, actions, image_key, args.frame_skip, args.settle_steps
        )
        intervention_frames = render(
            env, model_xml, state, ep_meta, intervention, image_key, args.frame_skip, args.settle_steps
        )
    finally:
        env.close()

    count = max(len(baseline_frames), len(intervention_frames))
    baseline_frames.extend([baseline_frames[-1]] * (count - len(baseline_frames)))
    intervention_frames.extend([intervention_frames[-1]] * (count - len(intervention_frames)))
    comparison = [np.concatenate([left, right], axis=1) for left, right in zip(baseline_frames, intervention_frames)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(args.output, comparison, duration=args.frame_skip / 20.0, loop=0)
    metadata = {
        "left_panel": "baseline",
        "right_panel": f"{args.arm} arm suffix delayed by {args.delay} steps at {args.onset:.0%}",
        "frames": count,
        "camera": args.camera,
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
