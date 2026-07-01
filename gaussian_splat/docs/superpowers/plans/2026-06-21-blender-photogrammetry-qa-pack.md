# Blender Photogrammetry QA Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable Blender QA Pack generator that packages existing Gaussian Splat job outputs into Blender-inspectable SfM/camera/point-cloud diagnostics.

**Architecture:** Add one focused Python CLI that reads an existing job or benchmark variant, discovers frames, COLMAP sparse model files, reports, and splat exports, then writes a `blender-pack/` folder with a manifest, camera path JSON, sparse point-cloud PLY, proxy frames, QA report, and README. The 3wa server only generates inspection assets; Blender is opened later on a Windows workstation or GUI engineering machine. The first implementation must not run Blender, create `.blend` files, or automate the Photogrammetry Importer add-on.

**Tech Stack:** Python 3.10+, pytest, COLMAP binary model parsing, JSON, PLY ASCII output, existing Gaussian Splat job folders.

---

## File Structure

- Create: `scripts/generate_blender_pack.py`
  - Responsibility: CLI and library functions for discovering job artifacts, parsing COLMAP sparse binaries, writing Blender QA pack files, and producing a concise report.
- Create: `tests/test_blender_qa_pack.py`
  - Responsibility: unit tests for COLMAP binary parsing, manifest generation, report generation, README content, and CLI output.
- Modify: `docs/frame-quality-runbook.md`
  - Responsibility: add a short Blender QA Pack section and the first command for `uploads/3`.
- Modify: `history.md`
  - Responsibility: record that G1.8 design moved into an implementation plan and define the first command to run.

No PHP, viewer, training, cleanup, or database code changes are required for this plan.

## Runtime Boundary

Phase 1 server responsibilities:

- convert COLMAP sparse points to PLY;
- write `camera_path.json`;
- write `image_manifest.json`;
- write `blender_qa_manifest.json`;
- write `blender_qa_report.json` initial values;
- write `README.md`;
- generate `frames_50/` and `frames_25/` proxy frames when `ffmpeg` can read the selected images.

Phase 2 workstation responsibilities:

- open Blender with a GUI;
- install and run `SBCV/Blender-Addon-Photogrammetry-Importer`;
- manually inspect camera path, point cloud, ROI, low-confidence periphery, ground plane, and delivery candidates;
- fill human judgment back into `blender_qa_notes.md` or a later review report.

Phase 3 optional automation:

- only after the manual workflow is stable, evaluate headless Blender import, `.blend` saving, and screenshots.

This plan intentionally does not create `run_blender_headless.py`.

## Target Output

First production command:

```bash
python3 scripts/generate_blender_pack.py \
  uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

Expected files:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/
  README.md
  blender_qa_manifest.json
  blender_qa_report.json
  blender_qa_notes.md
  import/
    colmap/
      cameras.bin
      images.bin
      points3D.bin
    sparse_points.ply
    camera_path.json
    image_manifest.json
  proxies/
    frames_50/
    frames_25/
    sparse_points_preview.ply
```

---

### Task 1: Write Failing Tests For Pack Generation

**Files:**
- Create: `tests/test_blender_qa_pack.py`
- Create in test tmp dirs only: synthetic COLMAP `points3D.bin`, `images.bin`, job reports, frame folders, and exports.

- [ ] **Step 1: Create the test file with binary fixture helpers**

Create `tests/test_blender_qa_pack.py` with:

```python
import json
import struct
import subprocess
from pathlib import Path

from scripts.generate_blender_pack import (
    generate_blender_pack,
    parse_images_bin,
    parse_points3d_bin,
)


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_points3d_bin(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(struct.pack("<Q", 2))
        fh.write(struct.pack("<QdddBBBdQ", 10, 1.0, 2.0, 3.0, 255, 100, 50, 0.2, 1))
        fh.write(struct.pack("<ii", 7, 3))
        fh.write(struct.pack("<QdddBBBdQ", 11, -1.0, -2.0, -3.0, 10, 20, 30, 0.4, 0))


def write_images_bin(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(struct.pack("<Q", 2))
        fh.write(struct.pack("<idddddddi", 7, 1.0, 0.0, 0.0, 0.0, -1.0, -2.0, -3.0, 1))
        fh.write(b"frame_00001.jpg\x00")
        fh.write(struct.pack("<Q", 0))
        fh.write(struct.pack("<idddddddi", 8, 1.0, 0.0, 0.0, 0.0, -4.0, -5.0, -6.0, 1))
        fh.write(b"frame_00002.jpg\x00")
        fh.write(struct.pack("<Q", 0))


def make_job(tmp_path: Path) -> Path:
    job = tmp_path / "selected-30k-hierarchical"
    (job / "processed" / "images").mkdir(parents=True)
    (job / "processed" / "images" / "frame_00001.jpg").write_bytes(b"jpg1")
    (job / "processed" / "images" / "frame_00002.jpg").write_bytes(b"jpg2")
    sparse = job / "processed" / "colmap" / "sparse" / "0"
    write_points3d_bin(sparse / "points3D.bin")
    write_images_bin(sparse / "images.bin")
    (job / "processed" / "colmap" / "database.db").write_bytes(b"sqlite")
    (job / "exports").mkdir()
    (job / "exports" / "splat.ply").write_text("ply\n", encoding="utf-8")
    (job / "exports" / "splat.clean.ply").write_text("ply\n", encoding="utf-8")
    write_json(job / "qa_report.json", {"registered_count": 2, "frame_count": 2, "quality_grade": "B"})
    write_json(job / "frame_quality_report.json", {"selected_count": 2, "candidate_count": 6})
    write_json(job / "processed" / "sfm_report.json", {"mapper": "hierarchical", "registered_ratio": 1.0})
    return job
```

- [ ] **Step 2: Add parser expectations**

Append to `tests/test_blender_qa_pack.py`:

```python
def test_parse_points3d_bin_reads_colmap_sparse_points(tmp_path):
    points_path = tmp_path / "points3D.bin"
    write_points3d_bin(points_path)

    points = parse_points3d_bin(points_path)

    assert points == [
        {
            "id": 10,
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "red": 255,
            "green": 100,
            "blue": 50,
            "error": 0.2,
            "track_length": 1,
        },
        {
            "id": 11,
            "x": -1.0,
            "y": -2.0,
            "z": -3.0,
            "red": 10,
            "green": 20,
            "blue": 30,
            "error": 0.4,
            "track_length": 0,
        },
    ]


def test_parse_images_bin_outputs_camera_centers(tmp_path):
    images_path = tmp_path / "images.bin"
    write_images_bin(images_path)

    cameras = parse_images_bin(images_path)

    assert cameras == [
        {"id": 7, "name": "frame_00001.jpg", "camera_id": 1, "center": [1.0, 2.0, 3.0]},
        {"id": 8, "name": "frame_00002.jpg", "camera_id": 1, "center": [4.0, 5.0, 6.0]},
    ]
```

- [ ] **Step 3: Add end-to-end pack expectations**

Append to `tests/test_blender_qa_pack.py`:

```python
def test_generate_blender_pack_writes_manifest_assets_and_docs(tmp_path):
    job = make_job(tmp_path)

    pack_dir = generate_blender_pack(job)

    manifest = json.loads((pack_dir / "blender_qa_manifest.json").read_text(encoding="utf-8"))
    report = json.loads((pack_dir / "blender_qa_report.json").read_text(encoding="utf-8"))
    camera_path = json.loads((pack_dir / "import" / "camera_path.json").read_text(encoding="utf-8"))
    image_manifest = json.loads((pack_dir / "import" / "image_manifest.json").read_text(encoding="utf-8"))
    sparse_ply = (pack_dir / "import" / "sparse_points.ply").read_text(encoding="utf-8")
    preview_ply = (pack_dir / "proxies" / "sparse_points_preview.ply").read_text(encoding="utf-8")
    readme = (pack_dir / "README.md").read_text(encoding="utf-8")

    assert manifest["jobId"] == str(job)
    assert manifest["colmapSparseModel"] == "processed/colmap/sparse/0"
    assert manifest["database"] == "processed/colmap/database.db"
    assert manifest["splatClean"] == "exports/splat.clean.ply"
    assert manifest["blender"]["importer"] == "SBCV/Blender-Addon-Photogrammetry-Importer"
    assert manifest["proxyFrames"]["scales"] == [50, 25]
    assert report["cameraPath"]["registeredFrames"] == 2
    assert report["cameraPath"]["selectedFrames"] == 2
    assert report["cameraPath"]["registeredRatio"] == 1.0
    assert report["artifactDiagnosis"]["recommendedAction"] == "open Blender QA Pack and classify ROI/periphery artifacts"
    assert camera_path["cameras"][0]["center"] == [1.0, 2.0, 3.0]
    assert image_manifest["imageCount"] == 2
    assert "element vertex 2" in sparse_ply
    assert "255 100 50" in sparse_ply
    assert "element vertex 2" in preview_ply
    assert (pack_dir / "proxies" / "frames_50").is_dir()
    assert (pack_dir / "proxies" / "frames_25").is_dir()
    assert "File > Import > COLMAP" in readme


def test_generate_blender_pack_cli_prints_output_path(tmp_path):
    job = make_job(tmp_path)

    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "generate_blender_pack.py"),
            str(job),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert str(job / "blender-pack") in result.stdout
    assert (job / "blender-pack" / "blender_qa_manifest.json").is_file()
```

- [ ] **Step 4: Run the new tests and confirm they fail**

Run:

```bash
pytest -q tests/test_blender_qa_pack.py
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'scripts.generate_blender_pack'`.

- [ ] **Step 5: Commit the failing tests**

Run:

```bash
git add tests/test_blender_qa_pack.py
git commit -m "test: add blender qa pack expectations"
```

---

### Task 2: Implement Blender QA Pack Generator

**Files:**
- Create: `scripts/generate_blender_pack.py`
- Test: `tests/test_blender_qa_pack.py`

- [ ] **Step 1: Create the script with COLMAP parsers and pack builder**

