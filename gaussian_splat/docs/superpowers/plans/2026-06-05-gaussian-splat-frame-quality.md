# Gaussian Splat Frame Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve customer-facing Gaussian Splat quality by selecting sharper, better-exposed video frames before COLMAP/Nerfstudio, preserving chronological camera intent for viewer entry, and keeping AI upscaling as a measured experiment rather than the default path.

**Architecture:** Add a Python frame-quality selector between `scripts/extract_frames.py` and `scripts/process_nerfstudio.sh`. It extracts dense candidates from the video, scores blur/exposure/texture, selects one best frame per temporal bucket, writes `frame_quality_report.json`, and feeds only selected frames to Nerfstudio. A separate optional Real-ESRGAN enhancement adapter reuses `/var/www/html/demo/php/ai_video/binary/realesrgan-ncnn-vulkan` after selection for A/B tests.

**Tech Stack:** Python 3.10, OpenCV `cv2`, NumPy, Pillow, pytest, ffmpeg/ffprobe, Bash, Nerfstudio/COLMAP, existing Real-ESRGAN NCNN Vulkan binary from `/var/www/html/demo/php/ai_video`, GaussianSplats3D viewer metadata.

---

## Context And Decision

The current Gaussian pipeline uses `scripts/extract_frames.py` to run a direct ffmpeg command:

```text
ffmpeg -y -i input.mp4 -vf fps={fps},scale={width}:-1 -frames:v {max_frames} -an -f image2 frame_%05d.jpg
```

That is deterministic, but it is blind. At `fps=3`, it may pick a frame during motion blur, autofocus hunting, rolling exposure, or low-light noise. For Gaussian Splat training, a blurry frame hurts COLMAP feature detection and gives `splatfacto` inconsistent texture evidence. So yes: in low-light field captures, extracting "exactly every 1/3 second" without quality selection can materially reduce reconstruction quality.

The older `/var/www/html/demo/php/ai_video` app is a Real-ESRGAN video upscaler. It extracts all frames at 30fps, runs `binary/realesrgan-ncnn-vulkan -s 2 -f png`, and reassembles MP4. It has reusable frame extraction and image enhancement patterns, but it does not do deblur scoring, frame ranking, COLMAP integration, or pose-aware fusion. For Gaussian Splat, reuse its Real-ESRGAN binary only as an optional experiment after selecting good frames.

Default strategy:

```text
video -> dense candidates -> score frames -> select best frame per time bucket -> Nerfstudio images
```

Experimental strategy:

```text
video -> dense candidates -> score/select -> optional Real-ESRGAN x2 -> Nerfstudio images
```

Avoid as default:

```text
video -> upscale all frames -> reassemble MP4 -> sample fps=3 -> Nerfstudio
```

That path is slow, storage-heavy, and can hallucinate inconsistent details.

## File Structure

Create or modify these files:

```text
/var/www/html/demo/php/map/3D/gaussian_splat/
  scripts/
    frame_quality_select.py          # New: dense extraction, scoring, bucket selection, report writer
    enhance_frames_realesrgan.py     # New: optional selected-frame Real-ESRGAN adapter
    run_mvp_pipeline.sh              # Modify: insert frame-quality selection before Nerfstudio
    build_qa_report.py               # Modify: include frame quality report summary
  js/
    gaussian_splat_viewer.js         # Modify later: load first-registered-frame camera metadata
  tests/
    test_frame_quality_select.py     # New: score/select/report tests
    test_enhance_frames_realesrgan.py # New: command construction and failure behavior
    test_nerfstudio_scripts.py       # Modify: pipeline order checks
    test_qa_report.py                # Modify: report includes frame-quality warnings
    test_viewer_assets.py            # Modify later: viewer metadata first-photo fields
```

Generated job directory shape after this plan:

```text
uploads/{id}/
  input/input.mp4
  candidates/
    candidate_000001.jpg
  images/
    frame_00001.jpg
  enhanced_images/
    frame_00001.png
  frame_quality_report.json
  processed/transforms.json
  outputs/
  exports/splat.ply
  qa_report.json
```

`images/` remains the default Nerfstudio input. `enhanced_images/` is only used when explicitly enabled.

## Quality Scoring Formula

