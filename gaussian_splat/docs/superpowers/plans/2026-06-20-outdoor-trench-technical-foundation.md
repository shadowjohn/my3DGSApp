# Outdoor Trench Technical Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the server-side technical foundation for outdoor road-excavation / sewer-construction reality layers, focusing on 3D processing, coverage QA, georef metadata, trench-focused exports, and oblique/GLB delivery metadata.

**Architecture:** Keep the current Gaussian Splat MVP pipeline intact and add focused scripts around it. The first version does not build the mobile web UI; it makes the server pipeline ready for future mobile uploads by supporting video/photo-set input contracts, engineering QA, and delivery manifests.

**Tech Stack:** Bash pipeline, Python 3 standard library, pytest, current Nerfstudio/splatfacto scripts, existing `viewer_splat.html` metadata pattern.

---

## Scope

This plan implements the technical foundation from:

```text
docs/superpowers/specs/2026-06-20-outdoor-trench-reality-layer-design.md
```

It intentionally does not implement the mobile web capture guide UI. It prepares the server-side contract that the mobile web guide will later call.

## File Structure

- Create `scripts/outdoor_intake.py`
  - Detect whether an input path is a video file or a photo directory.
  - Produce a normalized `input_manifest.json`.
  - Preserve a stable contract for future mobile uploads.

- Create `scripts/build_trench_coverage_report.py`
  - Read `frame_quality_report.json`, `processed/transforms.json`, and optional `input_manifest.json`.
  - Compute registered ratio, selected count, camera path span, sparse coverage warnings, and capture decision hints.

- Create `scripts/build_georef_metadata.py`
  - Create `georef.json` with stable fields for `none`, `exif`, `manual`, `gcp`, and `rtk`.
  - For MVP, accept manual CLI fields and default to low/none confidence.

- Create `scripts/build_trench_delivery.py`
  - Build `exports/splat.trench.ply` and `exports/splat.trench.viewer.json`.
  - V1 uses the clean splat as the source and writes trench-mode metadata.
  - Later tasks can replace this with true corridor filtering without changing downstream file names.

- Create `scripts/build_trench_qa_report.py`
  - Merge existing `qa_report.json`, coverage report, georef metadata, and trench delivery stats.
  - Produce `trench_qa_report.json` with engineering decisions.

- Create `scripts/build_delivery_manifest.py`
  - Record `delivery_mode`: `gaussian_splat`, `oblique_projection`, `glb_hybrid`, or `mixed`.
  - Include current splat links and future oblique/GLB placeholders without performing GIS integration.

- Modify `scripts/run_mvp_pipeline.sh`
  - Add optional `GS_TRENCH_MODE=1`.
  - When enabled, run coverage, georef, trench delivery, trench QA, and delivery manifest after standard cleanup.

- Modify tests:
  - Create `tests/test_outdoor_intake.py`
  - Create `tests/test_trench_coverage_report.py`
  - Create `tests/test_georef_metadata.py`
  - Create `tests/test_trench_delivery.py`
  - Create `tests/test_trench_qa_report.py`
  - Create `tests/test_delivery_manifest.py`
  - Extend `tests/test_nerfstudio_scripts.py`

---

### Task 1: Outdoor Input Manifest

**Files:**
- Create: `scripts/outdoor_intake.py`
- Test: `tests/test_outdoor_intake.py`

- [ ] **Step 1: Write failing tests for video and photo-set input**

Create `tests/test_outdoor_intake.py`:

```python
import json
from pathlib import Path

from scripts.outdoor_intake import build_input_manifest, write_input_manifest


def test_build_input_manifest_detects_video(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake-video")

    manifest = build_input_manifest(video)

    assert manifest["input_mode"] == "walk_video"
    assert manifest["source"] == str(video)
    assert manifest["video"]["filename"] == "input.mp4"
    assert manifest["photos"] == []
    assert manifest["warnings"] == []


def test_build_input_manifest_detects_photo_set(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    (images / "a.jpg").write_bytes(b"a")
    (images / "b.JPG").write_bytes(b"b")
    (images / "ignore.txt").write_text("ignore")

    manifest = build_input_manifest(images)

    assert manifest["input_mode"] == "photo_set"
    assert manifest["source"] == str(images)
    assert manifest["video"] is None
    assert [photo["filename"] for photo in manifest["photos"]] == ["a.jpg", "b.JPG"]
    assert manifest["warnings"] == []


def test_build_input_manifest_warns_for_sparse_photo_set(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    (images / "one.jpg").write_bytes(b"one")

    manifest = build_input_manifest(images)

    assert manifest["input_mode"] == "photo_set"
    assert "photo_set lower than 8 images" in manifest["warnings"]


def test_write_input_manifest_creates_json(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake-video")
    output = tmp_path / "job" / "input_manifest.json"

    write_input_manifest(video, output)

    data = json.loads(output.read_text())
    assert data["input_mode"] == "walk_video"
    assert data["source"] == str(video)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest -q tests/test_outdoor_intake.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.outdoor_intake'`.

