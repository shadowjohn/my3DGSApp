#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def frame_name(file_path: str | Path) -> str:
    return Path(file_path).name


def camera_position(transform_matrix: list[list[Any]]) -> list[float]:
    if not isinstance(transform_matrix, list) or len(transform_matrix) < 3:
        raise ValueError("transform_matrix must include at least three rows")
    for row in transform_matrix[:3]:
        if not isinstance(row, list) or len(row) < 4:
            raise ValueError("transform_matrix rows must include translation values")

    return [
        float(transform_matrix[0][3]),
        float(transform_matrix[1][3]),
        float(transform_matrix[2][3]),
    ]


def registered_map(transforms_path: Path) -> dict[str, list[float]]:
    data = json.loads(transforms_path.read_text())
    frames = data.get("frames", []) if isinstance(data, dict) else []
    registrations: dict[str, list[float]] = {}

    for frame in frames:
        if not isinstance(frame, dict):
            continue
        file_path = frame.get("file_path")
        transform_matrix = frame.get("transform_matrix")
        if not file_path or not transform_matrix:
            continue
        try:
            registrations[frame_name(file_path)] = camera_position(transform_matrix)
        except (IndexError, KeyError, TypeError, ValueError):
            continue

    return registrations


def camera_path_bounds(positions: list[list[float]]) -> dict[str, list[float]] | None:
    if not positions:
        return None

    axes = list(zip(*positions))
    return {
        "min": [float(min(axis)) for axis in axes],
        "max": [float(max(axis)) for axis in axes],
    }


def annotate_report(report_path: Path, transforms_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text())
    registrations = registered_map(transforms_path)
    selected = report.get("selected", [])
    if not isinstance(selected, list):
        selected = []
        report["selected"] = selected
    selected_rows = [
        row
        for row in selected
        if isinstance(row, dict) and isinstance(row.get("output_name"), str)
    ]
    registered_positions: list[list[float]] = []
    registered_count = 0

    for row in selected_rows:
        output_name = row.get("output_name")
        position = registrations.get(output_name)
        is_registered = position is not None
        row["colmap_registered"] = is_registered
        row["camera_position"] = position
        if is_registered:
            registered_count += 1
            registered_positions.append(position)

    selected_count = len(selected_rows)
    registered_ratio = round(registered_count / selected_count, 2) if selected_count else 0.0
    report["colmap"] = {
        "registered_count": registered_count,
        "registered_ratio": registered_ratio,
        "camera_path_bounds": camera_path_bounds(registered_positions),
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Annotate frame quality report with COLMAP registration results."
    )
    parser.add_argument("report_path", type=Path)
    parser.add_argument("transforms_path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    annotate_report(args.report_path, args.transforms_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