For each candidate frame:

```text
sharpness = variance_of_laplacian(gray)
gradient = mean(sobel_magnitude(gray))
exposure = 1.0 - abs(mean(gray) - 128.0) / 128.0
clipping_penalty = clipped_dark_ratio + clipped_bright_ratio
texture = entropy(gray)
score = z(sharpness) * 0.55 + z(gradient) * 0.20 + exposure * 0.15 + z(texture) * 0.10 - clipping_penalty * 2.0
```

Selection groups dense candidates into time buckets. For target `fps=3`, bucket duration is about 333ms. Pick the highest score in each bucket, but enforce chronological output names:

```text
candidate_000037.jpg -> images/frame_00001.jpg
candidate_000081.jpg -> images/frame_00002.jpg
```

This gives the customer-facing pipeline the best available image near each desired sample time, rather than a random exact tick from ffmpeg.

## Task 1: Frame Scoring Unit

**Files:**
- Create: `scripts/frame_quality_select.py`
- Create: `tests/test_frame_quality_select.py`

- [ ] **Step 1: Write failing tests for frame metrics**

Create `tests/test_frame_quality_select.py`:

```python
from pathlib import Path

import cv2
import numpy as np

from scripts.frame_quality_select import FrameMetrics, compute_frame_metrics, normalize_scores


def write_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), image)
    assert ok


def checkerboard(size: int = 128) -> np.ndarray:
    grid = np.indices((size, size)).sum(axis=0) % 2
    return (grid * 255).astype(np.uint8)


def test_compute_frame_metrics_scores_blurry_frame_lower(tmp_path):
    sharp = checkerboard()
    blurry = cv2.GaussianBlur(sharp, (15, 15), 0)
    sharp_path = tmp_path / "sharp.jpg"
    blurry_path = tmp_path / "blurry.jpg"
    write_image(sharp_path, sharp)
    write_image(blurry_path, blurry)

    sharp_metrics = compute_frame_metrics(sharp_path, index=1, timestamp=0.0)
    blurry_metrics = compute_frame_metrics(blurry_path, index=2, timestamp=0.1)

    assert sharp_metrics.sharpness > blurry_metrics.sharpness
    assert sharp_metrics.gradient > blurry_metrics.gradient
    assert sharp_metrics.path == sharp_path
    assert blurry_metrics.path == blurry_path


def test_normalize_scores_prefers_sharp_well_exposed_frame():
    rows = [
        FrameMetrics(Path("dark.jpg"), 1, 0.0, sharpness=100.0, gradient=30.0, exposure=0.2, clipping=0.6, texture=2.0),
        FrameMetrics(Path("sharp.jpg"), 2, 0.1, sharpness=900.0, gradient=120.0, exposure=0.9, clipping=0.0, texture=5.0),
        FrameMetrics(Path("flat.jpg"), 3, 0.2, sharpness=30.0, gradient=10.0, exposure=0.8, clipping=0.0, texture=0.5),
    ]

    scored = normalize_scores(rows)

    assert scored[1].score > scored[0].score
    assert scored[1].score > scored[2].score
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_frame_quality_select.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.frame_quality_select'
```

- [ ] **Step 3: Implement frame metric helpers**

Create `scripts/frame_quality_select.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
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
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"cannot read image: {path}")

    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
    gradient = np.sqrt(sobel_x * sobel_x + sobel_y * sobel_y)
    mean_value = float(image.mean())
    exposure = 1.0 - min(1.0, abs(mean_value - 128.0) / 128.0)
    clipped_dark = float((image <= 5).mean())
    clipped_bright = float((image >= 250).mean())

    return FrameMetrics(
        path=path,
        index=index,
        timestamp=timestamp,
        sharpness=float(laplacian.var()),
        gradient=float(gradient.mean()),
        exposure=exposure,
        clipping=clipped_dark + clipped_bright,
        texture=image_entropy(image),
    )


def zscore(values: list[float]) -> list[float]:
    if not values:
        return []
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    stddev = math.sqrt(variance)
    if stddev == 0:
        return [0.0 for _ in values]
    return [(value - mean) / stddev for value in values]


def normalize_scores(rows: list[FrameMetrics]) -> list[FrameMetrics]:
    sharpness = zscore([row.sharpness for row in rows])
    gradient = zscore([row.gradient for row in rows])
    texture = zscore([row.texture for row in rows])
    scored: list[FrameMetrics] = []
    for index, row in enumerate(rows):
        row.score = (
            sharpness[index] * 0.55
            + gradient[index] * 0.20
            + row.exposure * 0.15
            + texture[index] * 0.10
            - row.clipping * 2.0
        )
        scored.append(row)
    return scored
```