- [ ] **Step 3: Implement `scripts/outdoor_intake.py`**

Create `scripts/outdoor_intake.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".JPG", ".JPEG", ".PNG", ".HEIC"}


def photo_records(directory: Path) -> list[dict[str, Any]]:
    photos = [
        path
        for path in sorted(directory.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.suffix in PHOTO_EXTENSIONS
    ]
    return [
        {
            "filename": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
        }
        for path in photos
    ]


def build_input_manifest(source: Path) -> dict[str, Any]:
    source = Path(source)
    warnings: list[str] = []

    if source.is_file() and source.suffix.lower() in VIDEO_EXTENSIONS:
        return {
            "input_mode": "walk_video",
            "source": str(source),
            "video": {
                "filename": source.name,
                "path": str(source),
                "size_bytes": source.stat().st_size,
            },
            "photos": [],
            "warnings": warnings,
        }

    if source.is_dir():
        photos = photo_records(source)
        if len(photos) < 8:
            warnings.append("photo_set lower than 8 images")
        if not photos:
            warnings.append("photo_set has no supported images")
        return {
            "input_mode": "photo_set",
            "source": str(source),
            "video": None,
            "photos": photos,
            "warnings": warnings,
        }

    raise ValueError(f"unsupported outdoor input source: {source}")


def write_input_manifest(source: Path, output: Path) -> dict[str, Any]:
    manifest = build_input_manifest(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build outdoor trench input manifest.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_input_manifest(args.source, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest -q tests/test_outdoor_intake.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outdoor_intake.py tests/test_outdoor_intake.py
git commit -m "feat: add outdoor trench input manifest"
```

---

### Task 2: Trench Coverage Report

**Files:**
- Create: `scripts/build_trench_coverage_report.py`
- Test: `tests/test_trench_coverage_report.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trench_coverage_report.py`:

```python
import json

from scripts.build_trench_coverage_report import build_coverage_report


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_build_coverage_report_from_frame_quality_and_transforms(tmp_path):
    job = tmp_path / "job"
    write_json(
        job / "input_manifest.json",
        {"input_mode": "walk_video", "warnings": []},
    )
    write_json(
        job / "frame_quality_report.json",
        {
            "candidate_count": 120,
            "selected_count": 60,
            "candidate_fps": 12,
            "target_fps": 3,
        },
    )
    write_json(
        job / "processed" / "transforms.json",
        {
            "frames": [
                {"file_path": "images/frame_00001.jpg", "transform_matrix": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
                {"file_path": "images/frame_00002.jpg", "transform_matrix": [[1, 0, 0, 3], [0, 1, 0, 4], [0, 0, 1, 0], [0, 0, 0, 1]]},
            ]
        },
    )

    report = build_coverage_report(job)

    assert report["input_mode"] == "walk_video"
    assert report["candidate_count"] == 120
    assert report["selected_count"] == 60
    assert report["registered_count"] == 2
    assert report["registered_ratio"] == 0.03
    assert report["camera_path_span"] == 5.0
    assert "registered_ratio lower than 0.65" in report["warnings"]
    assert report["coverage_decision"] == "supplemental_capture_needed"


def test_build_coverage_report_photo_set_with_sparse_images_warns(tmp_path):
    job = tmp_path / "job"
    write_json(
        job / "input_manifest.json",
        {"input_mode": "photo_set", "photos": [{"filename": "a.jpg"}], "warnings": ["photo_set lower than 8 images"]},
    )
    write_json(job / "processed" / "transforms.json", {"frames": []})

    report = build_coverage_report(job)

    assert report["input_mode"] == "photo_set"
    assert report["selected_count"] == 1
    assert report["registered_count"] == 0
    assert report["coverage_decision"] == "retake"
    assert "photo_set lower than 8 images" in report["warnings"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest -q tests/test_trench_coverage_report.py
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement coverage report**

Create `scripts/build_trench_coverage_report.py`:

```python
#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def frame_position(frame: dict[str, Any]) -> list[float] | None:
    matrix = frame.get("transform_matrix")
    if not isinstance(matrix, list) or len(matrix) < 3:
        return None
    try:
        return [float(matrix[0][3]), float(matrix[1][3]), float(matrix[2][3])]
    except (TypeError, ValueError, IndexError):
        return None


def camera_path_span(frames: list[dict[str, Any]]) -> float:
    positions = [position for frame in frames if (position := frame_position(frame)) is not None]
    if len(positions) < 2:
        return 0.0
    max_distance = 0.0
    for left in positions:
        for right in positions:
            distance = math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))
            max_distance = max(max_distance, distance)
    return round(max_distance, 2)


