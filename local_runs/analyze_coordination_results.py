"""Aggregate JSONL output from coordination_pipeline.py into CSV and Markdown."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    """95% Wilson interval for a binomial proportion."""
    if n == 0:
        return None, None
    p = successes / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def render_heatmap(aggregates: list[dict], output: Path) -> None:
    rows = [row for row in aggregates if row["variant"] == "suffix_delay"]
    if not rows:
        return
    delays = sorted({int(row["delay_steps"]) for row in rows})
    onsets = sorted({float(row["onset_fraction"]) for row in rows})
    lookup = {(row["arm"], int(row["delay_steps"]), float(row["onset_fraction"])): row for row in rows}
    cell_w, cell_h = 76, 58
    left_margin, top_margin, panel_gap = 82, 76, 90
    panel_w = cell_w * len(delays)
    width = left_margin + 2 * panel_w + panel_gap + 30
    height = top_margin + cell_h * len(onsets) + 65
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#222}.title{font-size:17px;font-weight:700}.axis{font-size:13px}.cell{font-size:12px;font-weight:600}</style>',
        f'<text x="{width / 2}" y="24" text-anchor="middle" class="title">Paired failure rate after stability hold</text>',
    ]
    for panel_index, arm in enumerate(("left", "right")):
        x0 = left_margin + panel_index * (panel_w + panel_gap)
        parts.append(f'<text x="{x0 + panel_w / 2}" y="50" text-anchor="middle" class="title">{arm.capitalize()} arm delayed</text>')
        for col, delay in enumerate(delays):
            x = x0 + col * cell_w
            parts.append(f'<text x="{x + cell_w / 2}" y="{top_margin - 8}" text-anchor="middle" class="axis">{delay}</text>')
        for row_index, onset in enumerate(onsets):
            y = top_margin + row_index * cell_h
            if panel_index == 0:
                parts.append(f'<text x="{left_margin - 12}" y="{y + cell_h / 2 + 4}" text-anchor="end" class="axis">{onset:.2f}</text>')
            for col, delay in enumerate(delays):
                x = x0 + col * cell_w
                item = lookup.get((arm, delay, onset))
                rate = item.get("paired_failure_rate") if item else None
                eligible = int(item.get("baseline_successful_n", 0)) if item else 0
                if rate is None:
                    fill, label = "#eeeeee", "-"
                else:
                    red = int(245 - 55 * rate)
                    green = int(245 - 175 * rate)
                    blue = int(245 - 185 * rate)
                    fill = f"rgb({red},{green},{blue})"
                    label = f"{rate:.0%} (n={eligible})"
                parts.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cell_w - 2}" height="{cell_h - 2}" fill="{fill}" stroke="#ffffff"/>')
                parts.append(f'<text x="{x + cell_w / 2}" y="{y + cell_h / 2 + 4}" text-anchor="middle" class="cell">{html.escape(label)}</text>')
    parts.append(f'<text x="{left_margin + panel_w}" y="{height - 12}" text-anchor="middle" class="axis">Delay steps</text>')
    parts.append(f'<text x="18" y="{top_margin + cell_h * len(onsets) / 2}" transform="rotate(-90 18 {top_margin + cell_h * len(onsets) / 2})" text-anchor="middle" class="axis">Onset fraction</text>')
    parts.append("</svg>")
    output.write_text("\n".join(parts), encoding="utf-8")


def render_heatmap_png(aggregates: list[dict], output: Path) -> None:
    rows = [row for row in aggregates if row["variant"] == "suffix_delay"]
    if not rows:
        return
    delays = sorted({int(row["delay_steps"]) for row in rows})
    onsets = sorted({float(row["onset_fraction"]) for row in rows})
    lookup = {(row["arm"], int(row["delay_steps"]), float(row["onset_fraction"])): row for row in rows}
    cell_w, cell_h = 110, 72
    left_margin, top_margin, panel_gap = 100, 100, 85
    panel_w = cell_w * len(delays)
    width = left_margin + 2 * panel_w + panel_gap + 30
    height = top_margin + cell_h * len(onsets) + 75
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    def centered_text(x: float, y: float, label: str, fill="black") -> None:
        box = draw.textbbox((0, 0), label, font=font)
        draw.text((x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2), label, fill=fill, font=font)

    centered_text(width / 2, 22, "Paired failure rate after stability hold")
    for panel_index, arm in enumerate(("left", "right")):
        x0 = left_margin + panel_index * (panel_w + panel_gap)
        centered_text(x0 + panel_w / 2, 53, f"{arm.capitalize()} arm delayed")
        for col, delay in enumerate(delays):
            centered_text(x0 + col * cell_w + cell_w / 2, top_margin - 20, str(delay))
        for row_index, onset in enumerate(onsets):
            y = top_margin + row_index * cell_h
            if panel_index == 0:
                centered_text(left_margin - 35, y + cell_h / 2, f"{onset:.2f}")
            for col, delay in enumerate(delays):
                x = x0 + col * cell_w
                item = lookup.get((arm, delay, onset))
                rate = item.get("paired_failure_rate") if item else None
                eligible = int(item.get("baseline_successful_n", 0)) if item else 0
                if rate is None:
                    color, label = (238, 238, 238), "-"
                else:
                    color = (
                        int(245 - 55 * rate),
                        int(245 - 175 * rate),
                        int(245 - 185 * rate),
                    )
                    label = f"{rate:.0%} (n={eligible})"
                draw.rectangle((x + 1, y + 1, x + cell_w - 2, y + cell_h - 2), fill=color, outline="white")
                centered_text(x + cell_w / 2, y + cell_h / 2, label)
    centered_text(left_margin + panel_w, height - 22, "Delay steps")
    image.save(output)


def write_latex_table(aggregates: list[dict], output: Path, min_eligible: int) -> None:
    candidates = [
        row for row in aggregates
        if row["variant"] == "suffix_delay"
        and row["paired_failure_rate"] is not None
        and row["baseline_successful_n"] >= min_eligible
    ]
    candidates.sort(key=lambda row: (-row["paired_failure_rate"], row["arm"], row["delay_steps"], row["onset_fraction"]))
    lines = [
        "% Auto-generated by analyze_coordination_results.py",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "手臂 & 延迟步数 & 起点比例 & 稳定基线 $n$ & 配对失败率（95\\% CI） \\\\",
        "\\midrule",
    ]
    for row in candidates[:12]:
        low, high = row["paired_failure_ci_low"], row["paired_failure_ci_high"]
        lines.append(
            f"{row['arm']} & {row['delay_steps']} & {row['onset_fraction']:.2f} & "
            f"{row['baseline_successful_n']} & {row['paired_failure_rate']:.1%} "
            f"[{low:.1%}, {high:.1%}] \\\\"
        )
    if not candidates:
        lines.append(f"\\multicolumn{{5}}{{c}}{{有效稳定基线数尚未达到 {min_eligible}}} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--min-eligible", type=int, default=10)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("input contains no results")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw_csv = args.output_dir / "coordination_results.csv"
    columns = sorted({key for row in rows for key in row})
    with raw_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    baseline_by_demo = {row["demo"]: row for row in rows if row["variant"] == "baseline"}
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["variant"], row.get("arm"), row.get("delay_steps", 0), row.get("onset_fraction", 0.0))].append(row)

    aggregates = []
    for key, group in sorted(grouped.items(), key=lambda item: str(item[0])):
        variant, arm, delay, onset = key
        n = len(group)
        eligible = [row for row in group if baseline_by_demo.get(row["demo"], {}).get("success_after_settle", False)]
        paired_rate = (
            sum(bool(row["success_after_settle"]) for row in eligible) / len(eligible) if eligible else None
        )
        stable_successes = sum(bool(row["success_after_settle"]) for row in group)
        stable_ci = wilson_interval(stable_successes, n)
        paired_failures = sum(not bool(row["success_after_settle"]) for row in eligible)
        paired_failure_ci = wilson_interval(paired_failures, len(eligible))
        aggregates.append(
            {
                "variant": variant,
                "arm": arm or "-",
                "delay_steps": delay,
                "onset_fraction": onset,
                "n": n,
                "success_any_rate": sum(bool(row["success_any"]) for row in group) / n,
                "success_before_settle_rate": sum(bool(row["success_before_settle"]) for row in group) / n,
                "success_after_settle_rate": sum(bool(row["success_after_settle"]) for row in group) / n,
                "success_after_settle_ci_low": stable_ci[0],
                "success_after_settle_ci_high": stable_ci[1],
                "baseline_successful_n": len(eligible),
                "paired_success_rate": paired_rate,
                "paired_failure_rate": 1.0 - paired_rate if paired_rate is not None else None,
                "paired_failure_ci_low": paired_failure_ci[0],
                "paired_failure_ci_high": paired_failure_ci[1],
            }
        )

    aggregate_csv = args.output_dir / "coordination_aggregate.csv"
    with aggregate_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(aggregates[0]))
        writer.writeheader()
        writer.writerows(aggregates)

    report = [
        "# 双臂时序反事实实验汇总",
        "",
        f"- 轨迹结果数：{len(rows)}",
        f"- 示范数：{len({row['demo'] for row in rows})}",
        "- 核心指标：settle 后仍成功，避免把瞬时穿环误判为稳定执行。",
        "",
        "| 干预 | 手臂 | 延迟步数 | 起点比例 | n | 曾成功 | 稳定后成功 | 基线成功子集 n | 配对成功率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in aggregates:
        report.append(
            f"| {row['variant']} | {row['arm']} | {row['delay_steps']} | {row['onset_fraction']:.2f} | "
            f"{row['n']} | {row['success_any_rate']:.1%} | {row['success_after_settle_rate']:.1%} | "
            f"{row['baseline_successful_n']} | "
            f"{row['paired_success_rate']:.1%} |" if row["paired_success_rate"] is not None else
            f"{row['n']} | {row['success_any_rate']:.1%} | {row['success_after_settle_rate']:.1%} | 0 | - |"
        )
    report_path = args.output_dir / "coordination_report.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    heatmap_path = args.output_dir / "sensitivity_heatmap.svg"
    render_heatmap(aggregates, heatmap_path)
    heatmap_png_path = args.output_dir / "sensitivity_heatmap.png"
    render_heatmap_png(aggregates, heatmap_png_path)
    latex_path = args.output_dir / "screening_table.tex"
    write_latex_table(aggregates, latex_path, args.min_eligible)
    ranked = sorted(
        [row for row in aggregates if row["variant"] == "suffix_delay" and row["paired_failure_rate"] is not None],
        key=lambda row: (-row["paired_failure_rate"], -row["baseline_successful_n"]),
    )
    summary_path = args.output_dir / "screening_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "rows": len(rows),
                "demos": len({row["demo"] for row in rows}),
                "stable_baseline_demos": sum(bool(row["success_after_settle"]) for row in baseline_by_demo.values()),
                "top_conditions": ranked[:12],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"saved {raw_csv}, {aggregate_csv}, {report_path}, {heatmap_path}, "
        f"{heatmap_png_path}, {latex_path}, and {summary_path}"
    )


if __name__ == "__main__":
    main()
