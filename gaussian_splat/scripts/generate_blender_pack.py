#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any, BinaryIO


POINT3D_STRUCT = struct.Struct("<QdddBBBdQ")
IMAGE_STRUCT = struct.Struct("<idddddddi")
PROXY_FRAME_SCALES = (50, 25)
PROXY_FRAME_TIMEOUT_SECONDS = 30
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_BINARY_SKIP_BYTES = 64 * 1024 * 1024
SKIP_CHUNK_SIZE = 1024 * 1024


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


def read_c_string(handle: BinaryIO) -> str:
    chunks = bytearray()
    while True:
        value = handle.read(1)
        if value in {b"", b"\x00"}:
            break
        chunks.extend(value)
    return chunks.decode("utf-8", errors="replace")


def safe_skip_records(handle: BinaryIO, record_count: int, record_size: int) -> bool:
    if record_count < 0 or record_size < 0:
        return False
    if record_count and record_size > MAX_BINARY_SKIP_BYTES // record_count:
        return False

    remaining = record_count * record_size
    while remaining:
        to_read = min(remaining, SKIP_CHUNK_SIZE)
        try:
            chunk = handle.read(to_read)
        except (OSError, OverflowError, ValueError):
            return False
        if len(chunk) != to_read:
            return False
        remaining -= len(chunk)
    return True


def qvec_to_rotation(qvec: tuple[float, float, float, float]) -> list[list[float]]:
    qw, qx, qy, qz = qvec
    return [
        [
            1.0 - 2.0 * qy * qy - 2.0 * qz * qz,
            2.0 * qx * qy - 2.0 * qz * qw,
            2.0 * qx * qz + 2.0 * qy * qw,
        ],
        [
            2.0 * qx * qy + 2.0 * qz * qw,
            1.0 - 2.0 * qx * qx - 2.0 * qz * qz,
            2.0 * qy * qz - 2.0 * qx * qw,
        ],
        [
            2.0 * qx * qz - 2.0 * qy * qw,
            2.0 * qy * qz + 2.0 * qx * qw,
            1.0 - 2.0 * qx * qx - 2.0 * qy * qy,
        ],
    ]


def camera_center(qvec: tuple[float, float, float, float], tvec: tuple[float, float, float]) -> list[float]:
    rotation = qvec_to_rotation(qvec)
    center = []
    for col in range(3):
        value = -sum(rotation[row][col] * tvec[row] for row in range(3))
        center.append(round(value, 6))
    return center


def parse_points3d_bin(path: Path) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    with Path(path).open("rb") as handle:
        count_data = handle.read(8)
        if len(count_data) != 8:
            return points
        (count,) = struct.unpack("<Q", count_data)

        for _ in range(count):
            point_data = handle.read(POINT3D_STRUCT.size)
            if len(point_data) != POINT3D_STRUCT.size:
                break
            point_id, x, y, z, red, green, blue, error, track_length = POINT3D_STRUCT.unpack(point_data)
            if not safe_skip_records(handle, track_length, 8):
                break
            points.append(
                {
                    "id": int(point_id),
                    "x": float(x),
                    "y": float(y),
                    "z": float(z),
                    "red": int(red),
                    "green": int(green),
                    "blue": int(blue),
                    "error": float(error),
                    "track_length": int(track_length),
                }
            )
    return points


def parse_images_bin(path: Path) -> list[dict[str, Any]]:
    cameras: list[dict[str, Any]] = []
    with Path(path).open("rb") as handle:
        count_data = handle.read(8)
        if len(count_data) != 8:
            return cameras
        (count,) = struct.unpack("<Q", count_data)

        for _ in range(count):
            image_data = handle.read(IMAGE_STRUCT.size)
            if len(image_data) != IMAGE_STRUCT.size:
                break
            image_id, qw, qx, qy, qz, tx, ty, tz, camera_id = IMAGE_STRUCT.unpack(image_data)
            name = read_c_string(handle)
            points2d_count_data = handle.read(8)
            if len(points2d_count_data) != 8:
                break
            (points2d_count,) = struct.unpack("<Q", points2d_count_data)
            if not safe_skip_records(handle, points2d_count, 24):
                break
            cameras.append(
                {
                    "id": int(image_id),
                    "name": name,
                    "camera_id": int(camera_id),
                    "center": camera_center((qw, qx, qy, qz), (tx, ty, tz)),
                }
            )
    return cameras


