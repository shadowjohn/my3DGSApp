#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, NamedTuple


class RegisteredFrames(NamedTuple):
    count: int
    invalid: bool


class FrameQualityReport(NamedTuple):
    summary: dict[str, int] | None
    invalid: bool


def count_registered_frames(transforms_json: Path) -> RegisteredFrames:
    if not transforms_json.is_file():
        return RegisteredFrames(0, False)
    try:
        data = json.loads(transforms_json.read_text())
    except json.JSONDecodeError:
        return RegisteredFrames(0, True)
    if not isinstance(data, dict):
        return RegisteredFrames(0, True)
    frames = data.get("frames", [])
    if not isinstance(frames, list):
        return RegisteredFrames(0, True)
    return RegisteredFrames(len(frames), False)


def load_frame_quality(job_dir: Path) -> FrameQualityReport:
    frame_quality_path = job_dir / "frame_quality_report.json"
    if not frame_quality_path.is_file():
        return FrameQualityReport(None, False)
    try:
        data = json.loads(frame_quality_path.read_text())
        if not isinstance(data, dict):
            return FrameQualityReport(None, True)
        summary = {
            "candidate_count": int(data["candidate_count"]),
            "selected_count": int(data["selected_count"]),
            "candidate_fps": int(data["candidate_fps"]),
            "target_fps": int(data["target_fps"]),
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return FrameQualityReport(None, True)
    return FrameQualityReport(summary, False)


def load_sfm_report(processed_dir: Path) -> dict[str, Any] | None:
    sfm_path = processed_dir / "sfm_report.json"
    if not sfm_path.is_file():
        return None
    try:
        data = json.loads(sfm_path.read_text())
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    summary: dict[str, Any] = {}
    for key in [
        "mapper",
        "matcher",
        "registered_count",
        "registered_ratio",
        "sparse_model_path",
    ]:
        if key in data:
            summary[key] = data[key]
    return summary or None


def splat_count_from_ply(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with path.open("rb") as ply_file:
            for raw_line in ply_file:
                line = raw_line.decode("ascii", errors="ignore").strip()
                parts = line.split()
                if len(parts) == 3 and parts[:2] == ["element", "vertex"]:
                    return int(parts[2])
                if line == "end_header":
                    return 0
    except (OSError, ValueError):
        return 0
    return 0


def quality_grade(
    registered_ratio: float, frame_count: int, viewer_ready: bool
) -> tuple[str, str]:
    if not viewer_ready or frame_count < 8:
        return ("D", "retake_recommended")
    if registered_ratio >= 0.9:
        return ("A", "excellent")
    if registered_ratio >= 0.8:
        return ("B", "good")
    if registered_ratio >= 0.65:
        return ("C", "usable_with_caution")
    return ("D", "retake_recommended")


def build_report(
    job_id: str,
    images_dir: Path,
    processed_dir: Path,
    exports_dir: Path,
    has_transform: bool,
) -> dict[str, Any]:
    frame_quality = load_frame_quality(images_dir.parent)
    frame_count = len(list(images_dir.glob("*.jpg"))) + len(list(images_dir.glob("*.png")))
    registered_frames = count_registered_frames(processed_dir / "transforms.json")
    registered_count = registered_frames.count
    ratio = round(registered_count / frame_count, 2) if frame_count else 0.0
    splat_path = exports_dir / "splat.ply"
    splat_size_mb = (
        round(splat_path.stat().st_size / 1024 / 1024, 2)
        if splat_path.is_file()
        else 0.0
    )
    viewer_ready = splat_path.is_file()
    grade, label = quality_grade(ratio, frame_count, viewer_ready)

    warnings: list[str] = []
    if frame_count < 8:
        warnings.append("frame_count lower than 8")
    if ratio < 0.8:
        warnings.append("registered_ratio lower than 0.8")
    if not splat_path.is_file():
        warnings.append("splat.ply missing")
    if splat_size_mb > 300:
        warnings.append("splat file larger than 300MB")
    if not has_transform:
        warnings.append("transform.json missing")
    if registered_frames.invalid:
        warnings.append("transforms.json invalid")
    if frame_quality.invalid:
        warnings.append("frame_quality_report.json invalid")
    if frame_quality.summary is not None and frame_quality.summary["selected_count"] < 60:
        warnings.append("selected frame count lower than 60")

    report = {
        "job_id": job_id,
        "frame_count": frame_count,
        "registered_frame_count": registered_count,
        "registered_count": registered_count,
        "registered_ratio": ratio,
        "splat_count": splat_count_from_ply(splat_path),
        "splat_file_size_mb": splat_size_mb,
        "has_transform": has_transform,
        "viewer_ready": viewer_ready,
        "outlier_ratio": None,
        "largest_component_ratio": None,
        "quality_grade": grade,
        "quality_label": label,
        "warnings": warnings,
    }
    if frame_quality.summary is not None:
        report["frame_quality"] = frame_quality.summary
    sfm_report = load_sfm_report(processed_dir)
    if sfm_report is not None:
        report["sfm"] = sfm_report
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaussian Splat QA report.")
    parser.add_argument("job_id")
    parser.add_argument("job_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.job_id,
        args.job_dir / "images",
        args.job_dir / "processed",
        args.job_dir / "exports",
        (args.job_dir / "transform.json").is_file(),
    )
    output = args.job_dir / "qa_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