def coverage_decision(registered_ratio: float, selected_count: int, warnings: list[str]) -> str:
    if selected_count < 8 or registered_ratio < 0.3:
        return "retake"
    if registered_ratio < 0.65 or "photo_set lower than 8 images" in warnings:
        return "supplemental_capture_needed"
    if registered_ratio < 0.8:
        return "review_needed"
    return "usable"


def build_coverage_report(job_dir: Path) -> dict[str, Any]:
    manifest = load_json(job_dir / "input_manifest.json")
    frame_quality = load_json(job_dir / "frame_quality_report.json")
    transforms = load_json(job_dir / "processed" / "transforms.json")
    frames = transforms.get("frames", [])
    frames = frames if isinstance(frames, list) else []

    input_mode = manifest.get("input_mode") or "walk_video"
    manifest_warnings = manifest.get("warnings", [])
    warnings = [item for item in manifest_warnings if isinstance(item, str)]

    selected_count = 0
    candidate_count = 0
    if frame_quality:
        candidate_count = int(frame_quality.get("candidate_count", 0) or 0)
        selected_count = int(frame_quality.get("selected_count", 0) or 0)
    elif input_mode == "photo_set":
        photos = manifest.get("photos", [])
        selected_count = len(photos) if isinstance(photos, list) else 0

    registered_count = len(frames)
    registered_ratio = round(registered_count / selected_count, 2) if selected_count else 0.0

    if selected_count < 60:
        warnings.append("selected frame count lower than 60")
    if registered_ratio < 0.65:
        warnings.append("registered_ratio lower than 0.65")

    decision = coverage_decision(registered_ratio, selected_count, warnings)
    return {
        "input_mode": input_mode,
        "candidate_count": candidate_count,
        "selected_count": selected_count,
        "registered_count": registered_count,
        "registered_ratio": registered_ratio,
        "camera_path_span": camera_path_span(frames),
        "coverage_decision": decision,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build outdoor trench coverage report.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.job_dir / "trench_coverage_report.json"
    report = build_coverage_report(args.job_dir)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest -q tests/test_trench_coverage_report.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_trench_coverage_report.py tests/test_trench_coverage_report.py
git commit -m "feat: add trench coverage report"
```

---

### Task 3: Georef Metadata

**Files:**
- Create: `scripts/build_georef_metadata.py`
- Test: `tests/test_georef_metadata.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_georef_metadata.py`:

```python
import json

from scripts.build_georef_metadata import build_georef_metadata, write_georef_metadata


def test_build_georef_metadata_defaults_to_none():
    data = build_georef_metadata()

    assert data["mode"] == "none"
    assert data["crs"] is None
    assert data["origin"] == {"lat": None, "lng": None, "height": None}
    assert data["headingDegrees"] is None
    assert data["scaleMetersPerUnit"] is None
    assert data["confidence"] == "none"
    assert data["notes"] == []


def test_build_georef_metadata_manual_origin():
    data = build_georef_metadata(
        mode="manual",
        lat=24.15,
        lng=120.66,
        height=12.5,
        heading=30.0,
        scale=0.01,
        crs="EPSG:4326",
        note="field estimate",
    )

    assert data["mode"] == "manual"
    assert data["origin"] == {"lat": 24.15, "lng": 120.66, "height": 12.5}
    assert data["headingDegrees"] == 30.0
    assert data["scaleMetersPerUnit"] == 0.01
    assert data["crs"] == "EPSG:4326"
    assert data["confidence"] == "low"
    assert data["notes"] == ["field estimate"]


def test_write_georef_metadata(tmp_path):
    output = tmp_path / "georef.json"

    write_georef_metadata(output, mode="manual", lat=1.0, lng=2.0)

    data = json.loads(output.read_text())
    assert data["mode"] == "manual"
    assert data["origin"]["lat"] == 1.0
    assert data["origin"]["lng"] == 2.0
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest -q tests/test_georef_metadata.py
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/build_georef_metadata.py`**

Create `scripts/build_georef_metadata.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


def confidence_for_mode(mode: str) -> str:
    return {
        "none": "none",
        "exif": "low",
        "manual": "low",
        "gcp": "medium",
        "rtk": "high",
    }.get(mode, "none")


def build_georef_metadata(
    mode: str = "none",
    lat: float | None = None,
    lng: float | None = None,
    height: float | None = None,
    heading: float | None = None,
    scale: float | None = None,
    crs: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if mode not in {"none", "exif", "manual", "gcp", "rtk"}:
        raise ValueError(f"unsupported georef mode: {mode}")
    notes = [note] if note else []
    return {
        "mode": mode,
        "crs": crs,
        "origin": {
            "lat": lat,
            "lng": lng,
            "height": height,
        },
        "headingDegrees": heading,
        "scaleMetersPerUnit": scale,
        "controlPoints": [],
        "confidence": confidence_for_mode(mode),
        "notes": notes,
    }


def write_georef_metadata(output: Path, **kwargs: Any) -> dict[str, Any]:
    data = build_georef_metadata(**kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build georef.json for outdoor trench jobs.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", default="none", choices=["none", "exif", "manual", "gcp", "rtk"])
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lng", type=float)
    parser.add_argument("--height", type=float)
    parser.add_argument("--heading", type=float)
    parser.add_argument("--scale", type=float)
    parser.add_argument("--crs")
    parser.add_argument("--note")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_georef_metadata(
        args.output,
        mode=args.mode,
        lat=args.lat,
        lng=args.lng,
        height=args.height,
        heading=args.heading,
        scale=args.scale,
        crs=args.crs,
        note=args.note,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest -q tests/test_georef_metadata.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_georef_metadata.py tests/test_georef_metadata.py
git commit -m "feat: add trench georef metadata"
```

---

### Task 4: Trench Delivery Export

**Files:**
- Create: `scripts/build_trench_delivery.py`
- Test: `tests/test_trench_delivery.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trench_delivery.py`:

```python
import json

from scripts.build_trench_delivery import build_trench_delivery


def test_build_trench_delivery_copies_clean_splat_and_writes_metadata(tmp_path):
    job = tmp_path / "job"
    exports = job / "exports"
    exports.mkdir(parents=True)
    clean = exports / "splat.clean.ply"
    clean.write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 0\nend_header\n")
    (exports / "splat.clean.viewer.json").write_text(
        json.dumps({"core": {"center": [1, 2, 3], "radius": 4}, "viewer": {"rx": 0}})
    )

    result = build_trench_delivery(job)

    assert result["delivery_mode"] == "gaussian_splat"
    assert result["trench_splat"] == str(exports / "splat.trench.ply")
    assert (exports / "splat.trench.ply").read_bytes() == clean.read_bytes()
    metadata = json.loads((exports / "splat.trench.viewer.json").read_text())
    assert metadata["mode"] == "trench"
    assert metadata["core"] == {"center": [1, 2, 3], "radius": 4}
    assert metadata["viewer"]["focusMode"] == "trench"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest -q tests/test_trench_delivery.py
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/build_trench_delivery.py`**

Create `scripts/build_trench_delivery.py`:

```python
#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def build_trench_delivery(job_dir: Path) -> dict[str, Any]:
    exports = job_dir / "exports"
    clean_splat = exports / "splat.clean.ply"
    raw_splat = exports / "splat.ply"
    source_splat = clean_splat if clean_splat.is_file() else raw_splat
    if not source_splat.is_file():
        raise FileNotFoundError(f"no splat source found in {exports}")

    output_splat = exports / "splat.trench.ply"
    output_meta = exports / "splat.trench.viewer.json"
    source_meta = load_json(exports / "splat.clean.viewer.json")

    shutil.copyfile(source_splat, output_splat)

    metadata = {
        **source_meta,
        "mode": "trench",
        "delivery": {
            "deliveryMode": "gaussian_splat",
            "sourceSplat": str(source_splat),
            "policy": "v1_clean_splat_as_trench_focus",
        },
        "viewer": {
            **source_meta.get("viewer", {}),
            "focusMode": "trench",
        },
    }
    output_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return {
        "delivery_mode": "gaussian_splat",
        "source_splat": str(source_splat),
        "trench_splat": str(output_splat),
        "trench_viewer_meta": str(output_meta),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trench-focused splat delivery files.")
    parser.add_argument("job_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_trench_delivery(args.job_dir)
    print(result["trench_splat"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest -q tests/test_trench_delivery.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_trench_delivery.py tests/test_trench_delivery.py
git commit -m "feat: add trench delivery export"
```

---

### Task 5: Trench QA Report

**Files:**
- Create: `scripts/build_trench_qa_report.py`
- Test: `tests/test_trench_qa_report.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trench_qa_report.py`:

```python
import json

from scripts.build_trench_qa_report import build_trench_qa_report


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_build_trench_qa_report_deliverable(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.86, "splat_count": 1000, "quality_grade": "B", "warnings": []})
    write_json(job / "trench_coverage_report.json", {"input_mode": "walk_video", "selected_count": 90, "registered_count": 78, "registered_ratio": 0.87, "warnings": []})
    write_json(job / "georef.json", {"confidence": "low"})
    write_json(job / "exports" / "splat.trench.viewer.json", {"delivery": {"deliveryMode": "gaussian_splat"}})
    (job / "exports" / "splat.trench.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 800\nend_header\n")

    report = build_trench_qa_report(job)

    assert report["input_mode"] == "walk_video"
    assert report["registered_ratio"] == 0.87
    assert report["splat_count"] == 1000
    assert report["trench_splat_count"] == 800
    assert report["georef_confidence"] == "low"
    assert report["delivery_grade"] == "B"
    assert report["decision"] == "deliverable"
    assert report["delivery_mode"] == "gaussian_splat"


def test_build_trench_qa_report_requests_supplemental_capture(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.55, "splat_count": 100, "quality_grade": "C", "warnings": ["registered_ratio lower than 0.8"]})
    write_json(job / "trench_coverage_report.json", {"input_mode": "photo_set", "selected_count": 12, "registered_count": 6, "registered_ratio": 0.5, "warnings": ["registered_ratio lower than 0.65"]})
    write_json(job / "georef.json", {"confidence": "none"})

    report = build_trench_qa_report(job)

    assert report["decision"] == "supplemental_capture_needed"
    assert report["delivery_grade"] == "C"
    assert "registered_ratio lower than 0.65" in report["warnings"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest -q tests/test_trench_qa_report.py
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/build_trench_qa_report.py`**

Create `scripts/build_trench_qa_report.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any

from scripts.build_qa_report import splat_count_from_ply


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def delivery_grade(registered_ratio: float, trench_splat_count: int) -> str:
    if trench_splat_count <= 0 or registered_ratio < 0.3:
        return "D"
    if registered_ratio >= 0.9:
        return "A"
    if registered_ratio >= 0.8:
        return "B"
    if registered_ratio >= 0.5:
        return "C"
    return "D"


def decision_for_grade(grade: str, registered_ratio: float) -> str:
    if grade in {"A", "B"}:
        return "deliverable"
    if grade == "C" and registered_ratio >= 0.5:
        return "supplemental_capture_needed"
    if grade == "C":
        return "review_needed"
    return "retake"


def build_trench_qa_report(job_dir: Path) -> dict[str, Any]:
    qa = load_json(job_dir / "qa_report.json")
    coverage = load_json(job_dir / "trench_coverage_report.json")
    georef = load_json(job_dir / "georef.json")
    trench_meta = load_json(job_dir / "exports" / "splat.trench.viewer.json")

    registered_ratio = float(coverage.get("registered_ratio", qa.get("registered_ratio", 0.0)) or 0.0)
    trench_splat_count = splat_count_from_ply(job_dir / "exports" / "splat.trench.ply")
    grade = delivery_grade(registered_ratio, trench_splat_count or int(qa.get("splat_count", 0) or 0))

    warnings = []
    for source in (qa.get("warnings", []), coverage.get("warnings", [])):
        if isinstance(source, list):
            warnings.extend(str(item) for item in source)

    return {
        "input_mode": coverage.get("input_mode", "walk_video"),
        "frame_count": qa.get("frame_count", 0),
        "selected_count": coverage.get("selected_count", qa.get("frame_count", 0)),
        "registered_count": coverage.get("registered_count", qa.get("registered_count", 0)),
        "registered_ratio": registered_ratio,
        "splat_count": qa.get("splat_count", 0),
        "trench_splat_count": trench_splat_count,
        "trench_kept_ratio": round(trench_splat_count / qa["splat_count"], 2) if qa.get("splat_count") else 0.0,
        "surface_readability": "good" if grade in {"A", "B"} else "fair" if grade == "C" else "poor",
        "texture_realism": "good" if grade in {"A", "B"} else "fair" if grade == "C" else "poor",
        "background_artifact_score": 3 if grade in {"A", "B"} else 2 if grade == "C" else 1,
        "georef_confidence": georef.get("confidence", "none"),
        "delivery_grade": grade,
        "decision": decision_for_grade(grade, registered_ratio),
        "delivery_mode": trench_meta.get("delivery", {}).get("deliveryMode", "gaussian_splat"),
        "warnings": sorted(set(warnings)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build engineering trench QA report.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.job_dir / "trench_qa_report.json"
    report = build_trench_qa_report(args.job_dir)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest -q tests/test_trench_qa_report.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_trench_qa_report.py tests/test_trench_qa_report.py
git commit -m "feat: add trench engineering QA"
```

---

### Task 6: Delivery Manifest For Gaussian / Oblique / GLB Hybrid

**Files:**
- Create: `scripts/build_delivery_manifest.py`
- Test: `tests/test_delivery_manifest.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_delivery_manifest.py`:

```python
import json

from scripts.build_delivery_manifest import build_delivery_manifest


def test_build_delivery_manifest_defaults_to_gaussian_splat(tmp_path):
    job = tmp_path / "job"
    exports = job / "exports"
    exports.mkdir(parents=True)
    (exports / "splat.trench.ply").write_bytes(b"ply")
    (exports / "splat.trench.viewer.json").write_text("{}")

    manifest = build_delivery_manifest(job)

    assert manifest["delivery_mode"] == "gaussian_splat"
    assert manifest["layers"]["gaussian_splat"]["splat"] == str(exports / "splat.trench.ply")
    assert manifest["layers"]["oblique_projection"] is None
    assert manifest["layers"]["glb_hybrid"] is None


def test_build_delivery_manifest_accepts_mixed_placeholders(tmp_path):
    job = tmp_path / "job"

    manifest = build_delivery_manifest(
        job,
        delivery_mode="mixed",
        oblique_projection="overlays/orthophoto.png",
        glb_hybrid="models/manhole.glb",
    )

    assert manifest["delivery_mode"] == "mixed"
    assert manifest["layers"]["oblique_projection"] == "overlays/orthophoto.png"
    assert manifest["layers"]["glb_hybrid"] == "models/manhole.glb"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest -q tests/test_delivery_manifest.py
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/build_delivery_manifest.py`**

Create `scripts/build_delivery_manifest.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


DELIVERY_MODES = {"gaussian_splat", "oblique_projection", "glb_hybrid", "mixed"}


def build_delivery_manifest(
    job_dir: Path,
    delivery_mode: str = "gaussian_splat",
    oblique_projection: str | None = None,
    glb_hybrid: str | None = None,
) -> dict[str, Any]:
    if delivery_mode not in DELIVERY_MODES:
        raise ValueError(f"unsupported delivery mode: {delivery_mode}")
    exports = job_dir / "exports"
    return {
        "delivery_mode": delivery_mode,
        "layers": {
            "gaussian_splat": {
                "splat": str(exports / "splat.trench.ply"),
                "meta": str(exports / "splat.trench.viewer.json"),
            },
            "oblique_projection": oblique_projection,
            "glb_hybrid": glb_hybrid,
        },
        "notes": [
            "Gaussian Splat is the primary MVP delivery layer.",
            "Oblique projection and GLB hybrid are reserved for map-review alternatives.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reality-layer delivery manifest.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--delivery-mode", default="gaussian_splat", choices=sorted(DELIVERY_MODES))
    parser.add_argument("--oblique-projection")
    parser.add_argument("--glb-hybrid")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.job_dir / "delivery_manifest.json"
    manifest = build_delivery_manifest(
        args.job_dir,
        delivery_mode=args.delivery_mode,
        oblique_projection=args.oblique_projection,
        glb_hybrid=args.glb_hybrid,
    )
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest -q tests/test_delivery_manifest.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_delivery_manifest.py tests/test_delivery_manifest.py
git commit -m "feat: add reality layer delivery manifest"
```

---

### Task 7: Pipeline Hook For `GS_TRENCH_MODE=1`

**Files:**
- Modify: `scripts/run_mvp_pipeline.sh`
- Modify: `tests/test_nerfstudio_scripts.py`

- [ ] **Step 1: Write failing static test**

Append to `tests/test_nerfstudio_scripts.py`:

```python
def test_run_pipeline_supports_trench_mode_outputs():
    text = read_script("run_mvp_pipeline.sh")
    assert 'TRENCH_MODE="${GS_TRENCH_MODE:-0}"' in text
    assert "scripts/outdoor_intake.py" in text
    assert "scripts/build_trench_coverage_report.py" in text
    assert "scripts/build_georef_metadata.py" in text
    assert "scripts/build_trench_delivery.py" in text
    assert "scripts/build_trench_qa_report.py" in text
    assert "scripts/build_delivery_manifest.py" in text
    assert 'chmod a+r "$JOB_DIR/georef.json"' in text
    assert 'chmod a+r "$JOB_DIR/trench_qa_report.json"' in text
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
pytest -q tests/test_nerfstudio_scripts.py::test_run_pipeline_supports_trench_mode_outputs
```

Expected: FAIL because `GS_TRENCH_MODE` is not wired.

- [ ] **Step 3: Modify `scripts/run_mvp_pipeline.sh`**

Add near the existing env variables:

```bash
TRENCH_MODE="${GS_TRENCH_MODE:-0}"
GEOREF_MODE="${GS_GEOREF_MODE:-none}"
GEOREF_CRS="${GS_GEOREF_CRS:-}"
GEOREF_LAT="${GS_GEOREF_LAT:-}"
GEOREF_LNG="${GS_GEOREF_LNG:-}"
GEOREF_HEIGHT="${GS_GEOREF_HEIGHT:-}"
GEOREF_HEADING="${GS_GEOREF_HEADING:-}"
GEOREF_SCALE="${GS_GEOREF_SCALE:-}"
```

Add this function before `finalize_outputs()`:

```bash
run_trench_outputs() {
  run_stage trench_input "outdoor input manifest" python3 "$PROJECT_ROOT/scripts/outdoor_intake.py" "$STAGED_INPUT" "$JOB_DIR/input_manifest.json" >&2
  run_stage trench_coverage "trench coverage report" python3 "$PROJECT_ROOT/scripts/build_trench_coverage_report.py" "$JOB_DIR" >&2

  local georef_args=("$JOB_DIR/georef.json" "--mode" "$GEOREF_MODE")
  if [ -n "$GEOREF_CRS" ]; then georef_args+=("--crs" "$GEOREF_CRS"); fi
  if [ -n "$GEOREF_LAT" ]; then georef_args+=("--lat" "$GEOREF_LAT"); fi
  if [ -n "$GEOREF_LNG" ]; then georef_args+=("--lng" "$GEOREF_LNG"); fi
  if [ -n "$GEOREF_HEIGHT" ]; then georef_args+=("--height" "$GEOREF_HEIGHT"); fi
  if [ -n "$GEOREF_HEADING" ]; then georef_args+=("--heading" "$GEOREF_HEADING"); fi
  if [ -n "$GEOREF_SCALE" ]; then georef_args+=("--scale" "$GEOREF_SCALE"); fi

  run_stage georef "georef metadata" python3 "$PROJECT_ROOT/scripts/build_georef_metadata.py" "${georef_args[@]}" >&2
  run_stage trench_delivery "trench delivery export" python3 "$PROJECT_ROOT/scripts/build_trench_delivery.py" "$JOB_DIR" >&2
  run_stage trench_qa "trench engineering QA" python3 "$PROJECT_ROOT/scripts/build_trench_qa_report.py" "$JOB_DIR" >&2
  run_stage delivery_manifest "delivery manifest" python3 "$PROJECT_ROOT/scripts/build_delivery_manifest.py" "$JOB_DIR" >&2
}
```

Add after standard cleanup and before `finalize_outputs`:

```bash
if [ "$TRENCH_MODE" = "1" ]; then
  run_trench_outputs
fi
```

Add chmod near the existing output permissions:

```bash
if [ -f "$JOB_DIR/input_manifest.json" ]; then chmod a+r "$JOB_DIR/input_manifest.json"; fi
if [ -f "$JOB_DIR/trench_coverage_report.json" ]; then chmod a+r "$JOB_DIR/trench_coverage_report.json"; fi
if [ -f "$JOB_DIR/georef.json" ]; then chmod a+r "$JOB_DIR/georef.json"; fi
if [ -f "$JOB_DIR/trench_qa_report.json" ]; then chmod a+r "$JOB_DIR/trench_qa_report.json"; fi
if [ -f "$JOB_DIR/delivery_manifest.json" ]; then chmod a+r "$JOB_DIR/delivery_manifest.json"; fi
if [ -f "$JOB_DIR/exports/splat.trench.ply" ]; then chmod a+r "$JOB_DIR/exports/splat.trench.ply"; fi
if [ -f "$JOB_DIR/exports/splat.trench.viewer.json" ]; then chmod a+r "$JOB_DIR/exports/splat.trench.viewer.json"; fi
```

- [ ] **Step 4: Run static test**

Run:

```bash
pytest -q tests/test_nerfstudio_scripts.py::test_run_pipeline_supports_trench_mode_outputs
```

Expected: PASS.

- [ ] **Step 5: Run focused script tests**

Run:

```bash
pytest -q tests/test_outdoor_intake.py tests/test_trench_coverage_report.py tests/test_georef_metadata.py tests/test_trench_delivery.py tests/test_trench_qa_report.py tests/test_delivery_manifest.py tests/test_nerfstudio_scripts.py
```

Expected: PASS, except any pre-existing environment-dependent upload symlink test may still fail if `uploads/` is not writable.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_mvp_pipeline.sh tests/test_nerfstudio_scripts.py
git commit -m "feat: wire trench mode pipeline outputs"
```

---

### Task 8: Runbook And Spec Alignment

**Files:**
- Modify: `docs/frame-quality-runbook.md`
- Modify: `history.md`

- [ ] **Step 1: Add runbook section**

Append this section to `docs/frame-quality-runbook.md`:

```markdown
## Outdoor Trench Reality Layer Mode

Use this mode for outdoor road excavation and sewer construction benchmarks.

```bash
GS_TRENCH_MODE=1 GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/<job>/input/input.mp4 uploads/<job>-trench
```

Expected additional files:

- `input_manifest.json`
- `trench_coverage_report.json`
- `georef.json`
- `exports/splat.trench.ply`
- `exports/splat.trench.viewer.json`
- `trench_qa_report.json`
- `delivery_manifest.json`

The first version uses `splat.clean.ply` as the trench-focused delivery source. True corridor filtering and oblique/GLB hybrid delivery are later improvements.
```
```

- [ ] **Step 2: Add history note**

Append to `history.md`:

```markdown
## 2026-06-20 Outdoor Trench Technical Foundation Plan

Scope:

- Keep Phase 1 mobile web capture guide as the product direction.
- Implement server-side 3D processing foundations first.
- Add trench coverage QA, georef metadata, trench-focused splat delivery, engineering QA, and delivery manifest.
- Reserve oblique projection and GLB hybrid delivery modes for map-review alternatives.

Primary spec:

- `docs/superpowers/specs/2026-06-20-outdoor-trench-reality-layer-design.md`

Implementation plan:

- `docs/superpowers/plans/2026-06-20-outdoor-trench-technical-foundation.md`
```

- [ ] **Step 3: Run doc grep**

Run:

```bash
rg -n "Outdoor Trench Reality Layer Mode|splat.trench|delivery_manifest|trench_qa_report" docs/frame-quality-runbook.md history.md
```

Expected: matches in both files.

- [ ] **Step 4: Commit**

```bash
git add docs/frame-quality-runbook.md history.md
git commit -m "docs: record outdoor trench technical foundation"
```

---

### Task 9: Final Verification

**Files:**
- No new source files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest -q tests/test_outdoor_intake.py tests/test_trench_coverage_report.py tests/test_georef_metadata.py tests/test_trench_delivery.py tests/test_trench_qa_report.py tests/test_delivery_manifest.py tests/test_nerfstudio_scripts.py
```

Expected: PASS, except pre-existing permission-sensitive tests should be documented if `uploads/` is not writable.

- [ ] **Step 2: Compile scripts**

Run:

```bash
python3 -m py_compile \
  scripts/outdoor_intake.py \
  scripts/build_trench_coverage_report.py \
  scripts/build_georef_metadata.py \
  scripts/build_trench_delivery.py \
  scripts/build_trench_qa_report.py \
  scripts/build_delivery_manifest.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Smoke trench scripts on a synthetic job**

Run:

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/job/exports" "$tmp/job/processed"
printf 'ply\nformat binary_little_endian 1.0\nelement vertex 0\nend_header\n' > "$tmp/job/exports/splat.clean.ply"
printf '{"frames":[]}\n' > "$tmp/job/processed/transforms.json"
printf '{"registered_ratio":0,"splat_count":0,"warnings":[]}\n' > "$tmp/job/qa_report.json"
python3 scripts/outdoor_intake.py "$tmp/job" "$tmp/job/input_manifest.json" || true
python3 scripts/build_trench_coverage_report.py "$tmp/job"
python3 scripts/build_georef_metadata.py "$tmp/job/georef.json"
python3 scripts/build_trench_delivery.py "$tmp/job"
python3 scripts/build_trench_qa_report.py "$tmp/job"
python3 scripts/build_delivery_manifest.py "$tmp/job"
find "$tmp/job" -maxdepth 2 -type f | sort
```

Expected files include:

```text
input_manifest.json
trench_coverage_report.json
georef.json
trench_qa_report.json
delivery_manifest.json
exports/splat.trench.ply
exports/splat.trench.viewer.json
```

- [ ] **Step 4: Run full test suite when environment allows**

Run:

```bash
pytest -q
```

Expected: PASS. If the existing symlink test fails because `uploads/` is owned by `www-data`, record that as an environment limitation and run:

```bash
pytest -q -k 'not test_run_pipeline_rejects_symlink_job_dir_outside_uploads'
```

- [ ] **Step 5: Commit verification doc updates if any**

```bash
git status --short
```

Expected: only intended files changed.

---

## Self-Review

Spec coverage:

- A walk-video mode: covered by `outdoor_intake.py`, pipeline hook, coverage report.
- C photo-set mode: covered by input manifest and coverage diagnostics; training support remains a later pipeline extension.
- Trench-focused export: covered by `build_trench_delivery.py`.
- Engineering QA: covered by `build_trench_coverage_report.py` and `build_trench_qa_report.py`.
- Georef metadata: covered by `build_georef_metadata.py`.
- Oblique/GLB hybrid path: covered by `build_delivery_manifest.py` metadata, not by actual projection.
- Mobile app future compatibility: covered by input manifest and server-side contract; UI is intentionally out of scope.

Known gaps intentionally deferred:

- True automatic trench corridor filtering.
- Admin-drawn ROI polygon.
- Oblique projection generation.
- GLB anchor placement.
- Mobile web capture guide UI.
- Cesium/Easymap layer integration.