- [ ] **Step 4: Run metric tests and verify pass**

Run:

```bash
pytest tests/test_frame_quality_select.py -q
```

Expected:

```text
.. [100%]
```

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/frame_quality_select.py tests/test_frame_quality_select.py
git commit -m "feat: score gaussian input frame quality"
```

## Task 2: Dense Candidate Extraction And Bucket Selection

**Files:**
- Modify: `scripts/frame_quality_select.py`
- Modify: `tests/test_frame_quality_select.py`

- [ ] **Step 1: Write failing tests for bucket selection and report shape**

Append to `tests/test_frame_quality_select.py`:

```python
import json

from scripts.frame_quality_select import select_best_frames, write_selected_frames


def metric(path: str, index: int, timestamp: float, score: float) -> FrameMetrics:
    return FrameMetrics(
        path=Path(path),
        index=index,
        timestamp=timestamp,
        sharpness=score * 100.0,
        gradient=score * 10.0,
        exposure=0.8,
        clipping=0.0,
        texture=score,
        score=score,
    )


def test_select_best_frames_keeps_best_candidate_per_bucket():
    rows = [
        metric("candidate_000001.jpg", 1, 0.00, 0.1),
        metric("candidate_000002.jpg", 2, 0.08, 2.0),
        metric("candidate_000003.jpg", 3, 0.20, 1.0),
        metric("candidate_000004.jpg", 4, 0.40, 0.5),
        metric("candidate_000005.jpg", 5, 0.55, 3.0),
    ]

    selected = select_best_frames(rows, target_fps=3, max_frames=10)

    assert [row.path.name for row in selected] == ["candidate_000002.jpg", "candidate_000005.jpg"]


def test_write_selected_frames_copies_chronological_images_and_report(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    write_image(source / "candidate_000001.jpg", checkerboard())
    write_image(source / "candidate_000002.jpg", cv2.GaussianBlur(checkerboard(), (7, 7), 0))
    rows = [
        metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0),
        metric(str(source / "candidate_000002.jpg"), 2, 0.3, 1.0),
    ]

    write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    assert (images / "frame_00001.jpg").is_file()
    data = json.loads(report.read_text())
    assert data["candidate_count"] == 2
    assert data["selected_count"] == 2
    assert data["candidate_fps"] == 12
    assert data["target_fps"] == 3
    assert data["selected"][0]["output_name"] == "frame_00001.jpg"
    assert data["selected"][0]["source_name"] == "candidate_000001.jpg"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_frame_quality_select.py -q
```

Expected:

```text
ImportError: cannot import name 'select_best_frames'
```

- [ ] **Step 3: Implement selection and report writer**

Append to `scripts/frame_quality_select.py`:

```python
def select_best_frames(rows: list[FrameMetrics], target_fps: int, max_frames: int) -> list[FrameMetrics]:
    if target_fps <= 0:
        raise ValueError("target_fps must be positive")
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


def serialize_metric(row: FrameMetrics) -> dict[str, float | int | str]:
    data = asdict(row)
    data["path"] = str(row.path)
    return data


