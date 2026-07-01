#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np


@dataclass
class FrameMetrics:
    path: Path
    index: int
    timestamp: float
    sharpness: float
    gradient: float
    exposure: float
    clipping: float
    texture: float
    score: float = 0.0


def image_entropy(gray: np.ndarray) -> float:
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    total = float(hist.sum())
    if total <= 0:
        return 0.0

    probabilities = hist[hist > 0] / total
    return float(-(probabilities * np.log2(probabilities)).sum())


def compute_frame_metrics(path: Path, index: int, timestamp: float) -> FrameMetrics:
    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise FileNotFoundError(f"Could not read image: {path}")

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = float(laplacian.var())

    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient = float(np.mean(cv2.magnitude(sobel_x, sobel_y)))

    mean_intensity = float(gray.mean())
    exposure = float(max(0.0, 1.0 - abs(mean_intensity - 128.0) / 128.0))

    dark_ratio = float(np.mean(gray <= 5))
    bright_ratio = float(np.mean(gray >= 250))
    clipping = dark_ratio + bright_ratio

    return FrameMetrics(
        path=path,
        index=index,
        timestamp=timestamp,
        sharpness=sharpness,
        gradient=gradient,
        exposure=exposure,
        clipping=clipping,
        texture=image_entropy(gray),
    )


def zscore(values: list[float]) -> list[float]:
    if not values:
        return []

    array = np.asarray(values, dtype=np.float64)
    std = float(array.std())
    if std == 0.0:
        return [0.0 for _ in values]

    mean = float(array.mean())
    return [float((value - mean) / std) for value in array]


def normalize_scores(rows: list[FrameMetrics]) -> list[FrameMetrics]:
    sharpness_scores = zscore([row.sharpness for row in rows])
    gradient_scores = zscore([row.gradient for row in rows])
    texture_scores = zscore([row.texture for row in rows])

    scored_rows = []
    for row, sharpness, gradient, texture in zip(
        rows,
        sharpness_scores,
        gradient_scores,
        texture_scores,
    ):
        score = (
            sharpness * 0.55
            + gradient * 0.20
            + row.exposure * 0.15
            + texture * 0.10
            - row.clipping * 2.0
        )
        scored_rows.append(replace(row, score=score))

    return scored_rows


def select_best_frames(
    rows: list[FrameMetrics],
    target_fps: int,
    max_frames: int,
) -> list[FrameMetrics]:
    if target_fps <= 0:
        raise ValueError("target_fps must be positive")
    if max_frames <= 0:
        return []

    bucket_seconds = 1.0 / target_fps
    buckets: dict[int, list[FrameMetrics]] = {}
    for row in rows:
        bucket = int(row.timestamp / bucket_seconds)
        buckets.setdefault(bucket, []).append(row)

    selected = [
        max(bucket_rows, key=lambda row: row.score)
        for _bucket, bucket_rows in sorted(buckets.items())
    ]
    selected.sort(key=lambda row: row.timestamp)
    return selected[:max_frames]


def path_contains(parent: Path, child: Path) -> bool:
    resolved_parent = parent.resolve(strict=False)
    resolved_child = child.resolve(strict=False)
    return resolved_child == resolved_parent or resolved_child.is_relative_to(
        resolved_parent
    )


def validate_output_paths(
    images_dir: Path,
    candidates_dir: Path,
    report_path: Path,
) -> None:
    if path_contains(candidates_dir, images_dir) or path_contains(
        images_dir,
        candidates_dir,
    ):
        raise ValueError("images_dir must not overlap candidates_dir")
    if path_contains(images_dir, report_path):
        raise ValueError("report_path must not be inside images_dir")
    if path_contains(candidates_dir, report_path):
        raise ValueError("report_path must not overlap candidates_dir")


def serialize_metric(row: FrameMetrics) -> dict[str, float | int | str]:
    return {
        "source_name": row.path.name,
        "index": row.index,
        "timestamp": row.timestamp,
        "sharpness": row.sharpness,
        "gradient": row.gradient,
        "exposure": row.exposure,
        "clipping": row.clipping,
        "texture": row.texture,
        "score": row.score,
    }


def is_ascii_digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def is_generated_frame_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() == ".jpg"
        and path.stem.startswith("frame_")
        and is_ascii_digits(path.stem.removeprefix("frame_"))
    )


def prepare_images_dir(images_dir: Path) -> None:
    if not images_dir.exists():
        images_dir.mkdir(parents=True, exist_ok=True)
        return
    if not images_dir.is_dir():
        raise ValueError("images_dir exists but is not a directory")

    entries = list(images_dir.iterdir())
    unexpected = [path for path in entries if not is_generated_frame_file(path)]
    if unexpected:
        raise ValueError("images_dir contains unexpected content")

    for path in entries:
        path.unlink()