def write_points_ply(path: Path, points: list[dict[str, Any]], max_points: int | None = None) -> None:
    selected = points[:max_points] if max_points is not None else points
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(selected)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header",
    ]
    for point in selected:
        lines.append(
            f"{point['x']:.9g} {point['y']:.9g} {point['z']:.9g} "
            f"{point['red']} {point['green']} {point['blue']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_proxy_frames(
    images: list[dict[str, Any]],
    job_dir: Path,
    proxies_dir: Path,
    scales: tuple[int, ...] = PROXY_FRAME_SCALES,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "scales": list(scales),
        "status": "generated",
        "generated": {},
        "failed": {},
    }

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        result["status"] = "skipped_no_ffmpeg"
        for scale in scales:
            (proxies_dir / f"frames_{scale}").mkdir(parents=True, exist_ok=True)
            result["generated"][str(scale)] = 0
            result["failed"][str(scale)] = len(images)
        return result

    for scale in scales:
        output_dir = proxies_dir / f"frames_{scale}"
        output_dir.mkdir(parents=True, exist_ok=True)
        generated = 0
        failed = 0

        for image in images:
            relative_path = image.get("path")
            name = image.get("name")
            if not isinstance(relative_path, str) or not isinstance(name, str):
                failed += 1
                continue

            source = job_dir / relative_path
            output = output_dir / name
            ratio = scale / 100.0
            command = [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vf",
                f"scale=iw*{ratio}:ih*{ratio}",
                str(output),
            ]
            try:
                completed = subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=PROXY_FRAME_TIMEOUT_SECONDS,
                )
            except (OSError, subprocess.SubprocessError):
                failed += 1
                continue
            if completed.returncode == 0 and output.is_file():
                generated += 1
            else:
                failed += 1

        result["generated"][str(scale)] = generated
        result["failed"][str(scale)] = failed

    failed_total = sum(result["failed"].values())
    generated_total = sum(result["generated"].values())
    if failed_total:
        result["status"] = "partial" if generated_total else "failed"
    return result


def discover_images_dir(job_dir: Path) -> Path | None:
    for candidate in (job_dir / "processed" / "images", job_dir / "images"):
        if candidate.is_dir():
            return candidate
    return None


def image_entries(images_dir: Path | None, job_dir: Path) -> list[dict[str, Any]]:
    if images_dir is None:
        return []
    entries = []
    for path in sorted(images_dir.iterdir()):
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        entries.append({"name": path.name, "path": relpath(path, job_dir)})
    return entries


def camera_path_span(cameras: list[dict[str, Any]]) -> float:
    centers = [camera["center"] for camera in cameras if isinstance(camera.get("center"), list)]
    if len(centers) < 2:
        return 0.0

    span = 0.0
    for index, first in enumerate(centers):
        for second in centers[index + 1 :]:
            span = max(span, math.dist(first, second))
    return round(span, 3)


def build_report(
    cameras: list[dict[str, Any]],
    qa_report: dict[str, Any],
    frame_report: dict[str, Any],
    sfm_report: dict[str, Any],
) -> dict[str, Any]:
    selected_count = frame_report.get("selected_count") or qa_report.get("frame_count") or len(cameras)
    registered_count = len(cameras)
    registered_ratio = round(registered_count / selected_count, 2) if selected_count else 0.0

    return {
        "cameraPath": {
            "registeredFrames": registered_count,
            "selectedFrames": selected_count,
            "registeredRatio": sfm_report.get("registered_ratio", registered_ratio),
            "mapper": sfm_report.get("mapper"),
            "pathSpan": camera_path_span(cameras),
            "suspectedJumps": [],
        },
        "coverage": {
            "subjectCoverage": "needs_blender_review",
            "peripheryCoverage": "needs_blender_review",
            "singleSidedRisk": "needs_blender_review",
            "lowTextureRisk": "needs_blender_review",
        },
        "artifactDiagnosis": {
            "mainSubject": "needs_blender_review",
            "periphery": "needs_blender_review",
            "likelyCauses": [],
            "recommendedAction": "open Blender QA Pack and classify ROI/periphery artifacts",
        },
    }


def copy_colmap_sparse_model(sparse_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not sparse_dir.is_dir():
        return
    for path in sparse_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, output_dir / path.name)


