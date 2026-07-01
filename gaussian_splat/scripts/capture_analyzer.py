#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageStat
except ImportError:
    Image = None
    ImageStat = None


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


@dataclass
class FrameSample:
    blur: float
    brightness: float
    contrast: float
    thumbnail: Any = None
    readable: bool = True


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def risk_level(score: float) -> str:
    if score >= 0.75:
        return "low"
    if score >= 0.45:
        return "medium"
    return "high"


def collect_image_paths(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def opencv_sample(gray: Any) -> FrameSample:
    thumbnail = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    return FrameSample(
        blur=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        brightness=float(gray.mean() / 255.0),
        contrast=float(gray.std() / 255.0),
        thumbnail=thumbnail,
    )


def pil_blur_estimate(image: Any) -> float:
    small = image.resize((64, 64))
    pixels = list(small.getdata())
    width, height = small.size
    diffs = []
    for y in range(height):
        offset = y * width
        for x in range(1, width):
            diffs.append(abs(pixels[offset + x] - pixels[offset + x - 1]))
    for y in range(1, height):
        offset = y * width
        previous = (y - 1) * width
        for x in range(width):
            diffs.append(abs(pixels[offset + x] - pixels[previous + x]))
    return float(mean(diffs) ** 2) if diffs else 0.0


def pil_sample(path: Path) -> FrameSample | None:
    if Image is None or ImageStat is None:
        return None
    try:
        with Image.open(path) as image:
            gray = image.convert("L")
            stats = ImageStat.Stat(gray)
            return FrameSample(
                blur=pil_blur_estimate(gray),
                brightness=float(stats.mean[0] / 255.0),
                contrast=float(stats.stddev[0] / 255.0),
                thumbnail=list(gray.resize((64, 64)).getdata()),
            )
    except Exception:
        return None


def load_image_sample(path: Path) -> FrameSample:
    if cv2 is not None:
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if gray is not None:
            return opencv_sample(gray)

    sample = pil_sample(path)
    if sample is not None:
        return sample

    return FrameSample(0.0, 0.0, 0.0, readable=False)


def load_image_frames(directory: Path) -> list[FrameSample]:
    frames = []
    for path in collect_image_paths(directory):
        frames.append(load_image_sample(path))
    return frames


def target_frame_indices(total_frames: int, max_frames: int) -> list[int]:
    if max_frames <= 0 or total_frames <= 0:
        return []
    if total_frames <= max_frames:
        return list(range(total_frames))
    if max_frames == 1:
        return [0]
    return [
        int(index * (total_frames - 1) / (max_frames - 1))
        for index in range(max_frames)
    ]


def load_video_frames(path: Path, max_frames: int = 48) -> list[FrameSample]:
    if cv2 is None:
        raise ValueError("Video input requires OpenCV (cv2), which is not installed")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Could not read video: {path}")

    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames: list[FrameSample] = []

    if total > 0:
        read_indices = target_frame_indices(total, max_frames)
    else:
        read_indices = list(range(max(0, max_frames)))

    for index in read_indices:
        if total > 0:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            continue
        frames.append(opencv_sample(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))

    capture.release()
    return frames


def load_frames(input_path: Path) -> list[FrameSample]:
    if input_path.is_dir():
        return load_image_frames(input_path)
    if input_path.is_file() and input_path.suffix.lower() in VIDEO_SUFFIXES:
        return load_video_frames(input_path)
    if input_path.is_file() and input_path.suffix.lower() in IMAGE_SUFFIXES:
        return load_image_frames(input_path.parent)
    raise ValueError(f"Expected an image directory or video path: {input_path}")


def thumbnail_diff(previous: Any, current: Any) -> float | None:
    if previous is None or current is None:
        return None
    if cv2 is not None and hasattr(previous, "shape") and hasattr(current, "shape"):
        return float(cv2.absdiff(previous, current).mean() / 255.0)
    pairs = list(zip(previous, current))
    if not pairs:
        return None
    return float(mean(abs(left - right) / 255.0 for left, right in pairs))


def frame_motion(frames: list[FrameSample]) -> list[float]:
    if len(frames) < 2:
        return []

    motions = []
    previous = frames[0].thumbnail
    for frame in frames[1:]:
        current = frame.thumbnail
        diff = thumbnail_diff(previous, current)
        if diff is not None:
            motions.append(diff)
        previous = current
    return motions


def build_metrics(frames: list[FrameSample]) -> dict[str, Any]:
    readable = [frame for frame in frames if frame.readable]
    blurs = [frame.blur for frame in readable]
    brightness = [frame.brightness for frame in readable]
    contrasts = [frame.contrast for frame in readable]
    motions = frame_motion(frames)

    duplicate_ratio = (
        float(sum(value < 0.02 for value in motions) / len(motions)) if motions else 1.0
    )
    jump_ratio = (
        float(sum(value > 0.45 for value in motions) / len(motions)) if motions else 1.0
    )

    return {
        "frameCount": len(frames),
        "blurEstimate": float(median(blurs)) if blurs else 0.0,
        "brightnessEstimate": float(mean(brightness)) if brightness else 0.0,
        "contrastEstimate": float(mean(contrasts)) if contrasts else 0.0,
        "duplicateRatio": duplicate_ratio,
        "lowMotionRatio": duplicate_ratio,
        "meanMotion": float(mean(motions)) if motions else 0.0,
        "motionJumpRatio": jump_ratio,
        "readableFrameCount": len(readable),
        "sampledFrameCount": len(frames),
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def job_dir_candidates(path: Path) -> list[Path]:
    start = path if path.is_dir() else path.parent
    return [start, *start.parents[:3]]


def colmap_registration_probe(input_path: Path, frame_count: int) -> dict[str, Any]:
    for candidate in job_dir_candidates(input_path):
        report = load_json(candidate / "processed" / "sfm_report.json")
        if report:
            ratio = report.get("registered_ratio")
            registered = report.get("registered_count")
            image_count = report.get("image_count")
            return {
                "source": "processed/sfm_report.json",
                "registeredRatio": ratio if isinstance(ratio, (int, float)) else None,
                "registeredCount": registered if isinstance(registered, int) else None,
                "imageCount": image_count if isinstance(image_count, int) else None,
            }

        transforms = load_json(candidate / "processed" / "transforms.json")
        frames = transforms.get("frames") if isinstance(transforms.get("frames"), list) else None
        if frames is not None:
            registered = len(frames)
            return {
                "source": "processed/transforms.json",
                "registeredRatio": round(registered / frame_count, 6) if frame_count else None,
                "registeredCount": registered,
                "imageCount": frame_count,
            }
    return {}


def score_report(metrics: dict[str, Any]) -> tuple[float, dict[str, float]]:
    frame_score = clamp(metrics["frameCount"] / 10.0)
    blur_score = clamp(metrics["blurEstimate"] / 350.0)
    brightness_score = clamp(1.0 - abs(metrics["brightnessEstimate"] - 0.5) / 0.5)
    contrast_score = clamp(metrics["contrastEstimate"] / 0.25)
    motion_score = clamp(1.0 - metrics["lowMotionRatio"])
    jump_score = clamp(1.0 - metrics["motionJumpRatio"])

    parts = {
        "frameCount": frame_score,
        "blur": blur_score,
        "brightness": brightness_score,
        "contrast": contrast_score,
        "motion": motion_score,
        "motionJump": jump_score,
    }
    score = (
        frame_score * 0.20
        + blur_score * 0.25
        + brightness_score * 0.15
        + contrast_score * 0.15
        + motion_score * 0.15
        + jump_score * 0.10
    )
    return round(clamp(score), 3), parts


def grade_for(score: float) -> str:
    if score >= 0.93:
        return "A"
    if score >= 0.85:
        return "A-"
    if score >= 0.80:
        return "B+"
    if score >= 0.70:
        return "B"
    if score >= 0.60:
        return "C"
    if score >= 0.50:
        return "D"
    return "F"


def decision_for(score: float) -> str:
    if score >= 0.80:
        return "run"
    if score >= 0.60:
        return "warn"
    if score >= 0.40:
        return "require_override"
    return "recapture_recommended"


def recommendations(metrics: dict[str, Any], parts: dict[str, float]) -> list[str]:
    items = []
    if metrics["frameCount"] < 10:
        items.append("Add more frames before reconstruction.")
    if parts["blur"] < 0.45:
        items.append("Recapture sharper images or remove blurry frames.")
    if parts["brightness"] < 0.45:
        items.append("Improve lighting and avoid under/over-exposed frames.")
    if parts["contrast"] < 0.45:
        items.append("Add frames with more visible texture and contrast.")
    if metrics["lowMotionRatio"] > 0.40:
        items.append("Move around the subject more; many frames look duplicated.")
    if metrics["motionJumpRatio"] > 0.25:
        items.append("Avoid large viewpoint jumps between neighboring frames.")
    probe = metrics.get("colmapRegistrationProbe") if isinstance(metrics.get("colmapRegistrationProbe"), dict) else {}
    ratio = probe.get("registeredRatio")
    if isinstance(ratio, (int, float)) and ratio < 0.60:
        items.append("COLMAP registered too few frames; add overlap or recapture weak angles.")
    return items


def analyze_capture(input_path: str | Path) -> dict[str, Any]:
    path = Path(input_path)
    frames = load_frames(path)
    metrics = build_metrics(frames)
    probe = colmap_registration_probe(path, metrics["frameCount"])
    if probe:
        metrics["colmapRegistrationProbe"] = probe
    score, parts = score_report(metrics)
    registration_score = score
    ratio = probe.get("registeredRatio") if probe else None
    if isinstance(ratio, (int, float)):
        registration_score = float(ratio)
    risks = {
        "frameCount": risk_level(parts["frameCount"]),
        "blur": risk_level(parts["blur"]),
        "brightness": risk_level(parts["brightness"]),
        "contrast": risk_level(parts["contrast"]),
        "duplicates": risk_level(1.0 - metrics["duplicateRatio"]),
        "motion": risk_level(parts["motion"]),
        "motionJump": risk_level(parts["motionJump"]),
        "registration": risk_level(registration_score),
    }

    return {
        "confidenceScore": score,
        "grade": grade_for(score),
        "decision": decision_for(score),
        "estimatedRisk": risks,
        "metrics": metrics,
        "recommendations": recommendations(metrics, parts),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score capture quality before heavy reconstruction."
    )
    parser.add_argument("input", help="Frame/image directory or video path")
    parser.add_argument("--output", help="Write JSON report to this path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        report = analyze_capture(args.input)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    payload = json.dumps(report, indent=2, sort_keys=True)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n")
        print(output)
    else:
        print(payload)


if __name__ == "__main__":
    main()
