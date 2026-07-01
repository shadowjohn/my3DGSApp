# Gaussian Splat Quality Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a measurable Gaussian Splat quality pipeline so each upload can be judged by evidence instead of viewer impressions.

**Architecture:** Keep the current Nerfstudio pipeline intact, then add small diagnostics scripts around it. Phase 1 creates A/B evidence packages from completed jobs; Phase 2 annotates frame selection with COLMAP registration and camera positions; Phase 3 grades quality in `qa_report.json`; Phase 4 reports low-confidence splat cleanup effectiveness. Real-ESRGAN stays out of the MVP quality loop to avoid adding another variable.

**Tech Stack:** PHP, Bash, Python 3, pytest, ffmpeg, Nerfstudio/COLMAP `transforms.json`, binary little-endian PLY parsing, existing `timing_report.json`, `frame_quality_report.json`, and `qa_report.json`.

---

## Scope

This plan implements Phase 1 through Phase 4:

- Phase 1: A/B quality evidence package.
- Phase 2: COLMAP-aware frame selector reporting.
- Phase 3: quality report with A-D grade.
- Phase 4: low-confidence splat cleanup reporting.

Phase 5 `dgGaussianSplat`, Phase 6 MapLibre overlay, and Phase 7 Cesium overlay are intentionally deferred into separate plans after the quality metrics are stable.

Real-ESRGAN is intentionally excluded from this MVP evidence loop. The first stable comparison set is:

- `baseline_30k`: legacy fps=3 frames, no frame selector, 30k training.
- `selected`: candidate fps=12, target fps=3, frame selector, default training iterations.
- `selected_30k`: candidate fps=12, target fps=3, frame selector, 30k training.

## File Structure

- Create `scripts/build_ab_evidence_report.py`: read multiple completed job directories and write a JSON/Markdown evidence package.
- Create `tests/test_ab_evidence_report.py`: unit tests for evidence report parsing and CLI output.
- Modify `scripts/run_mvp_pipeline.sh`: add `GS_FRAME_SELECTOR=0` legacy baseline path.
- Modify `tests/test_nerfstudio_scripts.py`: asset tests for selector toggle and evidence commands.
- Create `scripts/annotate_frame_quality_colmap.py`: merge COLMAP registration and camera positions into `frame_quality_report.json`.
- Create `tests/test_annotate_frame_quality_colmap.py`: tests for selected frame registration mapping and camera path summary.
- Modify `scripts/run_mvp_pipeline.sh`: run the annotation after COLMAP and before training.
- Modify `scripts/build_qa_report.py`: add canonical quality fields and A-D grading.
- Modify `tests/test_qa_report.py`: tests for quality grade thresholds and new fields.
- Modify `scripts/filter_splat_ply.py`: include cleanup statistics in viewer metadata.
- Modify `tests/test_filter_splat_ply.py`: tests for cleanup stats.
- Modify `docs/frame-quality-runbook.md`: update the runbook to the new MVP order and evidence commands.

---

### Task 1: A/B Evidence Report Builder

**Files:**
- Create: `scripts/build_ab_evidence_report.py`
- Create: `tests/test_ab_evidence_report.py`
- Modify: `docs/frame-quality-runbook.md`

- [ ] **Step 1: Write failing tests for evidence metrics**