def write_readme(path: Path, job_dir: Path) -> None:
    text = f"""# Blender Photogrammetry QA Pack

Job:

```text
{job_dir}
```

## Open In Blender

This pack was generated on the 3wa server. Blender inspection should happen on a Windows workstation or another GUI engineering machine.

1. Install `SBCV/Blender-Addon-Photogrammetry-Importer`.
2. If point clouds render incorrectly, set Blender display backend to OpenGL.
3. Use `File > Import > COLMAP` and select `import/colmap` or the original COLMAP sparse model listed in `blender_qa_manifest.json`.
4. Load `import/sparse_points.ply` or `proxies/sparse_points_preview.ply` as a point cloud or mesh points.
5. Use `proxies/frames_50` or `proxies/frames_25` for lighter image background review when generated.
6. Use `import/camera_path.json` to review camera centers and path continuity.
7. Compare the Blender camera path with the website splat viewer before changing cleanup thresholds.

## Review Questions

- Does the camera path move around the subject instead of rotating in place?
- Is the main ROI covered from multiple angles?
- Are glass-shard artifacts outside the intended ROI?
- Is strict cleanup making the main subject transparent?
- For construction scenes, does the path follow the trench or work corridor?
"""
    path.write_text(text, encoding="utf-8")


def generate_blender_pack(
    job_dir: Path | str,
    output_dir: Path | str | None = None,
    max_preview_points: int = 250000,
) -> Path:
    job_dir = Path(job_dir)
    pack_dir = Path(output_dir) if output_dir is not None else job_dir / "blender-pack"
    import_dir = pack_dir / "import"
    proxies_dir = pack_dir / "proxies"
    import_dir.mkdir(parents=True, exist_ok=True)
    proxies_dir.mkdir(parents=True, exist_ok=True)

    sparse_dir = job_dir / "processed" / "colmap" / "sparse" / "0"
    points_path = sparse_dir / "points3D.bin"
    images_path = sparse_dir / "images.bin"
    images_dir = discover_images_dir(job_dir)

    points = parse_points3d_bin(points_path) if points_path.is_file() else []
    cameras = parse_images_bin(images_path) if images_path.is_file() else []
    images = image_entries(images_dir, job_dir)

    copy_colmap_sparse_model(sparse_dir, import_dir / "colmap")
    write_points_ply(import_dir / "sparse_points.ply", points)
    write_points_ply(proxies_dir / "sparse_points_preview.ply", points, max_preview_points)
    write_json(
        import_dir / "camera_path.json",
        {"cameraCount": len(cameras), "pathSpan": camera_path_span(cameras), "cameras": cameras},
    )
    write_json(import_dir / "image_manifest.json", {"imageCount": len(images), "images": images})

    proxy_frames = build_proxy_frames(images, job_dir, proxies_dir)

    qa_report = load_json(job_dir / "qa_report.json")
    frame_report = load_json(job_dir / "frame_quality_report.json") or load_json(job_dir / "frame_report.json")
    sfm_report = load_json(job_dir / "processed" / "sfm_report.json")
    manifest = {
        "jobId": str(job_dir),
        "sourceVideo": relpath(job_dir / "input" / "input.mp4", job_dir),
        "imagesDir": relpath(images_dir, job_dir),
        "colmapSparseModel": relpath(sparse_dir, job_dir),
        "database": relpath(job_dir / "processed" / "colmap" / "database.db", job_dir),
        "splatRaw": relpath(job_dir / "exports" / "splat.ply", job_dir),
        "splatClean": relpath(job_dir / "exports" / "splat.clean.ply", job_dir),
        "qaReport": relpath(job_dir / "qa_report.json", job_dir),
        "frameReport": relpath(job_dir / "frame_quality_report.json", job_dir)
        or relpath(job_dir / "frame_report.json", job_dir),
        "sfmReport": relpath(job_dir / "processed" / "sfm_report.json", job_dir),
        "proxyPolicy": {"frameScales": list(PROXY_FRAME_SCALES), "maxPreviewPoints": max_preview_points},
        "proxyFrames": proxy_frames,
        "blender": {
            "targetVersion": "4.x",
            "displayBackend": "OpenGL",
            "importer": "SBCV/Blender-Addon-Photogrammetry-Importer",
        },
    }

    write_json(pack_dir / "blender_qa_manifest.json", manifest)
    write_json(pack_dir / "blender_qa_report.json", build_report(cameras, qa_report, frame_report, sfm_report))
    (pack_dir / "blender_qa_notes.md").write_text(
        "# Blender QA Notes\n\n"
        "- Main subject: needs review\n"
        "- Periphery: needs review\n"
        "- Capture/path notes: needs review\n"
        "- Recommended action: needs review\n",
        encoding="utf-8",
    )
    write_readme(pack_dir / "README.md", job_dir)
    return pack_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Blender Photogrammetry QA Pack for an existing Gaussian Splat job.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-preview-points", type=int, default=250000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pack_dir = generate_blender_pack(args.job_dir, args.output_dir, args.max_preview_points)
    print(pack_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
