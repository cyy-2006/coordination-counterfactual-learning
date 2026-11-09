"""Create a lightweight robomimic HDF5 subset using external demo links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--demo-names", nargs="+", required=True)
    parser.add_argument("--mask-name", default="source_only")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"output exists: {args.output}; pass --overwrite to replace it")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    relative_source = Path("..") / Path("generated") / args.source.name

    with h5py.File(args.source, "r") as source:
        missing = sorted(set(args.demo_names) - set(source["data"].keys()))
        if missing:
            raise SystemExit(f"source demos not found: {missing}")
        total = sum(int(source["data"][name]["actions"].shape[0]) for name in args.demo_names)
        env_args = source["data"].attrs["env_args"]

    with h5py.File(args.output, "w") as target:
        data = target.create_group("data")
        data.attrs["env_args"] = env_args
        data.attrs["total"] = total
        data.attrs["source_dataset"] = str(args.source.resolve())
        data.attrs["source_demo_names"] = json.dumps(args.demo_names)
        for name in args.demo_names:
            data[name] = h5py.ExternalLink(str(relative_source).replace("\\", "/"), f"/data/{name}")
        mask = target.create_group("mask")
        mask.create_dataset(
            args.mask_name,
            data=np.asarray(args.demo_names, dtype=h5py.string_dtype(encoding="utf-8")),
        )
    print(json.dumps({"output": str(args.output), "demos": len(args.demo_names), "samples": total}, indent=2))


if __name__ == "__main__":
    main()