Create `tests/test_ab_evidence_report.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

from scripts.build_ab_evidence_report import build_evidence_report


def make_job(tmp_path: Path, name: str, frames: int, registered: int, splat_count: int) -> Path:
    job = tmp_path / name
    images = job / "images"
    processed = job / "processed"
    exports = job / "exports"
    images.mkdir(parents=True)
    processed.mkdir()
    exports.mkdir()
    for index in range(frames):
        (images / f"frame_{index + 1:05d}.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": f"images/frame_{index + 1:05d}.jpg",
                        "transform_matrix": [
                            [1, 0, 0, float(index)],
                            [0, 1, 0, 2.0],
                            [0, 0, 1, 3.0],
                        ],
                    }
                    for index in range(registered)
                ]
            }
        )
    )
    (exports / "splat.ply").write_text(
        "ply\nformat binary_little_endian 1.0\nelement vertex "
        + str(splat_count)
        + "\nproperty float x\nend_header\n"
    )
    (job / "timing_report.json").write_text(
        json.dumps({"duration_seconds": 123.4, "stages": [{"key": "train", "duration_seconds": 90.0}]})
    )
    (job / "qa_report.json").write_text(
        json.dumps({"quality_grade": "B", "warnings": ["registered_ratio lower than 0.8"]})
    )
    return job


def test_build_evidence_report_compares_variants(tmp_path):
    baseline = make_job(tmp_path, "baseline", frames=90, registered=60, splat_count=1000)
    selected = make_job(tmp_path, "selected", frames=120, registered=110, splat_count=1500)

    report = build_evidence_report(
        [
            ("baseline_30k", baseline),
            ("selected_30k", selected),
        ],
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        project_root=tmp_path,
    )

    assert report["summary"]["variant_count"] == 2
    assert report["variants"][0]["variant"] == "baseline_30k"
    assert report["variants"][0]["registered_ratio"] == 0.67
    assert report["variants"][0]["splat_count"] == 1000
    assert report["variants"][0]["psnr_status"] == "not_computed_requires_rendered_eval_images"
    assert "ns-viewer --load-config" in report["variants"][0]["official_viewer_command"]
    assert "viewer_splat.html?src=" in report["variants"][1]["web_viewer_url"]


def test_cli_writes_json_and_markdown(tmp_path):
    baseline = make_job(tmp_path, "baseline", frames=10, registered=8, splat_count=100)
    output = tmp_path / "evidence.json"
    markdown = tmp_path / "evidence.md"
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_ab_evidence_report.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--variant",
            f"baseline_30k={baseline}",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--viewer-base-url",
            "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert markdown.is_file()
    assert "baseline_30k" in markdown.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_ab_evidence_report.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.build_ab_evidence_report'`.

- [ ] **Step 3: Implement the evidence builder**

Create `scripts/build_ab_evidence_report.py` with these public functions:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote


def count_images(job_dir: Path) -> int:
    images = job_dir / "images"
    return len(list(images.glob("*.jpg"))) + len(list(images.glob("*.png")))


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def registered_frames(job_dir: Path) -> list[dict[str, Any]]:
    transforms = load_json(job_dir / "processed" / "transforms.json")
    frames = transforms.get("frames", [])
    return [frame for frame in frames if isinstance(frame, dict)] if isinstance(frames, list) else []


