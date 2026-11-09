"""Minimal, deterministic DexMimicGen smoke test with offscreen capture."""

import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import robosuite
from robosuite import load_composite_controller_config

import dexmimicgen  # noqa: F401 - registers the custom environments


OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(7)
env = robosuite.make(
    env_name="TwoArmThreading",
    robots=["Panda", "Panda"],
    controller_configs=load_composite_controller_config(robot="Panda"),
    has_renderer=False,
    has_offscreen_renderer=True,
    ignore_done=True,
    use_camera_obs=True,
    camera_names="frontview",
    camera_heights=360,
    camera_widths=480,
    control_freq=20,
)

obs = env.reset()
image_key = next(key for key in obs if key.endswith("_image"))
frames = [np.flipud(obs[image_key])]
rewards = []

for step in range(240):
    action = rng.normal(0.0, 0.35, size=env.action_spec[0].shape)
    action = np.clip(action, env.action_spec[0], env.action_spec[1])
    obs, reward, done, info = env.step(action)
    rewards.append(float(reward))
    if step % 6 == 0:
        frames.append(np.flipud(obs[image_key]))

env.close()

imageio.imwrite(OUT / "dexmimicgen_two_arm_threading_first.png", frames[0])
imageio.imwrite(OUT / "dexmimicgen_two_arm_threading_last.png", frames[-1])
imageio.mimsave(
    OUT / "dexmimicgen_two_arm_threading.gif",
    frames,
    duration=0.10,
    loop=0,
)

summary = {
    "environment": "TwoArmThreading",
    "robots": ["Panda", "Panda"],
    "steps": 240,
    "action_dimension": int(env.action_spec[0].shape[0]),
    "camera_key": image_key,
    "captured_frames": len(frames),
    "reward_min": min(rewards),
    "reward_max": max(rewards),
    "reward_mean": float(np.mean(rewards)),
    "seed": 7,
}
(OUT / "dexmimicgen_smoke_test.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)
print(json.dumps(summary, indent=2))