Create `scripts/generate_blender_pack.py` with:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def relpath(path: Path, base: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def read_c_string(handle) -> str:
    chunks = bytearray()
    while True:
        value = handle.read(1)
        if value == b"":
            break
        if value == b"\x00":
            break
        chunks.extend(value)
    return chunks.decode("utf-8", errors="replace")


def qvec_to_rotation(qvec: tuple[float, float, float, float]) -> list[list[float]]:
    qw, qx, qy, qz = qvec
    return [
        [1.0 - 2.0 * qy * qy - 2.0 * qz * qz, 2.0 * qx * qy - 2.0 * qz * qw, 2.0 * qx * qz + 2.0 * qy * qw],
        [2.0 * qx * qy + 2.0 * qz * qw, 1.0 - 2.0 * qx * qx - 2.0 * qz * qz, 2.0 * qy * qz - 2.0 * qx * qw],
        [2.0 * qx * qz - 2.0 * qy * qw, 2.0 * qy * qz + 2.0 * qx * qw, 1.0 - 2.0 * qx * qx - 2.0 * qy * qy],
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
    with path.open("rb") as handle:
        count_data = handle.read(8)
        if len(count_data) != 8:
            return points
        (count,) = struct.unpack("<Q", count_data)
        for _ in range(count):
            point_data = handle.read(43)
            if len(point_data) != 43:
                break
            point_id, x, y, z, red, green, blue, error, track_length = struct.unpack("<QdddBBBdQ", point_data)
            for _track_index in range(track_length):
                handle.read(8)
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
    with path.open("rb") as handle:
        count_data = handle.read(8)
        if len(count_data) != 8:
            return cameras
        (count,) = struct.unpack("<Q", count_data)
        for _ in range(count):
            image_data = handle.read(64)
            if len(image_data) != 64:
                break
            image_id, qw, qx, qy, qz, tx, ty, tz, camera_id = struct.unpack("<idddddddi", image_data)
            name = read_c_string(handle)
            points2d_data = handle.read(8)
            if len(points2d_data) != 8:
                break
            (points2d_count,) = struct.unpack("<Q", points2d_data)
            handle.read(points2d_count * 24)
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
            f"{point['x']:.9g} {point['y']:.9g} {point['z']:.9g} {point['red']} {point['green']} {point['blue']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_proxy_frames(
    images: list[dict[str, Any]],
    job_dir: Path,
    proxies_dir: Path,
    scales: tuple[int, ...] = (50, 25),
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
        ratio = scale / 100.0
        for image in images:
            relative_path = image.get("path")
            name = image.get("name")
            if not isinstance(relative_path, str) or not isinstance(name, str):
                failed += 1
                continue
            source = job_dir / relative_path
            output = output_dir / name
            command = [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                "-vf",
                f"scale=iw*{ratio}:ih*{ratio}",
                str(output),
            ]
            completed = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if completed.returncode == 0 and output.is_file():
                generated += 1
            else:
                failed += 1
        result["generated"][str(scale)] = generated
        result["failed"][str(scale)] = failed

    if any(count for count in result["failed"].values()):
        result["status"] = "partial" if any(count for count in result["generated"].values()) else "failed"
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
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
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


def generate_blender_pack(job_dir: Path | str, output_dir: Path | str | None = None, max_preview_points: int = 250000) -> Path:
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

    write_points_ply(import_dir / "sparse_points.ply", points)
    write_points_ply(proxies_dir / "sparse_points_preview.ply", points, max_preview_points)
    (import_dir / "camera_path.json").write_text(
        json.dumps({"cameraCount": len(cameras), "pathSpan": camera_path_span(cameras), "cameras": cameras}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    images = image_entries(images_dir, job_dir)
    (import_dir / "image_manifest.json").write_text(
        json.dumps({"imageCount": len(images), "images": images}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    proxy_frames = build_proxy_frames(images, job_dir, proxies_dir)

    qa_report = load_json(job_dir / "qa_report.json")
    frame_report = load_json(job_dir / "frame_quality_report.json") or load_json(job_dir / "frame_report.json")
    sfm_report = load_json(job_dir / "processed" / "sfm_report.json")
    manifest = {
        "jobId": str(job_dir),
        "sourceVideo": relpath(job_dir / "input" / "input.mp4", job_dir),
        "imagesDir": relpath(images_dir, job_dir) if images_dir is not None else None,
        "colmapSparseModel": relpath(sparse_dir, job_dir),
        "database": relpath(job_dir / "processed" / "colmap" / "database.db", job_dir),
        "splatRaw": relpath(job_dir / "exports" / "splat.ply", job_dir),
        "splatClean": relpath(job_dir / "exports" / "splat.clean.ply", job_dir),
        "qaReport": relpath(job_dir / "qa_report.json", job_dir),
        "frameReport": relpath(job_dir / "frame_quality_report.json", job_dir) or relpath(job_dir / "frame_report.json", job_dir),
        "sfmReport": relpath(job_dir / "processed" / "sfm_report.json", job_dir),
        "proxyPolicy": {"frameScales": [50, 25], "maxPreviewPoints": max_preview_points},
        "proxyFrames": proxy_frames,
        "blender": {
            "targetVersion": "4.x",
            "displayBackend": "OpenGL",
            "importer": "SBCV/Blender-Addon-Photogrammetry-Importer",
        },
    }
    (pack_dir / "blender_qa_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pack_dir / "blender_qa_report.json").write_text(
        json.dumps(build_report(cameras, qa_report, frame_report, sfm_report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (pack_dir / "blender_qa_notes.md").write_text(
        "# Blender QA Notes\n\n- Main subject: needs review\n- Periphery: needs review\n- Capture/path notes: needs review\n- Recommended action: needs review\n",
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
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
pytest -q tests/test_blender_qa_pack.py
```

Expected: PASS for all tests in `tests/test_blender_qa_pack.py`.

- [ ] **Step 3: Run static Python syntax check**

Run:

```bash
python3 -m py_compile scripts/generate_blender_pack.py tests/test_blender_qa_pack.py
```

Expected: command exits with status `0`.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add scripts/generate_blender_pack.py tests/test_blender_qa_pack.py
git commit -m "feat: generate blender photogrammetry qa packs"
```

---

### Task 3: Document The Blender QA Pack Runbook

**Files:**
- Modify: `docs/frame-quality-runbook.md`
- Modify: `history.md`

- [ ] **Step 1: Add runbook section**

Append this section to `docs/frame-quality-runbook.md`:

```markdown
## Blender Photogrammetry QA Pack

Use this pack when the web viewer shows recognizable subject detail but severe peripheral glass-shard artifacts. The pack does not retrain the scene and does not run Blender on the server. It prepares existing frames, proxy frames, COLMAP sparse outputs, and QA reports for Blender inspection on a Windows workstation or GUI engineering machine.

First benchmark command:

```bash
python3 scripts/generate_blender_pack.py \
  uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

Expected output:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/
```

Open `blender-pack/README.md` on the engineering workstation, then import the COLMAP model with `SBCV/Blender-Addon-Photogrammetry-Importer`. Use `import/sparse_points.ply`, `proxies/sparse_points_preview.ply`, `proxies/frames_50`, `proxies/frames_25`, and `import/camera_path.json` to judge whether the artifact problem is capture coverage, SfM, training, cleanup, or viewer-related.

Capture notes to verify during Blender review:

- camera path should move around or along the subject, not only rotate in place;
- stabilization should be disabled when the capture app allows it;
- exposure and focus should be locked when possible;
- trenches and roadwork should include corridor movement plus cross-angle supplemental shots.
```

- [ ] **Step 2: Append history note**

Append to `history.md`:

```markdown
## 2026-06-21 - Blender Photogrammetry QA Pack Plan

- Approved G1.8 Blender Photogrammetry QA Pack design.
- The first implementation should generate a `blender-pack/` for `uploads/3/benchmark-uploads-3/selected-30k-hierarchical`.
- The 3wa server should generate manifests, COLMAP-derived PLY, proxy frames, camera path JSON, initial report, and README.
- Blender inspection should happen on a Windows workstation or GUI engineering machine.
- Blender is treated as an engineering inspection and delivery-bridge surface, not as a replacement for Gaussian Splatting, not as a server dependency, and not as the 3wa web viewer.
- First command:

```bash
python3 scripts/generate_blender_pack.py uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```
```

- [ ] **Step 3: Verify docs mention the command**

Run:

```bash
rg -n "generate_blender_pack|Blender Photogrammetry QA Pack" docs/frame-quality-runbook.md history.md
```

Expected: both files show the new section or note.

- [ ] **Step 4: Commit docs**

Run:

```bash
git add docs/frame-quality-runbook.md history.md
git commit -m "docs: add blender qa pack runbook"
```

---

### Task 4: Generate The First `uploads/3` Blender Pack

**Files:**
- Create runtime artifacts under: `uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/`

- [ ] **Step 1: Run generator on the hierarchical benchmark**

Run:

```bash
python3 scripts/generate_blender_pack.py \
  uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

Expected stdout:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack
```

- [ ] **Step 2: Inspect generated files**

Run:

```bash
find uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack -maxdepth 3 -type f | sort
```

Expected output includes:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/README.md
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_manifest.json
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_notes.md
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_report.json
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/colmap/cameras.bin
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/colmap/images.bin
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/colmap/points3D.bin
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/camera_path.json
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/image_manifest.json
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/sparse_points.ply
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/proxies/sparse_points_preview.ply
```

- [ ] **Step 3: Inspect proxy frame directories**

Run:

```bash
find uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/proxies -maxdepth 1 -type d | sort
```

Expected output includes:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/proxies/frames_25
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/proxies/frames_50
```

If `ffmpeg` can read the source frames, the proxy directories should contain generated images. If proxy generation fails, `blender_qa_manifest.json.proxyFrames.status` must record `partial`, `failed`, or `skipped_no_ffmpeg` instead of blocking pack generation.

- [ ] **Step 4: Validate JSON files**

Run:

```bash
python3 -m json.tool uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_manifest.json >/dev/null
python3 -m json.tool uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_report.json >/dev/null
python3 -m json.tool uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/camera_path.json >/dev/null
python3 -m json.tool uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/image_manifest.json >/dev/null
```

Expected: all commands exit with status `0`.

- [ ] **Step 5: Confirm point-cloud headers**

Run:

```bash
head -12 uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/import/sparse_points.ply
head -12 uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/proxies/sparse_points_preview.ply
```

Expected: both files start with `ply`, `format ascii 1.0`, and an `element vertex` line greater than `0`.

- [ ] **Step 6: Record generated pack path**

Append to `history.md`:

```markdown
## 2026-06-21 - First Blender QA Pack Artifact

- Generated first Blender QA Pack:
  - `uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack`
- Use `README.md` inside the pack for Blender import steps.
- Use `blender_qa_report.json` and `blender_qa_notes.md` to classify whether artifacts are capture, SfM, training, cleanup, or viewer-related.
```

- [ ] **Step 7: Commit generated metadata and history only if artifact policy allows it**

If the repository is allowed to track runtime benchmark metadata, run:

```bash
git add history.md uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/README.md uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_manifest.json uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_report.json uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack/blender_qa_notes.md
git commit -m "docs: record first blender qa pack artifact"
```

If runtime artifacts should not be tracked, commit only `history.md`:

```bash
git add history.md
git commit -m "docs: record first blender qa pack artifact"
```

---

### Task 5: Full Verification

**Files:**
- Read: `scripts/generate_blender_pack.py`
- Read: `tests/test_blender_qa_pack.py`
- Read: `docs/frame-quality-runbook.md`
- Read: `history.md`

- [ ] **Step 1: Run the Blender pack tests**

Run:

```bash
pytest -q tests/test_blender_qa_pack.py
```

Expected: all tests pass.

- [ ] **Step 2: Run neighboring QA tests that exercise report conventions**

Run:

```bash
pytest -q tests/test_georef_metadata.py tests/test_trench_coverage_report.py tests/test_blender_qa_pack.py
```

Expected: all tests pass.

- [ ] **Step 3: Run syntax checks**

Run:

```bash
python3 -m py_compile scripts/generate_blender_pack.py
```

Expected: command exits with status `0`.

- [ ] **Step 4: Search for incomplete plan/spec markers**

Run:

```bash
rg -n "T[B]D|TO[D]O|FIX[M]E|implement[ ]later" docs/superpowers/specs/2026-06-21-blender-photogrammetry-qa-pack-design.md docs/superpowers/plans/2026-06-21-blender-photogrammetry-qa-pack.md scripts/generate_blender_pack.py tests/test_blender_qa_pack.py
```

Expected: no output.

- [ ] **Step 5: Final status check**

Run:

```bash
git status --short
```

Expected: only unrelated pre-existing dirty files remain, or a clean tree if the implementer is working in an isolated worktree.

---

## Execution Notes

- The implementation must not rerun training.
- The implementation must not require Blender to be installed.
- The implementation must tolerate missing splat exports by writing `null` for absent manifest paths.
- The implementation must tolerate missing COLMAP binaries by producing empty point/camera files rather than crashing.
- The implementation must keep runtime artifacts under the selected job folder.
- The implementation must avoid changing `viewer_splat.html`, `js/gaussian_splat_viewer.js`, PHP pages, or training scripts.

## Self-Review

- Spec coverage: the plan creates the pack generator, manifest, sparse PLY, camera path JSON, report, notes, README, first `uploads/3` run, and docs/history updates required by the design.
- Scope: mesh extraction, texture baking, Cesium, Easymap, Unreal, and headless Blender automation are intentionally outside this first implementation.
- Type consistency: function names used by tests match the script API: `parse_points3d_bin`, `parse_images_bin`, and `generate_blender_pack`.
- Completeness scan: no unfinished requirement markers are intentionally present.