def write_selected_frames(
    candidates: list[FrameMetrics],
    selected: list[FrameMetrics],
    images_dir: Path,
    report_path: Path,
    candidate_fps: int,
    target_fps: int,
) -> None:
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    selected_report = []
    for output_index, row in enumerate(selected, start=1):
        output_name = f"frame_{output_index:05d}.jpg"
        output_path = images_dir / output_name
        shutil.copy2(row.path, output_path)
        selected_report.append(
            {
                "output_name": output_name,
                "source_name": row.path.name,
                "source_path": str(row.path),
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
    report_path.write_text(json.dumps(report, indent=2) + "\n")
```

- [ ] **Step 4: Add ffmpeg candidate extraction CLI**

Append to `scripts/frame_quality_select.py`:

```python
def build_extract_candidates_command(input_video: Path, candidates_dir: Path, candidate_fps: int, width: int) -> list[str]:
    return [
        "ffmpeg",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select high-quality frames for Gaussian Splat reconstruction.")
    parser.add_argument("input_video", type=Path)
    parser.add_argument("candidates_dir", type=Path)
    parser.add_argument("images_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--candidate-fps", type=int, default=12)
    parser.add_argument("--target-fps", type=int, default=3)
    parser.add_argument("--max-frames", type=int, default=180)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--reuse-candidates", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_candidate_metrics(candidates_dir: Path, candidate_fps: int) -> list[FrameMetrics]:
    rows: list[FrameMetrics] = []
    for index, path in enumerate(sorted(candidates_dir.glob("candidate_*.jpg")), start=1):
        rows.append(compute_frame_metrics(path, index=index, timestamp=(index - 1) / candidate_fps))
    return normalize_scores(rows)


def main() -> int:
    args = parse_args()
    if not args.input_video.is_file():
        raise SystemExit(f"input video not found: {args.input_video}")
    if args.candidate_fps < args.target_fps:
        raise SystemExit("candidate-fps must be greater than or equal to target-fps")

    args.candidates_dir.mkdir(parents=True, exist_ok=True)
    if not args.reuse_candidates:
        command = build_extract_candidates_command(args.input_video, args.candidates_dir, args.candidate_fps, args.width)
        if args.dry_run:
            print(" ".join(command))
            return 0
        subprocess.run(command, check=True)

    candidates = load_candidate_metrics(args.candidates_dir, args.candidate_fps)
    if len(candidates) < 8:
        raise SystemExit("candidate frame count is lower than 8")
    selected = select_best_frames(candidates, args.target_fps, args.max_frames)
    if len(selected) < 8:
        raise SystemExit("selected frame count is lower than 8")

    write_selected_frames(candidates, selected, args.images_dir, args.report, args.candidate_fps, args.target_fps)
    print(f"candidates={len(candidates)} selected={len(selected)} report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_frame_quality_select.py -q
node --check js/gaussian_splat_viewer.js
```

Expected:

```text
.... [100%]
```

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/frame_quality_select.py tests/test_frame_quality_select.py
git commit -m "feat: select sharp video frames for splat training"
```

## Task 3: Pipeline Integration

**Files:**
- Modify: `scripts/run_mvp_pipeline.sh`
- Modify: `tests/test_nerfstudio_scripts.py`

- [ ] **Step 1: Write failing pipeline order test**

Append to `tests/test_nerfstudio_scripts.py`:

```python
def test_run_pipeline_selects_quality_frames_before_nerfstudio():
    text = read_script("run_mvp_pipeline.sh")
    assert "scripts/frame_quality_select.py" in text
    assert '"$JOB_DIR/candidates"' in text
    assert '"$JOB_DIR/frame_quality_report.json"' in text
    assert text.index("scripts/frame_quality_select.py") < text.index("scripts/process_nerfstudio.sh")
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py::test_run_pipeline_selects_quality_frames_before_nerfstudio -q
```

Expected:

```text
AssertionError: assert 'scripts/frame_quality_select.py' in text
```

- [ ] **Step 3: Modify pipeline to use selector**

Change `scripts/run_mvp_pipeline.sh` around the current extraction step:

```bash
FRAME_CANDIDATE_FPS="${GS_FRAME_CANDIDATE_FPS:-12}"
FRAME_TARGET_FPS="${GS_FRAME_TARGET_FPS:-3}"
FRAME_MAX_FRAMES="${GS_FRAME_MAX_FRAMES:-180}"
FRAME_WIDTH="${GS_FRAME_WIDTH:-1600}"

python3 "$PROJECT_ROOT/scripts/frame_quality_select.py" \
  "$STAGED_INPUT" \
  "$JOB_DIR/candidates" \
  "$JOB_DIR/images" \
  --report "$JOB_DIR/frame_quality_report.json" \
  --candidate-fps "$FRAME_CANDIDATE_FPS" \
  --target-fps "$FRAME_TARGET_FPS" \
  --max-frames "$FRAME_MAX_FRAMES" \
  --width "$FRAME_WIDTH" >&2
```

Remove the old line:

```bash
python3 "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images" >&2
```

Keep `scripts/extract_frames.py` for manual compatibility; do not delete it.

- [ ] **Step 4: Run pipeline tests**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py tests/test_extract_frames.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/run_mvp_pipeline.sh tests/test_nerfstudio_scripts.py
git commit -m "feat: insert frame quality selection into pipeline"
```

## Task 4: QA Report Integration

**Files:**
- Modify: `scripts/build_qa_report.py`
- Modify: `tests/test_qa_report.py`

- [ ] **Step 1: Write failing QA report test**

Append to `tests/test_qa_report.py`:

```python
def test_build_report_includes_frame_quality_summary(tmp_path):
    job_dir = tmp_path / "job"
    images = job_dir / "images"
    processed = job_dir / "processed"
    exports = job_dir / "exports"
    images.mkdir(parents=True)
    processed.mkdir()
    exports.mkdir()
    (images / "frame_00001.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text('{"frames": [{"file_path": "images/frame_00001.jpg"}]}')
    (exports / "splat.ply").write_bytes(b"ply")
    (job_dir / "frame_quality_report.json").write_text(
        json.dumps(
            {
                "candidate_count": 36,
                "selected_count": 9,
                "candidate_fps": 12,
                "target_fps": 3,
                "selected": [
                    {"score": 1.5, "sharpness": 400.0, "exposure": 0.8, "clipping": 0.0}
                ],
            }
        )
    )

    report = build_report("site-quality", images, processed, exports, has_transform=True)

    assert report["frame_quality"]["candidate_count"] == 36
    assert report["frame_quality"]["selected_count"] == 9
    assert report["frame_quality"]["candidate_fps"] == 12
    assert report["frame_quality"]["target_fps"] == 3
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_qa_report.py::test_build_report_includes_frame_quality_summary -q
```

Expected:

```text
KeyError: 'frame_quality'
```

- [ ] **Step 3: Implement QA summary**

In `scripts/build_qa_report.py`, add:

```python
def load_frame_quality(job_dir: Path) -> dict[str, int | float] | None:
    path = job_dir / "frame_quality_report.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    return {
        "candidate_count": int(data.get("candidate_count", 0)),
        "selected_count": int(data.get("selected_count", 0)),
        "candidate_fps": int(data.get("candidate_fps", 0)),
        "target_fps": int(data.get("target_fps", 0)),
    }
```

Then, inside `build_report`, derive the job dir from `images_dir.parent`:

```python
frame_quality = load_frame_quality(images_dir.parent)
if frame_quality:
    report["frame_quality"] = frame_quality
```

Add warning logic:

```python
if frame_quality and frame_quality["selected_count"] < 60:
    warnings.append("selected frame count lower than 60")
```

- [ ] **Step 4: Run QA tests**

Run:

```bash
pytest tests/test_qa_report.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/build_qa_report.py tests/test_qa_report.py
git commit -m "feat: report selected frame quality"
```

## Task 5: Optional Real-ESRGAN Selected-Frame Enhancement

**Files:**
- Create: `scripts/enhance_frames_realesrgan.py`
- Create: `tests/test_enhance_frames_realesrgan.py`
- Modify: `scripts/run_mvp_pipeline.sh`
- Modify: `tests/test_nerfstudio_scripts.py`

- [ ] **Step 1: Write failing tests for command construction**

Create `tests/test_enhance_frames_realesrgan.py`:

```python
from pathlib import Path

from scripts.enhance_frames_realesrgan import build_realesrgan_command


def test_build_realesrgan_command_uses_ai_video_binary_and_selected_model(tmp_path):
    binary = Path("/var/www/html/demo/php/ai_video/binary/realesrgan-ncnn-vulkan")
    input_dir = tmp_path / "images"
    output_dir = tmp_path / "enhanced_images"

    command = build_realesrgan_command(binary, input_dir, output_dir, scale=2, model_name="realesrgan-x4plus")

    assert command == [
        str(binary),
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-s",
        "2",
        "-n",
        "realesrgan-x4plus",
        "-f",
        "png",
    ]
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_enhance_frames_realesrgan.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.enhance_frames_realesrgan'
```

- [ ] **Step 3: Implement enhancement adapter**

Create `scripts/enhance_frames_realesrgan.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


DEFAULT_BINARY = Path("/var/www/html/demo/php/ai_video/binary/realesrgan-ncnn-vulkan")


def build_realesrgan_command(binary: Path, input_dir: Path, output_dir: Path, scale: int, model_name: str) -> list[str]:
    return [
        str(binary),
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-s",
        str(scale),
        "-n",
        model_name,
        "-f",
        "png",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enhance selected Gaussian Splat input frames with Real-ESRGAN.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--model-name", default="realesrgan-x4plus")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.binary.is_file():
        raise SystemExit(f"Real-ESRGAN binary not found: {args.binary}")
    if not args.input_dir.is_dir():
        raise SystemExit(f"input image directory not found: {args.input_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    command = build_realesrgan_command(args.binary, args.input_dir, args.output_dir, args.scale, args.model_name)
    if args.dry_run:
        print(" ".join(command))
        return 0
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Wire optional enhancement into pipeline**

In `scripts/run_mvp_pipeline.sh`, after frame selection and before `process_nerfstudio.sh`, add:

```bash
NERFSTUDIO_IMAGES_DIR="$JOB_DIR/images"

if [ "${GS_FRAME_ENHANCE:-0}" = "1" ]; then
  python3 "$PROJECT_ROOT/scripts/enhance_frames_realesrgan.py" \
    "$JOB_DIR/images" \
    "$JOB_DIR/enhanced_images" \
    --scale "${GS_FRAME_ENHANCE_SCALE:-2}" \
    --model-name "${GS_FRAME_ENHANCE_MODEL:-realesrgan-x4plus}" >&2
  NERFSTUDIO_IMAGES_DIR="$JOB_DIR/enhanced_images"
fi
```

Change the Nerfstudio line to:

```bash
TRANSFORMS_PATH="$(bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh" "$NERFSTUDIO_IMAGES_DIR" "$JOB_DIR/processed")"
```

- [ ] **Step 5: Add pipeline test assertion**

Append to `tests/test_nerfstudio_scripts.py`:

```python
def test_run_pipeline_can_optionally_enhance_selected_frames():
    text = read_script("run_mvp_pipeline.sh")
    assert "GS_FRAME_ENHANCE" in text
    assert "scripts/enhance_frames_realesrgan.py" in text
    assert 'NERFSTUDIO_IMAGES_DIR="$JOB_DIR/enhanced_images"' in text
    assert '"$NERFSTUDIO_IMAGES_DIR" "$JOB_DIR/processed"' in text
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_enhance_frames_realesrgan.py tests/test_nerfstudio_scripts.py -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 7: Commit**

Run:

```bash
git add scripts/enhance_frames_realesrgan.py tests/test_enhance_frames_realesrgan.py scripts/run_mvp_pipeline.sh tests/test_nerfstudio_scripts.py
git commit -m "feat: add optional realesrgan frame enhancement"
```

## Task 6: First Registered Photo Viewer Entry

**Files:**
- Create: `scripts/build_viewer_metadata.py`
- Create: `tests/test_build_viewer_metadata.py`
- Modify: `js/gaussian_splat_viewer.js`
- Modify: `tests/test_viewer_assets.py`

- [ ] **Step 1: Write failing metadata test**

Create `tests/test_build_viewer_metadata.py`:

```python
import json
from pathlib import Path

from scripts.build_viewer_metadata import apply_dataparser_transform, first_registered_frame


def test_first_registered_frame_uses_chronological_filename_not_transform_order(tmp_path):
    transforms = tmp_path / "transforms.json"
    transforms.write_text(
        json.dumps(
            {
                "frames": [
                    {"file_path": "images/frame_00089.jpg", "transform_matrix": [[1, 0, 0, 9], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
                    {"file_path": "images/frame_00001.jpg", "transform_matrix": [[1, 0, 0, 1], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
                ]
            }
        )
    )

    frame = first_registered_frame(transforms)

    assert frame["file_path"] == "images/frame_00001.jpg"
    assert frame["transform_matrix"][0][3] == 1


def test_apply_dataparser_transform_rotates_and_scales_camera_position():
    camera_to_world = [
        [1, 0, 0, 10],
        [0, 1, 0, 20],
        [0, 0, 1, 30],
        [0, 0, 0, 1],
    ]
    dataparser = {
        "transform": [
            [1, 0, 0, 1],
            [0, 1, 0, 2],
            [0, 0, 1, 3],
        ],
        "scale": 0.5,
    }

    transformed = apply_dataparser_transform(camera_to_world, dataparser)

    assert transformed["position"] == [5.5, 11.0, 16.5]
    assert transformed["forward"] == [0, 0, -1]
```

- [ ] **Step 2: Run failing test**

Run:

```bash
pytest tests/test_build_viewer_metadata.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.build_viewer_metadata'
```

- [ ] **Step 3: Implement chronological first-frame helper**

Create `scripts/build_viewer_metadata.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FRAME_NUMBER = re.compile(r"frame_(\d+)\.")


def frame_sort_key(frame: dict[str, Any]) -> tuple[int, str]:
    path = str(frame.get("file_path", ""))
    match = FRAME_NUMBER.search(path)
    if match:
        return int(match.group(1)), path
    return 10**12, path


def first_registered_frame(transforms_path: Path) -> dict[str, Any]:
    data = json.loads(transforms_path.read_text())
    frames = data.get("frames", [])
    if not isinstance(frames, list) or not frames:
        raise ValueError(f"no registered frames in {transforms_path}")
    return sorted(frames, key=frame_sort_key)[0]


def mat3_vec_mul(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [
        sum(matrix[row][col] * vector[col] for col in range(3))
        for row in range(3)
    ]


def vec_add(a: list[float], b: list[float]) -> list[float]:
    return [a[index] + b[index] for index in range(3)]


def vec_scale(vector: list[float], scale: float) -> list[float]:
    return [value * scale for value in vector]


def apply_dataparser_transform(camera_to_world: list[list[float]], dataparser: dict[str, Any]) -> dict[str, list[float]]:
    transform = dataparser["transform"]
    scale = float(dataparser["scale"])
    parser_rotation = [row[:3] for row in transform]
    parser_translation = [row[3] for row in transform]
    camera_rotation = [row[:3] for row in camera_to_world[:3]]
    camera_position = [camera_to_world[row][3] for row in range(3)]

    transformed_position = vec_scale(
        vec_add(mat3_vec_mul(parser_rotation, camera_position), parser_translation),
        scale,
    )
    camera_forward = [-camera_rotation[0][2], -camera_rotation[1][2], -camera_rotation[2][2]]
    transformed_forward = mat3_vec_mul(parser_rotation, camera_forward)
    return {
        "position": transformed_position,
        "forward": transformed_forward,
    }
```

- [ ] **Step 4: Extend metadata schema for first-photo camera**

Add a function to `scripts/build_viewer_metadata.py`:

```python
def first_photo_metadata(transforms_path: Path, dataparser_transforms_path: Path, look_distance: float = 1.0) -> dict[str, Any]:
    frame = first_registered_frame(transforms_path)
    dataparser = json.loads(dataparser_transforms_path.read_text())
    camera = apply_dataparser_transform(frame["transform_matrix"], dataparser)
    look_at = vec_add(camera["position"], vec_scale(camera["forward"], look_distance))
    return {
        "firstFrame": {
            "filePath": frame["file_path"],
            "transformMatrix": frame["transform_matrix"],
            "cameraPosition": camera["position"],
            "cameraForward": camera["forward"],
            "cameraLookAt": look_at,
        }
    }
```

This makes the standalone viewer capable of entering from the first chronologically registered image direction. Validate visually against Nerfstudio viewer before presenting it as the production default.

- [ ] **Step 5: Add viewer test hooks**

Append to `tests/test_viewer_assets.py`:

```python
def test_viewer_js_can_read_first_frame_camera_metadata():
    text = (ROOT / "js" / "gaussian_splat_viewer.js").read_text()
    assert "viewerMeta?.firstFrame" in text
    assert "cameraPosition" in text
    assert "cameraLookAt" in text
    assert "initialCameraLookAt" in text
    assert "initialCameraPosition" in text
```

- [ ] **Step 6: Implement viewer metadata fallback**

In `js/gaussian_splat_viewer.js`, prefer valid first-frame camera metadata when present:

```javascript
const firstFrame = viewerMeta?.firstFrame;
const firstFrameCameraPosition = finiteVector3(firstFrame?.cameraPosition, null);
const firstFrameCameraLookAt = finiteVector3(firstFrame?.cameraLookAt, null);
```

Then choose camera values:

```javascript
const lookAt = firstFrameCameraLookAt || rotateVectorByQuaternion(center, rotation).map((value) => value * sceneScale);
const cameraPosition = firstFrameCameraPosition || [
  lookAt[0],
  lookAt[1] - distance,
  lookAt[2] + Math.max(1, distance * 0.45),
];
```

Keep URL overrides (`distance`, `rx`, `ry`, `rz`) working for manual correction.

- [ ] **Step 7: Run tests**

Run:

```bash
pytest tests/test_build_viewer_metadata.py tests/test_viewer_assets.py -q
node --check js/gaussian_splat_viewer.js
```

Expected:

```text
all tests pass
```

- [ ] **Step 8: Commit**

Run:

```bash
git add scripts/build_viewer_metadata.py tests/test_build_viewer_metadata.py js/gaussian_splat_viewer.js tests/test_viewer_assets.py
git commit -m "feat: record first registered frame for viewer entry"
```

## Task 7: A/B Evaluation Runbook

**Files:**
- Create: `docs/frame-quality-runbook.md`

- [ ] **Step 1: Write runbook**

Create `docs/frame-quality-runbook.md`:

```markdown
# Gaussian Splat Frame Quality Runbook

## Goal

Compare three preprocessing variants on the same source video:

1. Baseline: direct fps=3 extraction.
2. Selected: dense candidate extraction plus frame quality selection.
3. Enhanced: selected frames plus Real-ESRGAN x2.

## Commands

Baseline:

```bash
rm -rf uploads/eval-baseline
mkdir -p uploads/eval-baseline
GS_TRAIN_MAX_ITERATIONS=30000 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-baseline
```

Selected:

```bash
rm -rf uploads/eval-selected
mkdir -p uploads/eval-selected
GS_TRAIN_MAX_ITERATIONS=30000 GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected
```

Enhanced:

```bash
rm -rf uploads/eval-enhanced
mkdir -p uploads/eval-enhanced
GS_TRAIN_MAX_ITERATIONS=30000 GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_FRAME_ENHANCE=1 bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-enhanced
```

## Scorecard

Use this table when reviewing results:

| Variant | Registered ratio | Splats kept after filter | Glass shards | Main object texture | Training time | Customer-ready? |
| --- | ---: | ---: | --- | --- | ---: | --- |
| Baseline |  |  |  |  |  |  |
| Selected |  |  |  |  |  |  |
| Enhanced |  |  |  |  |  |  |

## Decision Rules

- If Selected improves registered ratio and reduces shard filtering, make it default.
- If Enhanced improves visible texture without lowering registered ratio, keep it as an optional "low light" preset.
- If neither improves the scene, retake footage is required: slower orbit, more light, less autofocus drift, object larger in frame.
```

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/frame-quality-runbook.md
git commit -m "docs: add gaussian frame quality evaluation runbook"
```

## Final Verification

Run:

```bash
pytest -q
node --check js/gaussian_splat_viewer.js
```

Expected:

```text
all pytest tests pass
node exits 0
```

## Implementation Notes

- Do not delete `scripts/extract_frames.py`; keep it for manual fallback and existing tests.
- Do not enhance all frames by default. Only enhance selected frames and only when `GS_FRAME_ENHANCE=1`.
- Do not blend adjacent frames into one training image unless the next plan adds optical-flow alignment and validates COLMAP registration. Naive temporal averaging reduces blur visually but destroys view-consistent features.
- Do not assume `transforms.json["frames"][0]` is the first camera view. Sort by `frame_XXXXX` filename and use the first registered chronological frame.
- Keep generated `uploads/`, `data/`, and `outputs/` artifacts out of git unless the user explicitly asks to archive a result.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-05-gaussian-splat-frame-quality.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