def splat_count_from_ply(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("rb") as handle:
        for raw_line in handle:
            line = raw_line.decode("ascii", errors="ignore").strip()
            if line.startswith("element vertex "):
                return int(line.rsplit(" ", 1)[1])
            if line == "end_header":
                break
    return 0


def latest_config(job_dir: Path) -> Path | None:
    configs = sorted((job_dir / "outputs").glob("*/splatfacto/*/config.yml"))
    return configs[-1] if configs else None


def relative_url_path(path: Path, project_root: Path) -> str:
    try:
        relative = path.resolve(strict=False).relative_to(project_root.resolve(strict=False))
    except ValueError:
        relative = path
    return quote(str(relative).replace("\\", "/"))


def variant_record(variant: str, job_dir: Path, viewer_base_url: str, project_root: Path) -> dict[str, Any]:
    frame_count = count_images(job_dir)
    registered_count = len(registered_frames(job_dir))
    splat_path = job_dir / "exports" / "splat.ply"
    config_path = latest_config(job_dir)
    ratio = round(registered_count / frame_count, 2) if frame_count else 0.0
    timing = load_json(job_dir / "timing_report.json")
    qa = load_json(job_dir / "qa_report.json")
    src = relative_url_path(splat_path, project_root)
    return {
        "variant": variant,
        "job_dir": str(job_dir),
        "frame_count": frame_count,
        "registered_count": registered_count,
        "registered_ratio": ratio,
        "splat_count": splat_count_from_ply(splat_path),
        "splat_file_size_mb": round(splat_path.stat().st_size / 1024 / 1024, 2) if splat_path.is_file() else 0.0,
        "duration_seconds": timing.get("duration_seconds"),
        "quality_grade": qa.get("quality_grade"),
        "warnings": qa.get("warnings", []),
        "psnr": None,
        "psnr_status": "not_computed_requires_rendered_eval_images",
        "official_viewer_command": f"ns-viewer --load-config {config_path}" if config_path else "ns-viewer config.yml not found",
        "web_viewer_url": f"{viewer_base_url}?src={src}",
    }


def build_evidence_report(
    variants: list[tuple[str, Path]],
    viewer_base_url: str,
    project_root: Path,
) -> dict[str, Any]:
    rows = [variant_record(name, path, viewer_base_url, project_root) for name, path in variants]
    best_ratio = max((row["registered_ratio"] for row in rows), default=0.0)
    return {
        "summary": {
            "variant_count": len(rows),
            "best_registered_ratio": best_ratio,
            "psnr_status": "not_computed_requires_rendered_eval_images",
        },
        "variants": rows,
    }
```

Also add `parse_variant`, `write_markdown`, `parse_args`, and `main` so the CLI in the tests works.

- [ ] **Step 4: Update runbook evidence commands**

Modify `docs/frame-quality-runbook.md` so the MVP variants are `baseline_30k`, `selected`, and `selected_30k`. Add this command block:

```bash
python3 scripts/build_ab_evidence_report.py \
  --variant baseline_30k=uploads/eval-baseline-30k \
  --variant selected=uploads/eval-selected \
  --variant selected_30k=uploads/eval-selected-30k \
  --output uploads/eval-ab-quality/evidence.json \
  --markdown uploads/eval-ab-quality/evidence.md \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_ab_evidence_report.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_ab_evidence_report.py tests/test_ab_evidence_report.py docs/frame-quality-runbook.md
git commit -m "feat: add gaussian splat ab evidence report"
```

---

### Task 2: Legacy Baseline Pipeline Toggle

**Files:**
- Modify: `scripts/run_mvp_pipeline.sh`
- Modify: `tests/test_nerfstudio_scripts.py`

- [ ] **Step 1: Write failing asset test**

Append to `tests/test_nerfstudio_scripts.py`:

```python
def test_run_pipeline_can_disable_frame_selector_for_legacy_fps_baseline():
    text = read_script("run_mvp_pipeline.sh")
    assert 'FRAME_SELECTOR="${GS_FRAME_SELECTOR:-1}"' in text
    assert 'if [ "$FRAME_SELECTOR" = "0" ]; then' in text
    assert 'run_stage legacy_extract "legacy fps frame extraction"' in text
    assert 'python3 "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images"' in text
    assert 'else' in text
    assert 'run_stage frame_select "frame quality selection"' in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py::test_run_pipeline_can_disable_frame_selector_for_legacy_fps_baseline -q
```

Expected: FAIL because `FRAME_SELECTOR` is not wired.

- [ ] **Step 3: Implement selector toggle**

In `scripts/run_mvp_pipeline.sh`, add:

```bash
FRAME_SELECTOR="${GS_FRAME_SELECTOR:-1}"
```

Replace the unconditional `run_stage frame_select ...` block with:

```bash
if [ "$FRAME_SELECTOR" = "0" ]; then
  run_stage legacy_extract "legacy fps frame extraction" python3 "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images" --fps "$FRAME_TARGET_FPS" --width "$FRAME_WIDTH" >&2
else
  run_stage frame_select "frame quality selection" python3 "$PROJECT_ROOT/scripts/frame_quality_select.py" \
    "$STAGED_INPUT" \
    "$JOB_DIR/candidates" \
    "$JOB_DIR/images" \
    --report "$JOB_DIR/frame_quality_report.json" \
    --candidate-fps "$FRAME_CANDIDATE_FPS" \
    --target-fps "$FRAME_TARGET_FPS" \
    --max-frames "$FRAME_MAX_FRAMES" \
    --width "$FRAME_WIDTH" >&2
fi
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_mvp_pipeline.sh tests/test_nerfstudio_scripts.py
git commit -m "feat: add legacy gaussian splat baseline toggle"
```

---

### Task 3: COLMAP-Aware Frame Quality Annotation

**Files:**
- Create: `scripts/annotate_frame_quality_colmap.py`
- Create: `tests/test_annotate_frame_quality_colmap.py`
- Modify: `scripts/run_mvp_pipeline.sh`
- Modify: `tests/test_nerfstudio_scripts.py`

- [ ] **Step 1: Write failing tests for annotation**

Create `tests/test_annotate_frame_quality_colmap.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

from scripts.annotate_frame_quality_colmap import annotate_report


def test_annotate_report_marks_registered_selected_frames(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "candidate_count": 20,
                "selected_count": 2,
                "candidate_fps": 12,
                "target_fps": 3,
                "selected": [
                    {"output_name": "frame_00001.jpg", "score": 1.2},
                    {"output_name": "frame_00002.jpg", "score": 0.8},
                ],
                "candidates": [],
            }
        )
    )
    transforms.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": "images/frame_00002.jpg",
                        "transform_matrix": [
                            [1, 0, 0, 4.0],
                            [0, 1, 0, 5.0],
                            [0, 0, 1, 6.0],
                        ],
                    }
                ]
            }
        )
    )

    annotated = annotate_report(report, transforms)

    assert annotated["selected"][0]["colmap_registered"] is False
    assert annotated["selected"][1]["colmap_registered"] is True
    assert annotated["selected"][1]["camera_position"] == [4.0, 5.0, 6.0]
    assert annotated["colmap"]["registered_count"] == 1
    assert annotated["colmap"]["registered_ratio"] == 0.5


