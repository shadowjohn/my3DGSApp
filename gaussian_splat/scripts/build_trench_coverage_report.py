#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
from typing import Any


SPARSE_PHOTO_WARNING = "photo_set lower than 8 images"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def frame_position(frame: dict[str, Any]) -> tuple[float, float, float] | None:
    matrix = frame.get("transform_matrix")
    if not isinstance(matrix, list) or len(matrix) < 3:
        return None
    rows = matrix[:3]
    if any(not isinstance(row, (list, tuple)) or len(row) < 4 for row in rows):
        return None
    try:
        return (
            float(rows[0][3]),
            float(rows[1][3]),
            float(rows[2][3]),
        )
    except (TypeError, ValueError):
        return None


def camera_path_span(frames: list[Any]) -> float:
    positions = [
        position
        for frame in frames
        if isinstance(frame, dict)
        for position in [frame_position(frame)]
        if position is not None
    ]
    if len(positions) < 2:
        return 0.0

    max_distance = 0.0
    for index, first in enumerate(positions):
        for second in positions[index + 1 :]:
            distance = math.dist(first, second)
            max_distance = max(max_distance, distance)
    return round(max_distance, 2)


def selected_count_from_reports(
    frame_quality_report: dict[str, Any], input_manifest: dict[str, Any]
) -> int:
    selected_count = frame_quality_report.get("selected_count")
    if isinstance(selected_count, int) and not isinstance(selected_count, bool):
        return selected_count

    if input_manifest.get("input_mode") == "photo_set":
        photos = input_manifest.get("photos", [])
        return len(photos) if isinstance(photos, list) else 0

    return 0


def coverage_decision(
    selected_count: int, registered_ratio: float, warnings: list[str]
) -> str:
    if selected_count < 8 or registered_ratio < 0.3:
        return "retake"
    if registered_ratio < 0.65 or SPARSE_PHOTO_WARNING in warnings:
        return "supplemental_capture_needed"
    if registered_ratio < 0.8:
        return "review_needed"
    return "usable"


def build_coverage_report(job_dir: Path | str) -> dict[str, Any]:
    job_dir = Path(job_dir)
    input_manifest = load_json(job_dir / "input_manifest.json")
    frame_quality_report = load_json(job_dir / "frame_quality_report.json")
    transforms = load_json(job_dir / "processed" / "transforms.json")

    frames = transforms.get("frames", [])
    if not isinstance(frames, list):
        frames = []

    selected_count = selected_count_from_reports(frame_quality_report, input_manifest)
    registered_count = len(frames)
    registered_ratio = (
        round(registered_count / selected_count, 2) if selected_count > 0 else 0.0
    )

    warnings = input_manifest.get("warnings", [])
    warnings = [str(warning) for warning in warnings] if isinstance(warnings, list) else []
    if selected_count < 60:
        warnings.append("selected frame count lower than 60")
    if registered_ratio < 0.65:
        warnings.append("registered_ratio lower than 0.65")

    return {
        "input_mode": input_manifest.get("input_mode"),
        "candidate_count": frame_quality_report.get("candidate_count"),
        "selected_count": selected_count,
        "registered_count": registered_count,
        "registered_ratio": registered_ratio,
        "camera_path_span": camera_path_span(frames),
        "warnings": warnings,
        "coverage_decision": coverage_decision(
            selected_count, registered_ratio, warnings
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trench coverage report.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.job_dir / "trench_coverage_report.json"
    report = build_coverage_report(args.job_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
