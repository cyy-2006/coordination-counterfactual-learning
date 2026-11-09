"""Merge checkpointed coordination JSONL files and remove duplicate variants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def result_key(row: dict) -> tuple:
    return (
        row["demo"],
        row["variant"],
        row.get("arm"),
        int(row.get("delay_steps", 0)),
        int(row.get("onset_step", 0)),
    )


def demo_index(name: str) -> int:
    try:
        return int(name.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 10**12


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-demos", type=int)
    parser.add_argument("--expected-variants-per-demo", type=int)
    args = parser.parse_args()

    unique: dict[tuple, dict] = {}
    duplicates = 0
    for path in args.inputs:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            key = result_key(row)
            if key in unique:
                duplicates += 1
                if unique[key] != row:
                    raise ValueError(f"conflicting duplicate result: {key}")
            else:
                unique[key] = row

    rows = sorted(
        unique.values(),
        key=lambda row: (
            demo_index(row["demo"]),
            0 if row["variant"] == "baseline" else 1,
            row.get("onset_fraction", 0.0),
            row.get("delay_steps", 0),
            row.get("arm") or "",
        ),
    )
    demos = {row["demo"] for row in rows}
    counts = {demo: sum(row["demo"] == demo for row in rows) for demo in demos}
    if args.expected_demos is not None and len(demos) != args.expected_demos:
        raise ValueError(f"expected {args.expected_demos} demos, found {len(demos)}")
    if args.expected_variants_per_demo is not None:
        incomplete = {demo: count for demo, count in counts.items() if count != args.expected_variants_per_demo}
        if incomplete:
            raise ValueError(f"incomplete demos: {incomplete}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "inputs": [str(path) for path in args.inputs],
                "output": str(args.output),
                "rows": len(rows),
                "demos": len(demos),
                "duplicates_removed": duplicates,
                "min_rows_per_demo": min(counts.values()),
                "max_rows_per_demo": max(counts.values()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