def test_cli_updates_report_in_place(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(json.dumps({"selected": [], "selected_count": 0, "candidate_count": 0, "candidate_fps": 12, "target_fps": 3}))
    transforms.write_text(json.dumps({"frames": []}))
    script = Path(__file__).resolve().parents[1] / "scripts" / "annotate_frame_quality_colmap.py"

    result = subprocess.run([sys.executable, str(script), str(report), str(transforms)], check=False, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert json.loads(report.read_text())["colmap"]["registered_count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_annotate_frame_quality_colmap.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement annotation script**

Create `scripts/annotate_frame_quality_colmap.py` with:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def frame_name(file_path: str) -> str:
    return Path(file_path).name


def camera_position(transform_matrix: list[list[float]]) -> list[float]:
    return [float(transform_matrix[row][3]) for row in range(3)]


def registered_map(transforms_path: Path) -> dict[str, list[float]]:
    data = json.loads(transforms_path.read_text())
    rows = {}
    for frame in data.get("frames", []):
        if not isinstance(frame, dict):
            continue
        file_path = frame.get("file_path")
        matrix = frame.get("transform_matrix")
        if isinstance(file_path, str) and isinstance(matrix, list) and len(matrix) >= 3:
            rows[frame_name(file_path)] = camera_position(matrix)
    return rows


def annotate_report(report_path: Path, transforms_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text())
    registered = registered_map(transforms_path)
    selected = report.get("selected", [])
    selected_rows = selected if isinstance(selected, list) else []
    positions = []
    for row in selected_rows:
        if not isinstance(row, dict):
            continue
        output_name = str(row.get("output_name", ""))
        position = registered.get(output_name)
        row["colmap_registered"] = position is not None
        row["camera_position"] = position
        if position is not None:
            positions.append(position)
    selected_count = len(selected_rows)
    registered_count = len(positions)
    report["colmap"] = {
        "registered_count": registered_count,
        "registered_ratio": round(registered_count / selected_count, 2) if selected_count else 0.0,
        "camera_path_bounds": camera_path_bounds(positions),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report
```

Also add `camera_path_bounds`, `parse_args`, and `main`.

- [ ] **Step 4: Wire annotation into pipeline**

After `TRANSFORMS_PATH=...` and `test -f "$TRANSFORMS_PATH"` in `scripts/run_mvp_pipeline.sh`, add:

```bash
if [ -f "$JOB_DIR/frame_quality_report.json" ]; then
  run_stage frame_colmap "frame COLMAP annotation" python3 "$PROJECT_ROOT/scripts/annotate_frame_quality_colmap.py" "$JOB_DIR/frame_quality_report.json" "$TRANSFORMS_PATH" >&2
fi
```

- [ ] **Step 5: Add pipeline asset test**

Append to `tests/test_nerfstudio_scripts.py`:

```python
def test_run_pipeline_annotates_frame_quality_after_colmap():
    text = read_script("run_mvp_pipeline.sh")
    assert "scripts/annotate_frame_quality_colmap.py" in text
    assert 'run_stage frame_colmap "frame COLMAP annotation"' in text
    assert text.index("scripts/process_nerfstudio.sh") < text.index("scripts/annotate_frame_quality_colmap.py")
    assert text.index("scripts/annotate_frame_quality_colmap.py") < text.index("scripts/train_splat.sh")
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_annotate_frame_quality_colmap.py tests/test_nerfstudio_scripts.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/annotate_frame_quality_colmap.py tests/test_annotate_frame_quality_colmap.py scripts/run_mvp_pipeline.sh tests/test_nerfstudio_scripts.py
git commit -m "feat: annotate selected frames with colmap registration"
```

---

### Task 4: Quality Report Grade

**Files:**
- Modify: `scripts/build_qa_report.py`
- Modify: `tests/test_qa_report.py`

- [ ] **Step 1: Write failing tests for quality grade**

Append to `tests/test_qa_report.py`:

```python
def test_build_report_includes_customer_quality_grade(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    for index in range(100):
        (images / f"frame_{index:05d}.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text(
        json.dumps({"frames": [{"file_path": f"images/frame_{index:05d}.jpg"} for index in range(92)]})
    )
    (exports / "splat.ply").write_text(
        "ply\nformat binary_little_endian 1.0\nelement vertex 1328456\nproperty float x\nend_header\n"
    )

    report = build_report("site-grade", images, processed, exports, has_transform=True)

    assert report["registered_count"] == 92
    assert report["registered_ratio"] == 0.92
    assert report["splat_count"] == 1328456
    assert report["quality_grade"] == "A"
    assert report["quality_label"] == "excellent"


def test_build_report_grades_low_registration_as_d(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    for index in range(100):
        (images / f"frame_{index:05d}.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text(
        json.dumps({"frames": [{"file_path": f"images/frame_{index:05d}.jpg"} for index in range(40)]})
    )
    (exports / "splat.ply").write_text(
        "ply\nformat binary_little_endian 1.0\nelement vertex 100\nproperty float x\nend_header\n"
    )

    report = build_report("site-low", images, processed, exports, has_transform=True)

    assert report["quality_grade"] == "D"
    assert report["quality_label"] == "retake_recommended"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_qa_report.py::test_build_report_includes_customer_quality_grade tests/test_qa_report.py::test_build_report_grades_low_registration_as_d -q
```

Expected: FAIL because `registered_count`, `splat_count`, and `quality_grade` are missing.

- [ ] **Step 3: Implement PLY count and grading**

In `scripts/build_qa_report.py`, add:

```python
def splat_count_from_ply(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("rb") as handle:
        for raw_line in handle:
            line = raw_line.decode("ascii", errors="ignore").strip()
            if line.startswith("element vertex "):
                return int(line.rsplit(" ", 1)[1])
            if line == "end_header":
                break
    return 0


def quality_grade(registered_ratio: float, frame_count: int, viewer_ready: bool) -> tuple[str, str]:
    if not viewer_ready or frame_count < 8:
        return "D", "retake_recommended"
    if registered_ratio >= 0.9:
        return "A", "excellent"
    if registered_ratio >= 0.8:
        return "B", "good"
    if registered_ratio >= 0.65:
        return "C", "usable_with_caution"
    return "D", "retake_recommended"
```

Add these fields to the report:

```python
"registered_count": registered_count,
"splat_count": splat_count,
"outlier_ratio": None,
"largest_component_ratio": None,
"quality_grade": grade,
"quality_label": label,
```

Keep `registered_frame_count` for backward compatibility.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_qa_report.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_qa_report.py tests/test_qa_report.py
git commit -m "feat: grade gaussian splat quality report"
```

---

### Task 5: Low-Confidence Splat Cleanup Stats

**Files:**
- Modify: `scripts/filter_splat_ply.py`
- Modify: `tests/test_filter_splat_ply.py`

- [ ] **Step 1: Write failing cleanup stat assertions**

In `tests/test_filter_splat_ply.py`, extend the metadata assertion test with:

```python
    assert meta["cleanup"]["source_vertex_count"] == 3
    assert meta["cleanup"]["kept_vertex_count"] == 1
    assert meta["cleanup"]["removed_vertex_count"] == 2
    assert meta["cleanup"]["kept_ratio"] == 0.33
    assert meta["cleanup"]["filters"]["min_opacity"] == 0.18
    assert "max_scale_used" in meta["cleanup"]["filters"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_filter_splat_ply.py -q
```

Expected: FAIL because `cleanup` metadata is missing.

- [ ] **Step 3: Implement cleanup stats**

Change `filter_rows` to return the kept rows and the max scale used as it does today. In `build_metadata`, add parameters `source_count`, `kept_count`, `min_opacity`, and `max_scale_used`, then write:

```python
"cleanup": {
    "source_vertex_count": source_count,
    "kept_vertex_count": kept_count,
    "removed_vertex_count": source_count - kept_count,
    "kept_ratio": round(kept_count / source_count, 2) if source_count else 0.0,
    "filters": {
        "min_opacity": min_opacity,
        "max_scale_used": max_scale_used,
    },
},
```

Pass those values from `main()` after reading and filtering the PLY.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_filter_splat_ply.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/filter_splat_ply.py tests/test_filter_splat_ply.py
git commit -m "feat: report gaussian splat cleanup stats"
```

---

### Task 6: Final Verification and Operator Notes

**Files:**
- Modify: `docs/frame-quality-runbook.md`

- [ ] **Step 1: Update runbook decision rules**

Add these rules to `docs/frame-quality-runbook.md`:

```markdown
## MVP Decision Rules

- Use `baseline_30k` vs `selected_30k` to decide whether frame selection helps this capture style.
- Treat `registered_ratio < 0.65` as retake territory even when a viewer output exists.
- Treat `quality_grade A/B` as frontstage acceptable, `C` as internal review, and `D` as retake.
- Do not enable Real-ESRGAN in the MVP evidence loop; it is a later experiment after frame selection, COLMAP, training, and cleanup are stable.
- Use cleanup stats to explain shard reduction: report source splat count, kept splat count, kept ratio, and filters.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add docs/frame-quality-runbook.md
git commit -m "docs: document gaussian splat quality decision rules"
```

---

## A/B Commands for the First Evidence Package

Run these after Tasks 1 and 2:

```bash
rm -rf uploads/eval-baseline-30k uploads/eval-selected uploads/eval-selected-30k uploads/eval-ab-quality
mkdir -p uploads/eval-baseline-30k uploads/eval-selected uploads/eval-selected-30k uploads/eval-ab-quality

GS_FRAME_SELECTOR=0 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-baseline-30k

GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected

GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected-30k

python3 scripts/build_ab_evidence_report.py \
  --variant baseline_30k=uploads/eval-baseline-30k \
  --variant selected=uploads/eval-selected \
  --variant selected_30k=uploads/eval-selected-30k \
  --output uploads/eval-ab-quality/evidence.json \
  --markdown uploads/eval-ab-quality/evidence.md \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

Open official viewer first:

```bash
ns-viewer --load-config uploads/eval-selected-30k/outputs/processed/splatfacto/<date>/config.yml
```

Then open the web viewer URLs generated in `uploads/eval-ab-quality/evidence.md`.

---

## Self-Review

- Spec coverage: Phase 1 maps to Tasks 1-2, Phase 2 maps to Task 3, Phase 3 maps to Task 4, Phase 4 maps to Task 5, operator notes map to Task 6.
- Completeness-marker scan: no task uses incomplete-work marker language; Real-ESRGAN and map overlays are explicitly out of scope.
- Type consistency: frame fields use `selected[].output_name`, COLMAP fields use `selected[].colmap_registered` and `selected[].camera_position`, QA fields use `registered_count`, `splat_count`, `quality_grade`, and `quality_label`.