def write_selected_frames(
    candidates: list[FrameMetrics],
    selected: list[FrameMetrics],
    images_dir: Path,
    report_path: Path,
    candidate_fps: int,
    target_fps: int,
) -> None:
    source_dirs = {row.path.parent.resolve(strict=False) for row in candidates}
    for source_dir in source_dirs:
        validate_output_paths(images_dir, source_dir, report_path)

    prepare_images_dir(images_dir)

    selected_report = []
    for output_index, row in enumerate(selected, start=1):
        output_name = f"frame_{output_index:05d}.jpg"
        shutil.copy2(row.path, images_dir / output_name)
        selected_report.append(
            {
                "output_name": output_name,
                "source_name": row.path.name,
                "timestamp": row.timestamp,
                "score": row.score,
                "sharpness": row.sharpness,
                "gradient": row.gradient,
                "exposure": row.exposure,
                "clipping": row.clipping,
                "texture": row.texture,
            }
        )

    report = {
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "candidate_fps": candidate_fps,
        "target_fps": target_fps,
        "selected": selected_report,
        "candidates": [serialize_metric(row) for row in candidates],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")


def clear_stale_candidates(candidates_dir: Path) -> None:
    candidates_dir.mkdir(parents=True, exist_ok=True)
    for path in candidates_dir.iterdir():
        if is_generated_candidate_file(path):
            path.unlink()


def is_generated_candidate_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() == ".jpg"
        and path.stem.startswith("candidate_")
        and is_ascii_digits(path.stem.removeprefix("candidate_"))
    )


def generated_candidate_files(candidates_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in candidates_dir.iterdir()
        if is_generated_candidate_file(path)
    )


def build_extract_candidates_command(
    input_video: Path,
    candidates_dir: Path,
    candidate_fps: int,
    width: int,
) -> list[str]:
    return [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"fps={candidate_fps},scale={width}:-1",
        "-an",
        "-f",
        "image2",
        str(candidates_dir / "candidate_%06d.jpg"),
    ]


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(f"{value!r} must be positive") from None
    if parsed <= 0:
        raise ValueError(f"{value!r} must be positive")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select high-quality frames for Gaussian Splat reconstruction."
    )
    parser.add_argument("input_video", type=Path)
    parser.add_argument("candidates_dir", type=Path)
    parser.add_argument("images_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--candidate-fps", type=positive_int, default=12)
    parser.add_argument("--target-fps", type=positive_int, default=3)
    parser.add_argument("--max-frames", type=positive_int, default=180)
    parser.add_argument("--min-candidates", type=positive_int, default=8)
    parser.add_argument("--min-selected", type=positive_int, default=8)
    parser.add_argument("--width", type=positive_int, default=1600)
    parser.add_argument("--reuse-candidates", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_candidate_metrics(candidates_dir: Path, candidate_fps: int) -> list[FrameMetrics]:
    rows: list[FrameMetrics] = []
    for index, path in enumerate(generated_candidate_files(candidates_dir), start=1):
        rows.append(
            compute_frame_metrics(
                path,
                index=index,
                timestamp=(index - 1) / candidate_fps,
            )
        )
    return normalize_scores(rows)


def main() -> int:
    args = parse_args()
    if not args.input_video.is_file():
        raise SystemExit(f"input video not found: {args.input_video}")
    if args.candidate_fps < args.target_fps:
        raise SystemExit("candidate-fps must be greater than or equal to target-fps")
    validate_output_paths(args.images_dir, args.candidates_dir, args.report)

    args.candidates_dir.mkdir(parents=True, exist_ok=True)
    if not args.reuse_candidates:
        command = build_extract_candidates_command(
            args.input_video,
            args.candidates_dir,
            args.candidate_fps,
            args.width,
        )
        if args.dry_run:
            print(" ".join(command))
            return 0
        clear_stale_candidates(args.candidates_dir)
        subprocess.run(command, check=True)

    candidates = load_candidate_metrics(args.candidates_dir, args.candidate_fps)
    if len(candidates) < args.min_candidates:
        raise SystemExit(
            f"candidate frame count is lower than {args.min_candidates}"
        )

    selected = select_best_frames(candidates, args.target_fps, args.max_frames)
    if len(selected) < args.min_selected:
        raise SystemExit(f"selected frame count is lower than {args.min_selected}")

    write_selected_frames(
        candidates,
        selected,
        args.images_dir,
        args.report,
        args.candidate_fps,
        args.target_fps,
    )
    print(f"candidates={len(candidates)} selected={len(selected)} report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
