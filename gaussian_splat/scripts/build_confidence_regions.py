#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.filter_splat_ply import property_indexes, read_ply


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relpath(path: Path | None, base: Path) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    q = min(1.0, max(0.0, q))
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def rounded(values: list[float]) -> list[float]:
    return [round(value, 6) for value in values]


def read_ascii_points_ply(path: Path) -> list[tuple[float, float, float]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        header_end = lines.index("end_header")
    except ValueError:
        return []

    points: list[tuple[float, float, float]] = []
    for line in lines[header_end + 1 :]:
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            points.append((float(parts[0]), float(parts[1]), float(parts[2])))
        except ValueError:
            continue
    return points


def bbox_from_points(
    points: list[tuple[float, float, float]],
    bbox_quantile: float,
    bbox_padding: float,
) -> dict[str, Any]:
    if not points:
        return {
            "bbox_min": [0.0, 0.0, 0.0],
            "bbox_max": [0.0, 0.0, 0.0],
            "center": [0.0, 0.0, 0.0],
            "radius": 0.0,
        }

    q = min(0.5, max(0.0, bbox_quantile))
    mins = []
    maxs = []
    for axis in range(3):
        values = [point[axis] for point in points]
        low = quantile(values, q)
        high = quantile(values, 1.0 - q)
        span = high - low
        padding = span * bbox_padding
        mins.append(low - padding)
        maxs.append(high + padding)

    center = [(low + high) / 2.0 for low, high in zip(mins, maxs)]
    radius = math.sqrt(sum((high - low) ** 2 for low, high in zip(mins, maxs))) / 2.0
    return {
        "bbox_min": rounded(mins),
        "bbox_max": rounded(maxs),
        "center": rounded(center),
        "radius": round(radius, 6),
    }


def confidence_grade(point_count: int, camera_count: int) -> str:
    if point_count >= 1000 and camera_count >= 20:
        return "high"
    if point_count >= 100 and camera_count >= 5:
        return "medium"
    if point_count > 0 and camera_count > 0:
        return "low"
    return "none"


def splat_confidence_grade(splat_count: int) -> str:
    if splat_count >= 100000:
        return "high"
    if splat_count >= 1000:
        return "medium"
    if splat_count > 0:
        return "low"
    return "none"


def inside_bbox(point: tuple[float, float, float], bbox_min: list[float], bbox_max: list[float]) -> bool:
    return all(bbox_min[index] <= point[index] <= bbox_max[index] for index in range(3))


def read_splat_points(splat_path: Path | None) -> list[tuple[float, float, float]]:
    if splat_path is None or not splat_path.is_file():
        return []

    _header, vertex_properties, rows = read_ply(splat_path)
    indexes = property_indexes(vertex_properties)
    return [(row[indexes["x"]], row[indexes["y"]], row[indexes["z"]]) for row in rows]


def point_statistics(
    points: list[tuple[float, float, float]],
    source: str | None,
    bbox_min: list[float],
    bbox_max: list[float],
) -> dict[str, Any]:
    inside_count = 0
    for point in points:
        if inside_bbox(point, bbox_min, bbox_max):
            inside_count += 1
    total_count = len(points)
    outside_count = total_count - inside_count
    return {
        "source": source,
        "total_count": total_count,
        "inside_roi_count": inside_count,
        "outside_roi_count": outside_count,
        "outside_roi_ratio": round(outside_count / total_count, 4) if total_count else 0.0,
    }


def choose_splat(job_dir: Path) -> Path | None:
    for candidate in (job_dir / "exports" / "splat.clean.ply", job_dir / "exports" / "splat.ply"):
        if candidate.is_file():
            return candidate
    return None


def build_confidence_regions(
    job_dir: Path | str,
    output_dir: Path | str | None = None,
    bbox_quantile: float = 0.05,
    bbox_padding: float = 0.2,
) -> dict[str, Path]:
    job_dir = Path(job_dir)
    output_dir = Path(output_dir) if output_dir is not None else job_dir / "exports"
    sparse_path = job_dir / "blender-pack" / "import" / "sparse_points.ply"
    camera_path_path = job_dir / "blender-pack" / "import" / "camera_path.json"
    splat_path = choose_splat(job_dir)

    points = read_ascii_points_ply(sparse_path)
    splat_points = read_splat_points(splat_path)
    camera_path = load_json(camera_path_path)
    camera_count = int(camera_path.get("cameraCount") or len(camera_path.get("cameras", [])) or 0)
    sparse_bbox = bbox_from_points(points, bbox_quantile, bbox_padding)
    splat_bbox = bbox_from_points(splat_points, bbox_quantile, bbox_padding)
    sparse_grade = confidence_grade(len(points), camera_count)
    splat_grade = splat_confidence_grade(len(splat_points))

    sparse_candidate = {
        "id": "sparse-core-robust-bbox",
        "type": "bbox",
        "method": "sparse_points_quantile_bbox",
        "coordinate_space": "colmap_sparse",
        "runtime_compatible": False,
        "confidence": sparse_grade,
        "bbox_min": sparse_bbox["bbox_min"],
        "bbox_max": sparse_bbox["bbox_max"],
        "center": sparse_bbox["center"],
        "radius": sparse_bbox["radius"],
        "source_point_count": len(points),
        "camera_count": camera_count,
        "bbox_quantile": bbox_quantile,
        "bbox_padding": bbox_padding,
    }
    candidates = [sparse_candidate]

    recommended_candidate = sparse_candidate
    if splat_points:
        splat_candidate = {
            "id": "splat-clean-robust-bbox",
            "type": "bbox",
            "method": "splat_positions_quantile_bbox",
            "coordinate_space": "splat_ply",
            "runtime_compatible": True,
            "confidence": splat_grade,
            "bbox_min": splat_bbox["bbox_min"],
            "bbox_max": splat_bbox["bbox_max"],
            "center": splat_bbox["center"],
            "radius": splat_bbox["radius"],
            "source_point_count": len(splat_points),
            "bbox_quantile": bbox_quantile,
            "bbox_padding": bbox_padding,
        }
        candidates.insert(0, splat_candidate)
        recommended_candidate = splat_candidate

        sparse_candidate["runtime_coverage"] = point_statistics(
            splat_points,
            relpath(splat_path, job_dir),
            sparse_candidate["bbox_min"],
            sparse_candidate["bbox_max"],
        )

    roi = {
        "job": str(job_dir),
        "source": {
            "sparsePoints": relpath(sparse_path, job_dir),
            "cameraPath": relpath(camera_path_path, job_dir),
            "splat": relpath(splat_path, job_dir),
        },
        "summary": {
            "sparse_point_count": len(points),
            "splat_count": len(splat_points),
            "camera_count": camera_count,
            "confidence": recommended_candidate["confidence"],
            "recommended_coordinate_space": recommended_candidate["coordinate_space"],
        },
        "recommended": recommended_candidate["id"],
        "roi_candidates": candidates,
    }

    stats = point_statistics(
        splat_points,
        relpath(splat_path, job_dir),
        recommended_candidate["bbox_min"],
        recommended_candidate["bbox_max"],
    )
    low = {
        "job": str(job_dir),
        "roi_source": f"roi_candidates.json#{recommended_candidate['id']}",
        "regions": [
            {
                "id": "outside-recommended-roi",
                "type": "outside_bbox",
                "bbox_min": recommended_candidate["bbox_min"],
                "bbox_max": recommended_candidate["bbox_max"],
                "action": "fade_or_remove",
                "confidence": recommended_candidate["confidence"],
                "reason": "outside recommended runtime ROI; treat as low-confidence 3DGS periphery",
            }
        ],
        "splat_statistics": stats,
        "viewer_hint": {
            "fadeOutsideRoi": True,
            "outsideAlpha": 0.05,
            "preserveInsideRoi": True,
        },
        "cleanup_hint": {
            "strategy": "preserve_roi_fade_or_remove_outside",
            "roiCandidate": recommended_candidate["id"],
        },
    }

    roi_path = output_dir / "roi_candidates.json"
    low_path = output_dir / "low_confidence_regions.json"
    write_json(roi_path, roi)
    write_json(low_path, low)
    return {"roi": roi_path, "low_confidence": low_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ROI and low-confidence region metadata for a Gaussian Splat job.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--bbox-quantile", type=float, default=0.05)
    parser.add_argument("--bbox-padding", type=float, default=0.2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = build_confidence_regions(
        args.job_dir,
        output_dir=args.output_dir,
        bbox_quantile=args.bbox_quantile,
        bbox_padding=args.bbox_padding,
    )
    print(outputs["roi"])
    print(outputs["low_confidence"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
